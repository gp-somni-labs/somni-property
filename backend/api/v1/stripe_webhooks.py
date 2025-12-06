"""
Stripe Webhook Handler
Processes Stripe payment events and updates subscription/billing status
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
import stripe
import logging
import json

from db.database import get_db
from db.family_models import FamilySubscription, FamilyBilling, SubscriptionStatus
from db.models import Client
from core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize Stripe
if hasattr(settings, 'STRIPE_SECRET_KEY') and settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature")
):
    """
    Stripe webhook endpoint

    Handles Stripe events:
    - payment_intent.succeeded: Payment successful
    - payment_intent.payment_failed: Payment failed
    - invoice.paid: Invoice paid
    - invoice.payment_failed: Invoice payment failed
    - customer.subscription.updated: Subscription updated
    - customer.subscription.deleted: Subscription cancelled

    Webhook secret is configured in Stripe Dashboard → Webhooks
    Set environment variable: STRIPE_WEBHOOK_SECRET

    Returns:
        200 OK on success, 400 on verification failure
    """
    payload = await request.body()
    sig_header = stripe_signature

    # Verify webhook signature
    try:
        if hasattr(settings, 'STRIPE_WEBHOOK_SECRET') and settings.STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        else:
            # If no webhook secret, parse JSON directly (NOT RECOMMENDED FOR PRODUCTION)
            logger.warning("Stripe webhook secret not configured - accepting unsigned webhooks")
            event = json.loads(payload)
    except ValueError as e:
        logger.error(f"Invalid Stripe webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Stripe webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    event_type = event['type']
    event_data = event['data']['object']

    logger.info(f"Received Stripe webhook: {event_type}")

    try:
        if event_type == 'payment_intent.succeeded':
            await handle_payment_succeeded(event_data, db)

        elif event_type == 'payment_intent.payment_failed':
            await handle_payment_failed(event_data, db)

        elif event_type == 'invoice.paid':
            await handle_invoice_paid(event_data, db)

        elif event_type == 'invoice.payment_failed':
            await handle_invoice_payment_failed(event_data, db)

        elif event_type == 'customer.subscription.updated':
            await handle_subscription_updated(event_data, db)

        elif event_type == 'customer.subscription.deleted':
            await handle_subscription_deleted(event_data, db)

        else:
            logger.info(f"Unhandled Stripe event type: {event_type}")

        await db.commit()

    except Exception as e:
        logger.error(f"Error handling Stripe webhook {event_type}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    return {"status": "success"}


async def handle_payment_succeeded(payment_intent: dict, db: AsyncSession):
    """
    Handle payment_intent.succeeded event

    Updates FamilyBilling record to mark as paid
    """
    logger.info(f"Payment succeeded: {payment_intent['id']}")

    # Get payment intent metadata (should contain subscription_id or billing_id)
    metadata = payment_intent.get('metadata', {})
    billing_id = metadata.get('billing_id')

    if not billing_id:
        logger.warning(f"No billing_id in payment intent metadata: {payment_intent['id']}")
        return

    # Update billing record
    query = select(FamilyBilling).where(FamilyBilling.id == billing_id)
    result = await db.execute(query)
    billing = result.scalar_one_or_none()

    if billing:
        billing.paid = True
        billing.paid_at = datetime.utcnow()
        billing.payment_method = 'stripe'
        billing.transaction_id = payment_intent['id']
        billing.status = 'paid'
        await db.flush()
        logger.info(f"Marked billing {billing_id} as paid")

        # Update subscription status to active if it was past_due
        query = select(FamilySubscription).where(
            FamilySubscription.id == billing.subscription_id
        )
        result = await db.execute(query)
        subscription = result.scalar_one_or_none()

        if subscription and subscription.status == SubscriptionStatus.PAST_DUE:
            subscription.status = SubscriptionStatus.ACTIVE
            await db.flush()
            logger.info(f"Reactivated subscription {subscription.id}")


async def handle_payment_failed(payment_intent: dict, db: AsyncSession):
    """
    Handle payment_intent.payment_failed event

    Marks subscription as past_due
    """
    logger.warning(f"Payment failed: {payment_intent['id']}")

    metadata = payment_intent.get('metadata', {})
    billing_id = metadata.get('billing_id')
    subscription_id = metadata.get('subscription_id')

    if billing_id:
        # Update billing record
        query = select(FamilyBilling).where(FamilyBilling.id == billing_id)
        result = await db.execute(query)
        billing = result.scalar_one_or_none()

        if billing:
            billing.status = 'failed'
            await db.flush()
            logger.info(f"Marked billing {billing_id} as failed")
            subscription_id = billing.subscription_id

    if subscription_id:
        # Mark subscription as past_due
        query = select(FamilySubscription).where(
            FamilySubscription.id == subscription_id
        )
        result = await db.execute(query)
        subscription = result.scalar_one_or_none()

        if subscription and subscription.status == SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.PAST_DUE
            await db.flush()
            logger.warning(f"Marked subscription {subscription_id} as past_due")

            # TODO: Send notification to customer and staff
            # - Email customer about failed payment
            # - Create support ticket for follow-up
            # - Schedule payment retry


async def handle_invoice_paid(invoice: dict, db: AsyncSession):
    """
    Handle invoice.paid event

    Similar to payment_succeeded but for invoices
    """
    logger.info(f"Invoice paid: {invoice['id']}")

    # Get subscription from invoice
    stripe_subscription_id = invoice.get('subscription')
    if not stripe_subscription_id:
        return

    # Find our subscription by Stripe subscription ID
    # Note: Need to add stripe_subscription_id column to FamilySubscription
    # For now, check metadata
    metadata = invoice.get('metadata', {})
    subscription_id = metadata.get('subscription_id')

    if subscription_id:
        query = select(FamilySubscription).where(
            FamilySubscription.id == subscription_id
        )
        result = await db.execute(query)
        subscription = result.scalar_one_or_none()

        if subscription and subscription.status != SubscriptionStatus.ACTIVE:
            subscription.status = SubscriptionStatus.ACTIVE
            await db.flush()
            logger.info(f"Reactivated subscription {subscription_id} from invoice payment")


async def handle_invoice_payment_failed(invoice: dict, db: AsyncSession):
    """
    Handle invoice.payment_failed event

    Mark subscription as past_due and trigger dunning workflow
    """
    logger.warning(f"Invoice payment failed: {invoice['id']}")

    stripe_subscription_id = invoice.get('subscription')
    if not stripe_subscription_id:
        return

    metadata = invoice.get('metadata', {})
    subscription_id = metadata.get('subscription_id')

    if subscription_id:
        query = select(FamilySubscription).where(
            FamilySubscription.id == subscription_id
        )
        result = await db.execute(query)
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.status = SubscriptionStatus.PAST_DUE
            await db.flush()
            logger.warning(f"Marked subscription {subscription_id} as past_due from invoice failure")

            # TODO: Dunning workflow
            # - Retry payment after 3 days
            # - Send reminder emails
            # - Suspend services after 10 days past due
            # - Cancel after 30 days past due


async def handle_subscription_updated(subscription: dict, db: AsyncSession):
    """
    Handle customer.subscription.updated event

    Update subscription details when changed in Stripe
    """
    logger.info(f"Subscription updated: {subscription['id']}")

    # Get our subscription
    metadata = subscription.get('metadata', {})
    subscription_id = metadata.get('subscription_id')

    if not subscription_id:
        logger.warning(f"No subscription_id in Stripe subscription metadata: {subscription['id']}")
        return

    query = select(FamilySubscription).where(
        FamilySubscription.id == subscription_id
    )
    result = await db.execute(query)
    our_subscription = result.scalar_one_or_none()

    if not our_subscription:
        logger.warning(f"Subscription {subscription_id} not found in database")
        return

    # Update status based on Stripe status
    stripe_status = subscription.get('status')
    if stripe_status == 'active':
        our_subscription.status = SubscriptionStatus.ACTIVE
    elif stripe_status in ['past_due', 'unpaid']:
        our_subscription.status = SubscriptionStatus.PAST_DUE
    elif stripe_status in ['canceled', 'incomplete_expired']:
        our_subscription.status = SubscriptionStatus.CANCELLED
        our_subscription.cancelled_at = datetime.utcnow()

    await db.flush()
    logger.info(f"Updated subscription {subscription_id} status to {our_subscription.status}")


async def handle_subscription_deleted(subscription: dict, db: AsyncSession):
    """
    Handle customer.subscription.deleted event

    Mark subscription as cancelled
    """
    logger.info(f"Subscription deleted: {subscription['id']}")

    metadata = subscription.get('metadata', {})
    subscription_id = metadata.get('subscription_id')

    if not subscription_id:
        return

    query = select(FamilySubscription).where(
        FamilySubscription.id == subscription_id
    )
    result = await db.execute(query)
    our_subscription = result.scalar_one_or_none()

    if our_subscription:
        our_subscription.status = SubscriptionStatus.CANCELLED
        our_subscription.cancelled_at = datetime.utcnow()
        await db.flush()
        logger.info(f"Cancelled subscription {subscription_id}")
