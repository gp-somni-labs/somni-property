"""
Payments API - Rent Payment Management with Stripe Integration
Handles rent payments, Stripe payment processing, and refunds
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
import logging

from db.database import get_db
from db.models import RentPayment, Lease, Tenant
from api.schemas import (
    RentPaymentCreate,
    RentPaymentUpdate,
    RentPaymentResponse,
    RentPaymentListResponse,
    StripePaymentIntentCreate,
    StripePaymentIntentResponse
)
from core.auth import get_auth_user, require_admin, require_manager, get_current_tenant, AuthUser, CurrentTenant
from core.config import settings
from services.stripe_service import stripe_service
from services.websocket_manager import manager as ws_manager
from services.invoiceninja_client import InvoiceNinjaClient, get_invoiceninja_client

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# PAYMENT CRUD OPERATIONS
# ============================================================================

@router.get("", response_model=RentPaymentListResponse)
async def list_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    lease_id: Optional[UUID] = None,
    status: Optional[str] = None,
    due_after: Optional[date] = None,
    due_before: Optional[date] = None,
    building_id: Optional[UUID] = Query(None, description="Filter by building ID"),
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List rent payments with optional filtering

    - **Admin/Manager**: Can see all payments
    - **Tenant**: Can only see their own payments
    - **Filters**: building_id, client_id, lease_id, status, due_after, due_before
    """
    from db.models import Unit, Building, Property

    query = select(RentPayment)

    # Role-based filtering
    if not (auth_user.is_admin or auth_user.is_manager):
        # Tenants can only see their own payments
        # Get tenant's leases
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.auth_user_id == auth_user.username)
        )
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            return RentPaymentListResponse(items=[], total=0, skip=skip, limit=limit)

        # Get tenant's lease IDs
        lease_result = await db.execute(
            select(Lease.id).where(Lease.tenant_id == tenant.id)
        )
        lease_ids = [row[0] for row in lease_result.all()]

        query = query.where(RentPayment.lease_id.in_(lease_ids))

    # Apply filters
    if lease_id:
        query = query.where(RentPayment.lease_id == lease_id)

    if status:
        query = query.where(RentPayment.status == status)

    if due_after:
        query = query.where(RentPayment.due_date >= due_after)

    if due_before:
        query = query.where(RentPayment.due_date <= due_before)

    # Filter by building_id (via unit relationship)
    if building_id:
        query = query.join(Unit, RentPayment.unit_id == Unit.id).where(Unit.building_id == building_id)

    # Filter by client_id (via lease -> unit -> building -> property relationship)
    if client_id:
        query = (query
            .join(Unit, RentPayment.unit_id == Unit.id)
            .join(Building, Unit.building_id == Building.id)
            .join(Property, Building.property_id == Property.id)
            .where(Property.client_id == client_id))

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(RentPayment.due_date.desc())
    result = await db.execute(query)
    payments = result.scalars().all()

    return RentPaymentListResponse(
        items=payments,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/overdue", response_model=RentPaymentListResponse)
async def list_overdue_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List overdue rent payments

    Returns payments where due_date is in the past and status is not 'paid'

    - **Admin/Manager**: Can see all overdue payments
    - **Tenant**: Can only see their own overdue payments
    """
    today = date.today()
    query = select(RentPayment).where(
        and_(
            RentPayment.due_date < today,
            RentPayment.status != "paid"
        )
    )

    # Role-based filtering
    if not (auth_user.is_admin or auth_user.is_manager):
        # Tenants can only see their own payments
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.auth_user_id == auth_user.username)
        )
        tenant = tenant_result.scalar_one_or_none()

        if not tenant:
            return RentPaymentListResponse(items=[], total=0, skip=skip, limit=limit)

        # Get tenant's lease IDs
        lease_result = await db.execute(
            select(Lease.id).where(Lease.tenant_id == tenant.id)
        )
        lease_ids = [row[0] for row in lease_result.all()]

        query = query.where(RentPayment.lease_id.in_(lease_ids))

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(RentPayment.due_date.asc())
    result = await db.execute(query)
    payments = result.scalars().all()

    return RentPaymentListResponse(
        items=payments,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{payment_id}", response_model=RentPaymentResponse)
async def get_payment(
    payment_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get rent payment by ID"""
    result = await db.execute(
        select(RentPayment).where(RentPayment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # Authorization check for tenants
    if not (auth_user.is_admin or auth_user.is_manager):
        # Get lease to check tenant
        lease_result = await db.execute(
            select(Lease).where(Lease.id == payment.lease_id)
        )
        lease = lease_result.scalar_one()

        tenant_result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.id == lease.tenant_id,
                    Tenant.auth_user_id == auth_user.username
                )
            )
        )
        if not tenant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this payment"
            )

    return payment


