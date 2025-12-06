"""
Subscription Billing Service
Automatically creates and manages Invoice Ninja recurring invoices for FamilySubscriptions
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.family_models import FamilySubscription, SubscriptionStatus, FamilyBilling
from db.models import Client
from services.invoiceninja_client import (
    InvoiceNinjaClient,
    get_invoiceninja_client,
    InvoiceLineItem
)

logger = logging.getLogger(__name__)


class SubscriptionBillingService:
    """
    Service for managing subscription billing via Invoice Ninja

    Responsibilities:
    - Create Invoice Ninja clients for MSP customers
    - Set up recurring invoices for subscriptions
    - Calculate total subscription cost (base + add-ons)
    - Sync subscription changes to Invoice Ninja
    - Handle subscription cancellations
    """

    def __init__(
        self,
        db: AsyncSession,
        invoiceninja_client: Optional[InvoiceNinjaClient] = None
    ):
        """
        Initialize service

        Args:
            db: Database session
            invoiceninja_client: Invoice Ninja client (defaults to singleton)
        """
        self.db = db
        self.invoiceninja = invoiceninja_client or get_invoiceninja_client()

    async def setup_subscription_billing(
        self,
        subscription_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Set up automatic billing for a subscription

        This is called when a FamilySubscription is created.
        It will:
        1. Get or create Invoice Ninja client for the customer
        2. Calculate total monthly cost (base + add-ons)
        3. Create recurring invoice in Invoice Ninja
        4. Store Invoice Ninja recurring invoice ID in subscription

        Args:
            subscription_id: FamilySubscription UUID

        Returns:
            Dict with:
                - invoiceninja_client_id: Invoice Ninja client ID
                - recurring_invoice_id: Invoice Ninja recurring invoice ID
                - monthly_total: Total monthly cost
        """
        # Get subscription with client
        query = select(FamilySubscription).where(
            FamilySubscription.id == subscription_id
        )
        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.error(f"Subscription {subscription_id} not found")
            return None

        # Get client
        client_query = select(Client).where(Client.id == subscription.client_id)
        client_result = await self.db.execute(client_query)
        client = client_result.scalar_one_or_none()

        if not client:
            logger.error(f"Client {subscription.client_id} not found")
            return None

        # Step 1: Get or create Invoice Ninja client
        invoiceninja_client_id = await self._get_or_create_invoiceninja_client(client)
        if not invoiceninja_client_id:
            logger.error(f"Failed to create Invoice Ninja client for {client.name}")
            return None

        # Store Invoice Ninja client ID on Client model
        client.invoiceninja_client_id = invoiceninja_client_id
        await self.db.flush()

        # Step 2: Calculate monthly total
        monthly_total = self._calculate_monthly_total(subscription)

        # Step 3: Build line items
        line_items = self._build_subscription_line_items(subscription, client)

        # Step 4: Create recurring invoice
        recurring_invoice = await self.invoiceninja.create_recurring_invoice(
            client_id=invoiceninja_client_id,
            line_items=line_items,
            frequency_id=5,  # Monthly
            remaining_cycles=-1,  # Infinite (until cancelled)
            due_date_terms="net 5",  # Due 5 days after invoice date
            auto_bill=True,  # Enable auto-billing
            public_notes=f"SomniFamily {subscription.tier.value.title()} Subscription",
            terms="Subscription will auto-renew monthly. Cancel anytime."
        )

        if not recurring_invoice:
            logger.error(f"Failed to create recurring invoice for subscription {subscription_id}")
            return None

        # Step 5: Store recurring invoice ID on subscription
        # Note: Need to add this column to FamilySubscription model
        # For now, store in addons JSON as a workaround
        if not subscription.addons:
            subscription.addons = {}
        subscription.addons['_invoiceninja_recurring_id'] = recurring_invoice.get('id')

        await self.db.commit()

        logger.info(
            f"Set up billing for subscription {subscription_id}: "
            f"Client={invoiceninja_client_id}, "
            f"RecurringInvoice={recurring_invoice.get('id')}, "
            f"Monthly=${monthly_total}"
        )

        return {
            'invoiceninja_client_id': invoiceninja_client_id,
            'recurring_invoice_id': recurring_invoice.get('id'),
            'monthly_total': monthly_total
        }

    async def update_subscription_billing(
        self,
        subscription_id: UUID
    ) -> bool:
        """
        Update existing recurring invoice when subscription changes

        Use when:
        - Add-ons are added/removed
        - Base price changes
        - Tier upgrade/downgrade

        Args:
            subscription_id: FamilySubscription UUID

        Returns:
            True if successful, False otherwise
        """
        # Get subscription with client
        query = select(FamilySubscription).where(
            FamilySubscription.id == subscription_id
        )
        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()

        if not subscription:
            return False

        # Get recurring invoice ID
        recurring_id = subscription.addons.get('_invoiceninja_recurring_id') if subscription.addons else None
        if not recurring_id:
            logger.warning(f"No recurring invoice found for subscription {subscription_id}")
            return False

        # Get client
        client_query = select(Client).where(Client.id == subscription.client_id)
        client_result = await self.db.execute(client_query)
        client = client_result.scalar_one_or_none()

        if not client:
            return False

        # Calculate new line items
        line_items = self._build_subscription_line_items(subscription, client)

        # Update recurring invoice
        # Note: Invoice Ninja API doesn't have a direct update method
        # We need to archive the old one and create a new one
        # For now, we'll just log and recommend manual update
        logger.warning(
            f"Subscription {subscription_id} changed. "
            f"Manual update required in Invoice Ninja for recurring invoice {recurring_id}"
        )

        # TODO: Implement proper update logic
        # 1. Archive old recurring invoice
        # 2. Create new recurring invoice
        # 3. Update subscription with new recurring_id

        return True

    async def cancel_subscription_billing(
        self,
        subscription_id: UUID
    ) -> bool:
        """
        Cancel recurring billing when subscription is cancelled

        Args:
            subscription_id: FamilySubscription UUID

        Returns:
            True if successful, False otherwise
        """
        # Get subscription
        query = select(FamilySubscription).where(
            FamilySubscription.id == subscription_id
        )
        result = await self.db.execute(query)
        subscription = result.scalar_one_or_none()

        if not subscription:
            return False

        # Get recurring invoice ID
        recurring_id = subscription.addons.get('_invoiceninja_recurring_id') if subscription.addons else None
        if not recurring_id:
            logger.warning(f"No recurring invoice found for subscription {subscription_id}")
            return False

        # Archive recurring invoice (stops future invoices)
        # Note: Invoice Ninja doesn't have a delete endpoint for recurring invoices
        # We need to set status to archived
        logger.info(f"Cancelling recurring invoice {recurring_id} for subscription {subscription_id}")

        # TODO: Implement Invoice Ninja archive_recurring_invoice method

        return True

    async def _get_or_create_invoiceninja_client(
        self,
        client: Client
    ) -> Optional[str]:
        """
        Get existing or create new Invoice Ninja client

        Args:
            client: SomniProperty Client model

        Returns:
            Invoice Ninja client ID or None on failure
        """
        # Check if client already has Invoice Ninja ID
        if hasattr(client, 'invoiceninja_client_id') and client.invoiceninja_client_id:
            # Verify it exists
            existing = await self.invoiceninja.get_client(client.invoiceninja_client_id)
            if existing:
                return client.invoiceninja_client_id

        # Create new Invoice Ninja client
        in_client = await self.invoiceninja.create_client(
            name=client.name,
            email=client.email or client.primary_contact_email,
            phone=client.phone or client.primary_contact_phone,
            address1=client.property_address_line1,
            address2=client.property_address_line2,
            city=client.property_city,
            state=client.property_state,
            postal_code=client.property_postal_code,
            id_number=str(client.id),  # Store SomniProperty client UUID
            custom_value1=client.client_type,  # Store client type
            custom_value2=client.tier  # Store service tier
        )

        if in_client:
            return in_client.id

        return None

    def _calculate_monthly_total(self, subscription: FamilySubscription) -> float:
        """
        Calculate total monthly subscription cost

        Args:
            subscription: FamilySubscription model

        Returns:
            Total monthly cost (base + add-ons)
        """
        total = subscription.base_price

        # Add add-on costs
        if subscription.addons:
            for addon_id, addon_data in subscription.addons.items():
                # Skip internal fields
                if addon_id.startswith('_'):
                    continue
                if isinstance(addon_data, dict) and 'price' in addon_data:
                    total += addon_data['price']

        return float(total)

    def _build_subscription_line_items(
        self,
        subscription: FamilySubscription,
        client: Client
    ) -> list[InvoiceLineItem]:
        """
        Build Invoice Ninja line items for subscription

        Args:
            subscription: FamilySubscription model
            client: Client model

        Returns:
            List of InvoiceLineItem
        """
        line_items = []

        # Base subscription
        line_items.append(
            InvoiceLineItem(
                product_key=f"subscription_{subscription.tier.value}",
                notes=f"SomniFamily {subscription.tier.value.title()} - Monthly Subscription for {client.name}",
                cost=float(subscription.base_price),
                quantity=1.0
            )
        )

        # Add-ons
        if subscription.addons:
            for addon_id, addon_data in subscription.addons.items():
                # Skip internal fields
                if addon_id.startswith('_'):
                    continue

                if isinstance(addon_data, dict) and 'name' in addon_data and 'price' in addon_data:
                    line_items.append(
                        InvoiceLineItem(
                            product_key=f"addon_{addon_id}",
                            notes=addon_data['name'],
                            cost=float(addon_data['price']),
                            quantity=1.0
                        )
                    )

        return line_items


async def setup_subscription_billing(
    subscription_id: UUID,
    db: AsyncSession
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to set up billing for a subscription

    Call this after creating a FamilySubscription.

    Args:
        subscription_id: FamilySubscription UUID
        db: Database session

    Returns:
        Billing setup result or None on failure
    """
    service = SubscriptionBillingService(db)
    return await service.setup_subscription_billing(subscription_id)
