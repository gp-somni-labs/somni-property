"""
Stripe Payment Processing Service
Handles payment intents, customer management, and webhook processing
"""

import stripe
from typing import Optional, Dict, Any
from decimal import Decimal
import logging

from core.config import settings

logger = logging.getLogger(__name__)


class StripeService:
    """
    Stripe payment processing service

    Handles payment intents, customer management, charges, and webhooks
    """

    def __init__(self):
        """Initialize Stripe with API key"""
        if settings.STRIPE_SECRET_KEY:
            stripe.api_key = settings.STRIPE_SECRET_KEY
            logger.info("Stripe service initialized")
        else:
            logger.warning("Stripe API key not configured - payment processing disabled")

    def _amount_to_cents(self, amount: Decimal) -> int:
        """Convert dollar amount to cents for Stripe"""
        return int(amount * 100)

    def _cents_to_amount(self, cents: int) -> Decimal:
        """Convert cents from Stripe to dollar amount"""
        return Decimal(cents) / 100

    async def create_customer(
        self,
        email: str,
        name: str,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe customer

        Args:
            email: Customer email
            name: Customer name
            phone: Customer phone (optional)
            metadata: Additional metadata (optional)

        Returns:
            Stripe customer object as dict
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                phone=phone,
                metadata=metadata or {}
            )
            logger.info(f"Created Stripe customer: {customer.id}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise

    async def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get Stripe customer by ID"""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve Stripe customer {customer_id}: {e}")
            return None

    async def create_payment_intent(
        self,
        amount: Decimal,
        customer_id: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Payment Intent

        Args:
            amount: Payment amount in dollars
            customer_id: Stripe customer ID
            description: Payment description
            metadata: Additional metadata (e.g., lease_id, payment_id)

        Returns:
            Stripe PaymentIntent object as dict
        """
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=self._amount_to_cents(amount),
                currency=settings.STRIPE_CURRENCY,
                customer=customer_id,
                description=description,
                metadata=metadata or {},
                automatic_payment_methods={'enabled': True}
            )
            logger.info(f"Created Payment Intent: {payment_intent.id} for ${amount}")
            return payment_intent
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create payment intent: {e}")
            raise

    async def get_payment_intent(self, payment_intent_id: str) -> Optional[Dict[str, Any]]:
        """Get Payment Intent by ID"""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return payment_intent
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve payment intent {payment_intent_id}: {e}")
            return None

    async def confirm_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """Confirm a Payment Intent"""
        try:
            payment_intent = stripe.PaymentIntent.confirm(payment_intent_id)
            logger.info(f"Confirmed Payment Intent: {payment_intent_id}")
            return payment_intent
        except stripe.error.StripeError as e:
            logger.error(f"Failed to confirm payment intent {payment_intent_id}: {e}")
            raise

    async def cancel_payment_intent(
        self,
        payment_intent_id: str,
        cancellation_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a Payment Intent"""
        try:
            payment_intent = stripe.PaymentIntent.cancel(
                payment_intent_id,
                cancellation_reason=cancellation_reason
            )
            logger.info(f"Canceled Payment Intent: {payment_intent_id}")
            return payment_intent
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel payment intent {payment_intent_id}: {e}")
            raise

    async def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a refund for a payment

        Args:
            payment_intent_id: Stripe Payment Intent ID
            amount: Refund amount in dollars (None = full refund)
            reason: Refund reason (optional)

        Returns:
            Stripe Refund object as dict
        """
        try:
            refund_params = {
                'payment_intent': payment_intent_id,
                'reason': reason
            }
            if amount is not None:
                refund_params['amount'] = self._amount_to_cents(amount)

            refund = stripe.Refund.create(**refund_params)
            logger.info(f"Created refund {refund.id} for Payment Intent: {payment_intent_id}")
            return refund
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create refund: {e}")
            raise

    async def create_payment_link(
        self,
        amount: Decimal,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Payment Link

        Args:
            amount: Payment amount in dollars
            description: Payment description
            metadata: Additional metadata

        Returns:
            Stripe PaymentLink object as dict
        """
        if not settings.STRIPE_ENABLE_PAYMENT_LINKS:
            raise ValueError("Payment Links are not enabled")

        try:
            # First create a price
            price = stripe.Price.create(
                unit_amount=self._amount_to_cents(amount),
                currency=settings.STRIPE_CURRENCY,
                product_data={'name': description}
            )

            # Then create the payment link
            payment_link = stripe.PaymentLink.create(
                line_items=[{'price': price.id, 'quantity': 1}],
                metadata=metadata or {}
            )
            logger.info(f"Created Payment Link: {payment_link.url}")
            return payment_link
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create payment link: {e}")
            raise

    async def list_customer_payment_methods(
        self,
        customer_id: str,
        payment_method_type: str = "card"
    ) -> list:
        """List payment methods for a customer"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=payment_method_type
            )
            return payment_methods.data
        except stripe.error.StripeError as e:
            logger.error(f"Failed to list payment methods for customer {customer_id}: {e}")
            return []

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> Optional[Dict[str, Any]]:
        """
        Verify Stripe webhook signature

        Args:
            payload: Request body bytes
            signature: Stripe-Signature header value

        Returns:
            Parsed event object or None if verification fails
        """
        if not settings.STRIPE_WEBHOOK_SECRET:
            logger.warning("Stripe webhook secret not configured")
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
            logger.info(f"Verified webhook event: {event['type']}")
            return event
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            return None

    async def handle_webhook_event(self, event: Dict[str, Any]) -> bool:
        """
        Handle Stripe webhook event

        Args:
            event: Stripe event object

        Returns:
            True if event was handled successfully
        """
        event_type = event['type']
        event_data = event['data']['object']

        logger.info(f"Handling Stripe webhook: {event_type}")

        # Handle different event types
        if event_type == 'payment_intent.succeeded':
            payment_intent_id = event_data['id']
            logger.info(f"Payment succeeded: {payment_intent_id}")
            # Update RentPayment status to 'paid'
            # This should be handled by the calling code

        elif event_type == 'payment_intent.payment_failed':
            payment_intent_id = event_data['id']
            logger.warning(f"Payment failed: {payment_intent_id}")
            # Update RentPayment status to 'failed'

        elif event_type == 'charge.refunded':
            charge_id = event_data['id']
            logger.info(f"Charge refunded: {charge_id}")
            # Update RentPayment status to 'refunded'

        elif event_type == 'customer.created':
            customer_id = event_data['id']
            logger.info(f"Customer created: {customer_id}")

        else:
            logger.info(f"Unhandled event type: {event_type}")

        return True


# Global Stripe service instance
stripe_service = StripeService()