@router.post("", response_model=RentPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: RentPaymentCreate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new rent payment (Admin/Manager only)

    EPIC D: Payment Linkage Invariants
    - Validates that tenant_id and unit_id match the lease
    - Returns 400 error if inconsistent
    - Database trigger provides additional validation layer
    """
    # Verify lease exists
    lease_result = await db.execute(
        select(Lease).where(Lease.id == payment_data.lease_id)
    )
    lease = lease_result.scalar_one_or_none()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lease not found"
        )

    # EPIC D: Validate payment linkage invariants
    if payment_data.tenant_id != lease.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"tenant_id and unit_id must match the lease. Expected tenant_id={lease.tenant_id}, got {payment_data.tenant_id}"
        )

    if payment_data.unit_id != lease.unit_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"tenant_id and unit_id must match the lease. Expected unit_id={lease.unit_id}, got {payment_data.unit_id}"
        )

    # Create payment
    payment = RentPayment(
        lease_id=payment_data.lease_id,
        tenant_id=payment_data.tenant_id,
        unit_id=payment_data.unit_id,
        amount=payment_data.amount,
        due_date=payment_data.due_date,
        payment_method=payment_data.payment_method,
        notes=payment_data.notes,
        status='pending'
    )

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    logger.info(f"Created payment {payment.id} for lease {lease.id} (tenant: {payment.tenant_id}, unit: {payment.unit_id})")
    return payment


@router.put("/{payment_id}", response_model=RentPaymentResponse)
async def update_payment(
    payment_id: UUID,
    payment_data: RentPaymentUpdate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Update a rent payment (Admin/Manager only)"""
    result = await db.execute(
        select(RentPayment).where(RentPayment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # Update fields
    update_data = payment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payment, field, value)

    payment.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(payment)

    logger.info(f"Updated payment {payment.id}")
    return payment


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment(
    payment_id: UUID,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Delete a rent payment (Admin/Manager only)"""
    result = await db.execute(
        select(RentPayment).where(RentPayment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # Don't allow deletion of paid payments with Stripe
    if payment.stripe_payment_intent_id and payment.status == 'paid':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete paid Stripe payment. Use refund instead."
        )

    await db.delete(payment)
    await db.commit()

    logger.info(f"Deleted payment {payment.id}")


# ============================================================================
# STRIPE PAYMENT PROCESSING
# ============================================================================

@router.post("/{payment_id}/stripe/create-intent", response_model=StripePaymentIntentResponse)
async def create_stripe_payment_intent(
    payment_id: UUID,
    intent_data: StripePaymentIntentCreate,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a Stripe Payment Intent for a rent payment

    This generates a client_secret that can be used to complete payment on the frontend
    """
    # Get payment
    result = await db.execute(
        select(RentPayment).where(RentPayment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    # Authorization check for tenants
    if not (auth_user.is_admin or auth_user.is_manager):
        lease_result = await db.execute(
            select(Lease).where(Lease.id == payment.lease_id)
        )
        lease = lease_result.scalar_one()

        tenant_result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.id == lease.tenant_id,
                    Tenant.auth_user_id == auth_user.username
                )
            )
        )
        if not tenant_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to pay this rent"
            )

    # Check if payment already has a Stripe intent
    if payment.stripe_payment_intent_id:
        # Retrieve existing intent
        existing_intent = await stripe_service.get_payment_intent(payment.stripe_payment_intent_id)
        if existing_intent and existing_intent['status'] in ['requires_payment_method', 'requires_confirmation']:
            return StripePaymentIntentResponse(
                client_secret=existing_intent['client_secret'],
                payment_intent_id=existing_intent['id'],
                amount=stripe_service._cents_to_amount(existing_intent['amount']),
                currency=existing_intent['currency'],
                status=existing_intent['status'],
                publishable_key=settings.STRIPE_PUBLISHABLE_KEY or ""
            )

    # Get lease and tenant for customer creation
    lease_result = await db.execute(
        select(Lease).where(Lease.id == payment.lease_id)
    )
    lease = lease_result.scalar_one()

    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == lease.tenant_id)
    )
    tenant = tenant_result.scalar_one()

    # Get or create Stripe customer
    if not tenant.stripe_customer_id:
        customer = await stripe_service.create_customer(
            email=tenant.email,
            name=f"{tenant.first_name} {tenant.last_name}",
            phone=tenant.phone,
            metadata={'tenant_id': str(tenant.id)}
        )
        tenant.stripe_customer_id = customer['id']
        await db.commit()

    # Create Payment Intent
    payment_intent = await stripe_service.create_payment_intent(
        amount=payment.amount + payment.late_fee_charged,
        customer_id=tenant.stripe_customer_id,
        description=f"Rent payment for lease {lease.id}",
        metadata={
            'payment_id': str(payment.id),
            'lease_id': str(lease.id),
            'tenant_id': str(tenant.id)
        }
    )

    # Update payment with Stripe details
    payment.stripe_payment_intent_id = payment_intent['id']
    payment.stripe_customer_id = tenant.stripe_customer_id
    payment.stripe_status = payment_intent['status']
    payment.payment_method = 'stripe'
    payment.status = 'processing'
    await db.commit()

    logger.info(f"Created Stripe Payment Intent {payment_intent['id']} for payment {payment.id}")

    return StripePaymentIntentResponse(
        client_secret=payment_intent['client_secret'],
        payment_intent_id=payment_intent['id'],
        amount=payment.amount + payment.late_fee_charged,
        currency=payment_intent['currency'],
        status=payment_intent['status'],
        publishable_key=settings.STRIPE_PUBLISHABLE_KEY or ""
    )


@router.post("/{payment_id}/stripe/refund", response_model=RentPaymentResponse)
async def refund_stripe_payment(
    payment_id: UUID,
    amount: Optional[Decimal] = None,
    reason: Optional[str] = None,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Refund a Stripe payment (Admin/Manager only)

    - **amount**: Refund amount (None = full refund)
    - **reason**: Refund reason
    """
    result = await db.execute(
        select(RentPayment).where(RentPayment.id == payment_id)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if not payment.stripe_payment_intent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment was not processed through Stripe"
        )

    if payment.status != 'paid':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paid payments can be refunded"
        )

    # Create refund
    try:
        refund = await stripe_service.create_refund(
            payment_intent_id=payment.stripe_payment_intent_id,
            amount=amount,
            reason=reason
        )

        # Update payment status
        payment.status = 'refunded'
        payment.stripe_status = 'refunded'
        payment.notes = (payment.notes or "") + f"\nRefunded: {refund['id']}"
        await db.commit()
        await db.refresh(payment)

        logger.info(f"Refunded payment {payment.id}: {refund['id']}")
        return payment

    except Exception as e:
        logger.error(f"Failed to refund payment {payment.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process refund: {str(e)}"
        )


# ============================================================================
# PAYMENT STATISTICS
# ============================================================================

@router.get("/statistics/overview")
async def get_payment_statistics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment statistics (Admin/Manager only)

    Returns:
    - total_collected: Total amount collected
    - total_pending: Total amount pending
    - total_late: Total amount late
    - payment_count: Number of payments
    """
    query = select(RentPayment)

    if start_date:
        query = query.where(RentPayment.due_date >= start_date)

    if end_date:
        query = query.where(RentPayment.due_date <= end_date)

    result = await db.execute(query)
    payments = result.scalars().all()

    total_collected = sum(p.amount for p in payments if p.status == 'paid')
    total_pending = sum(p.amount for p in payments if p.status == 'pending')
    total_late = sum(p.amount for p in payments if p.status == 'late')
    late_fees = sum(p.late_fee_charged for p in payments)

    return {
        "total_collected": float(total_collected),
        "total_pending": float(total_pending),
        "total_late": float(total_late),
        "late_fees_charged": float(late_fees),
        "payment_count": len(payments),
        "paid_count": sum(1 for p in payments if p.status == 'paid'),
        "pending_count": sum(1 for p in payments if p.status == 'pending'),
        "late_count": sum(1 for p in payments if p.status == 'late')
    }


@router.get("/reports/summary")
async def get_payment_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment summary report (Admin/Manager only)

    Returns summary statistics for dashboard display:
    - total_collected: Total amount collected (paid status)
    - total_pending: Total amount pending
    - total_overdue: Total amount overdue (late status)
    - total_refunded: Total amount refunded
    - payment_count: Total number of payments
    """
    query = select(RentPayment)

    if start_date:
        query = query.where(RentPayment.due_date >= start_date)

    if end_date:
        query = query.where(RentPayment.due_date <= end_date)

    result = await db.execute(query)
    payments = result.scalars().all()

    total_collected = sum(p.amount for p in payments if p.status == 'paid')
    total_pending = sum(p.amount for p in payments if p.status == 'pending')
    total_overdue = sum(p.amount for p in payments if p.status == 'late')
    total_refunded = sum(p.amount for p in payments if p.status == 'refunded')

    return {
        "total_collected": float(total_collected),
        "total_pending": float(total_pending),
        "total_overdue": float(total_overdue),
        "total_refunded": float(total_refunded),
        "payment_count": len(payments)
    }


# ============================================================================
# STRIPE WEBHOOKS
# ============================================================================

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
    invoiceninja: InvoiceNinjaClient = Depends(get_invoiceninja_client)
):
    """
    Stripe webhook endpoint

    Handles Stripe events like payment_intent.succeeded, payment_intent.failed, etc.
    """
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )

    # Get raw body
    body = await request.body()

    # Verify webhook signature
    event = stripe_service.verify_webhook_signature(body, stripe_signature)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature"
        )

    event_type = event['type']
    event_data = event['data']['object']

    logger.info(f"Received Stripe webhook: {event_type}")

    # Handle payment_intent.succeeded
    if event_type == 'payment_intent.succeeded':
        payment_intent_id = event_data['id']
        metadata = event_data.get('metadata', {})
        payment_id = metadata.get('payment_id')

        if payment_id:
            result = await db.execute(
                select(RentPayment).where(RentPayment.id == UUID(payment_id))
            )
            payment = result.scalar_one_or_none()

            if payment:
                payment.status = 'paid'
                payment.paid_date = date.today()
                payment.stripe_status = 'succeeded'
                payment.stripe_charge_id = event_data.get('latest_charge')
                await db.commit()

                logger.info(f"Payment {payment_id} marked as paid via webhook")

                # Mark invoice as paid in Invoice Ninja if it exists
                if payment.invoiceninja_invoice_id:
                    try:
                        success = await invoiceninja.mark_invoice_paid(
                            invoice_id=payment.invoiceninja_invoice_id,
                            amount=payment.amount,
                            payment_date=payment.paid_date,
                            payment_type="Credit Card",
                            transaction_reference=payment.stripe_charge_id
                        )
                        if success:
                            logger.info(f"Marked Invoice Ninja invoice {payment.invoiceninja_invoice_id} as paid")
                        else:
                            logger.warning(f"Failed to mark Invoice Ninja invoice {payment.invoiceninja_invoice_id} as paid")
                    except Exception as e:
                        # Non-fatal - payment is already marked as paid in our system
                        logger.error(f"Error updating Invoice Ninja: {e}")

                # Send WebSocket notification
                tenant_id = metadata.get('tenant_id')
                if tenant_id:
                    await ws_manager.send_payment_update(
                        payment_id=payment.id,
                        status='paid',
                        user_id=tenant_id,
                        amount=float(payment.amount)
                    )

    # Handle payment_intent.payment_failed
    elif event_type == 'payment_intent.payment_failed':
        payment_intent_id = event_data['id']
        metadata = event_data.get('metadata', {})
        payment_id = metadata.get('payment_id')

        if payment_id:
            result = await db.execute(
                select(RentPayment).where(RentPayment.id == UUID(payment_id))
            )
            payment = result.scalar_one_or_none()

            if payment:
                payment.status = 'failed'
                payment.stripe_status = 'failed'
                error_message = event_data.get('last_payment_error', {}).get('message', 'Unknown error')
                payment.notes = (payment.notes or "") + f"\nPayment failed: {error_message}"
                await db.commit()

                logger.warning(f"Payment {payment_id} marked as failed via webhook")

                # Send WebSocket notification
                tenant_id = metadata.get('tenant_id')
                if tenant_id:
                    await ws_manager.send_payment_update(
                        payment_id=payment.id,
                        status='failed',
                        user_id=tenant_id,
                        amount=float(payment.amount)
                    )

    # Handle charge.refunded
    elif event_type == 'charge.refunded':
        charge_id = event_data['id']
        payment_intent_id = event_data.get('payment_intent')

        if payment_intent_id:
            result = await db.execute(
                select(RentPayment).where(RentPayment.stripe_payment_intent_id == payment_intent_id)
            )
            payment = result.scalar_one_or_none()

            if payment:
                payment.status = 'refunded'
                payment.stripe_status = 'refunded'
                await db.commit()

                logger.info(f"Payment {payment.id} marked as refunded via webhook")

                # Send WebSocket notification
                # Get tenant_id from lease
                lease_result = await db.execute(
                    select(Lease).where(Lease.id == payment.lease_id)
                )
                lease = lease_result.scalar_one_or_none()
                if lease:
                    await ws_manager.send_payment_update(
                        payment_id=payment.id,
                        status='refunded',
                        user_id=str(lease.tenant_id),
                        amount=float(payment.amount)
                    )

    return {"status": "success", "event_type": event_type}
