"""
MRR/Analytics Dashboard API
Provides Monthly Recurring Revenue metrics and subscription analytics for MSP operations
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date
from decimal import Decimal
import logging

from db.database import get_db
from db.family_models import (
    FamilySubscription,
    FamilyBilling,
    SubscriptionStatus,
    SubscriptionTier
)
from db.models import Client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/analytics/mrr")
async def get_mrr_metrics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get Monthly Recurring Revenue (MRR) metrics

    Returns:
        - current_mrr: Total MRR from all active subscriptions
        - mrr_growth: MRR change vs. previous month
        - new_mrr: MRR from new subscriptions this month
        - expansion_mrr: MRR increase from upgrades/add-ons
        - churned_mrr: MRR lost from cancellations
        - active_subscriptions: Count of active subscriptions
        - mrr_by_tier: Breakdown by subscription tier
        - monthly_trend: MRR for last 12 months
    """

    # Get current month start/end
    today = datetime.utcnow()
    current_month_start = datetime(today.year, today.month, 1)

    # Calculate previous month
    if today.month == 1:
        prev_month_start = datetime(today.year - 1, 12, 1)
        prev_month_end = datetime(today.year, 1, 1) - timedelta(days=1)
    else:
        prev_month_start = datetime(today.year, today.month - 1, 1)
        prev_month_end = current_month_start - timedelta(days=1)

    # Current MRR: Sum of all active subscription base prices + add-ons
    query = select(FamilySubscription).where(
        FamilySubscription.status == SubscriptionStatus.ACTIVE
    )
    result = await db.execute(query)
    active_subscriptions = result.scalars().all()

    current_mrr = 0.0
    mrr_by_tier = {
        SubscriptionTier.STARTER: 0.0,
        SubscriptionTier.PRO: 0.0,
        SubscriptionTier.ENTERPRISE: 0.0
    }

    for subscription in active_subscriptions:
        # Base price
        subscription_mrr = float(subscription.base_price)

        # Add add-ons
        if subscription.addons:
            for addon_id, addon_data in subscription.addons.items():
                # Skip internal fields
                if addon_id.startswith('_'):
                    continue
                if isinstance(addon_data, dict) and 'price' in addon_data:
                    subscription_mrr += float(addon_data['price'])

        current_mrr += subscription_mrr
        mrr_by_tier[subscription.tier] += subscription_mrr

    active_count = len(active_subscriptions)

    # New MRR: Subscriptions created this month
    query = select(FamilySubscription).where(
        and_(
            FamilySubscription.created_at >= current_month_start,
            FamilySubscription.status == SubscriptionStatus.ACTIVE
        )
    )
    result = await db.execute(query)
    new_subscriptions = result.scalars().all()

    new_mrr = 0.0
    for subscription in new_subscriptions:
        subscription_mrr = float(subscription.base_price)
        if subscription.addons:
            for addon_id, addon_data in subscription.addons.items():
                if addon_id.startswith('_'):
                    continue
                if isinstance(addon_data, dict) and 'price' in addon_data:
                    subscription_mrr += float(addon_data['price'])
        new_mrr += subscription_mrr

    # Churned MRR: Subscriptions cancelled this month
    query = select(FamilySubscription).where(
        and_(
            FamilySubscription.cancelled_at >= current_month_start,
            FamilySubscription.status == SubscriptionStatus.CANCELLED
        )
    )
    result = await db.execute(query)
    churned_subscriptions = result.scalars().all()

    churned_mrr = 0.0
    for subscription in churned_subscriptions:
        subscription_mrr = float(subscription.base_price)
        if subscription.addons:
            for addon_id, addon_data in subscription.addons.items():
                if addon_id.startswith('_'):
                    continue
                if isinstance(addon_data, dict) and 'price' in addon_data:
                    subscription_mrr += float(addon_data['price'])
        churned_mrr += subscription_mrr

    # Expansion MRR: Upgrades and add-ons added this month
    # This would require tracking subscription changes in a history table
    # For now, we'll estimate as 0 (TODO: implement subscription change tracking)
    expansion_mrr = 0.0

    # Previous month MRR (for growth calculation)
    # This is a simplified calculation - ideally we'd have historical snapshots
    prev_month_mrr = current_mrr - new_mrr + churned_mrr - expansion_mrr

    # MRR growth
    if prev_month_mrr > 0:
        mrr_growth = ((current_mrr - prev_month_mrr) / prev_month_mrr) * 100
    else:
        mrr_growth = 100.0 if current_mrr > 0 else 0.0

    # Monthly trend (last 12 months)
    # For now, simplified - ideally we'd query historical billing data
    monthly_trend = []
    for i in range(11, -1, -1):
        month_date = today - timedelta(days=30 * i)
        month_key = month_date.strftime("%Y-%m")

        # This is a placeholder - proper implementation would query billing history
        # For now, show current MRR for all months
        monthly_trend.append({
            "month": month_key,
            "mrr": round(current_mrr, 2)
        })

    return {
        "current_mrr": round(current_mrr, 2),
        "mrr_growth": round(mrr_growth, 2),
        "new_mrr": round(new_mrr, 2),
        "expansion_mrr": round(expansion_mrr, 2),
        "churned_mrr": round(churned_mrr, 2),
        "active_subscriptions": active_count,
        "mrr_by_tier": {
            "starter": round(mrr_by_tier[SubscriptionTier.STARTER], 2),
            "pro": round(mrr_by_tier[SubscriptionTier.PRO], 2),
            "enterprise": round(mrr_by_tier[SubscriptionTier.ENTERPRISE], 2)
        },
        "monthly_trend": monthly_trend
    }


@router.get("/analytics/subscriptions")
async def get_subscription_breakdown(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get subscription breakdown metrics

    Returns:
        - total_subscriptions: Total count
        - by_status: Breakdown by status (active, past_due, cancelled, etc.)
        - by_tier: Breakdown by tier (starter, professional, enterprise)
        - by_client_type: Breakdown by client type (multi-unit vs single-family)
        - average_subscription_value: Average MRR per subscription
    """

    # Get all subscriptions
    query = select(FamilySubscription)
    result = await db.execute(query)
    all_subscriptions = result.scalars().all()

    # Initialize counters
    by_status = {
        "active": 0,
        "past_due": 0,
        "cancelled": 0,
        "trial": 0
    }

    by_tier = {
        "starter": 0,
        "professional": 0,
        "enterprise": 0
    }

    by_client_type = {
        "multi-unit": 0,
        "single-family": 0
    }

    total_mrr = 0.0

    # Get client info for client_type breakdown
    client_ids = [sub.client_id for sub in all_subscriptions]
    if client_ids:
        query = select(Client).where(Client.id.in_(client_ids))
        result = await db.execute(query)
        clients = {client.id: client for client in result.scalars().all()}
    else:
        clients = {}

    # Count subscriptions by various dimensions
    for subscription in all_subscriptions:
        # Status
        status_key = subscription.status.value if subscription.status else "unknown"
        by_status[status_key] = by_status.get(status_key, 0) + 1

        # Tier
        tier_key = subscription.tier.value if subscription.tier else "unknown"
        by_tier[tier_key] = by_tier.get(tier_key, 0) + 1

        # Client type
        client = clients.get(subscription.client_id)
        if client and hasattr(client, 'client_type'):
            client_type = client.client_type
            by_client_type[client_type] = by_client_type.get(client_type, 0) + 1

        # Calculate MRR
        subscription_mrr = float(subscription.base_price)
        if subscription.addons:
            for addon_id, addon_data in subscription.addons.items():
                if addon_id.startswith('_'):
                    continue
                if isinstance(addon_data, dict) and 'price' in addon_data:
                    subscription_mrr += float(addon_data['price'])
        total_mrr += subscription_mrr

    # Calculate average
    avg_subscription_value = total_mrr / len(all_subscriptions) if all_subscriptions else 0.0

    return {
        "total_subscriptions": len(all_subscriptions),
        "by_status": by_status,
        "by_tier": by_tier,
        "by_client_type": by_client_type,
        "average_subscription_value": round(avg_subscription_value, 2)
    }


@router.get("/analytics/churn")
async def get_churn_metrics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get churn rate and retention metrics

    Returns:
        - monthly_churn_rate: Percentage of subscriptions cancelled this month
        - customer_churn_rate: Percentage of customers lost this month
        - mrr_churn_rate: Percentage of MRR lost this month
        - cancelled_this_month: Count of cancellations
        - churned_mrr: MRR lost from cancellations
        - retention_rate: Percentage of customers retained
        - avg_customer_lifetime: Average months a customer stays subscribed
    """

    # Get current month start
    today = datetime.utcnow()
    current_month_start = datetime(today.year, today.month, 1)

    # Get all active subscriptions at start of month
    # This is simplified - ideally we'd have historical snapshots
    query = select(FamilySubscription).where(
        FamilySubscription.created_at < current_month_start
    )
    result = await db.execute(query)
    subscriptions_at_month_start = len(result.scalars().all())

    # Get cancellations this month
    query = select(FamilySubscription).where(
        and_(
            FamilySubscription.cancelled_at >= current_month_start,
            FamilySubscription.status == SubscriptionStatus.CANCELLED
        )
    )
    result = await db.execute(query)
    cancelled_subscriptions = result.scalars().all()
    cancelled_count = len(cancelled_subscriptions)

    # Calculate churned MRR
    churned_mrr = 0.0
    for subscription in cancelled_subscriptions:
        subscription_mrr = float(subscription.base_price)
        if subscription.addons:
            for addon_id, addon_data in subscription.addons.items():
                if addon_id.startswith('_'):
                    continue
                if isinstance(addon_data, dict) and 'price' in addon_data:
                    subscription_mrr += float(addon_data['price'])
        churned_mrr += subscription_mrr

    # Get current active MRR
    query = select(FamilySubscription).where(
        FamilySubscription.status == SubscriptionStatus.ACTIVE
    )
    result = await db.execute(query)
    active_subscriptions = result.scalars().all()

    current_mrr = 0.0
    for subscription in active_subscriptions:
        subscription_mrr = float(subscription.base_price)
        if subscription.addons:
            for addon_id, addon_data in subscription.addons.items():
                if addon_id.startswith('_'):
                    continue
                if isinstance(addon_data, dict) and 'price' in addon_data:
                    subscription_mrr += float(addon_data['price'])
        current_mrr += subscription_mrr

    # Calculate churn rates
    if subscriptions_at_month_start > 0:
        monthly_churn_rate = (cancelled_count / subscriptions_at_month_start) * 100
    else:
        monthly_churn_rate = 0.0

    customer_churn_rate = monthly_churn_rate  # Same for subscriptions

    total_mrr_at_start = current_mrr + churned_mrr
    if total_mrr_at_start > 0:
        mrr_churn_rate = (churned_mrr / total_mrr_at_start) * 100
    else:
        mrr_churn_rate = 0.0

    retention_rate = 100.0 - monthly_churn_rate

    # Average customer lifetime (simplified calculation)
    # Ideally: average(cancellation_date - created_date) for all cancelled subscriptions
    # For now, estimate based on current active subscriptions
    if active_subscriptions:
        total_months = 0
        for subscription in active_subscriptions:
            months = (today - subscription.created_at).days / 30
            total_months += months
        avg_customer_lifetime = total_months / len(active_subscriptions)
    else:
        avg_customer_lifetime = 0.0

    return {
        "monthly_churn_rate": round(monthly_churn_rate, 2),
        "customer_churn_rate": round(customer_churn_rate, 2),
        "mrr_churn_rate": round(mrr_churn_rate, 2),
        "cancelled_this_month": cancelled_count,
        "churned_mrr": round(churned_mrr, 2),
        "retention_rate": round(retention_rate, 2),
        "avg_customer_lifetime_months": round(avg_customer_lifetime, 1)
    }


@router.get("/analytics/revenue")
async def get_revenue_metrics(
    db: AsyncSession = Depends(get_db),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get revenue metrics from billing records

    Query params:
        - start_date: ISO date string (default: 30 days ago)
        - end_date: ISO date string (default: today)

    Returns:
        - total_revenue: Total revenue in period
        - paid_invoices: Count of paid invoices
        - pending_invoices: Count of pending invoices
        - failed_invoices: Count of failed invoices
        - average_invoice_value: Average invoice amount
        - revenue_by_tier: Revenue breakdown by subscription tier
    """

    # Parse dates
    if end_date:
        end_dt = datetime.fromisoformat(end_date)
    else:
        end_dt = datetime.utcnow()

    if start_date:
        start_dt = datetime.fromisoformat(start_date)
    else:
        start_dt = end_dt - timedelta(days=30)

    # Get billing records in date range
    query = select(FamilyBilling).where(
        and_(
            FamilyBilling.billing_date >= start_dt,
            FamilyBilling.billing_date <= end_dt
        )
    )
    result = await db.execute(query)
    billing_records = result.scalars().all()

    # Calculate metrics
    total_revenue = 0.0
    paid_count = 0
    pending_count = 0
    failed_count = 0
    revenue_by_tier = {
        "starter": 0.0,
        "professional": 0.0,
        "enterprise": 0.0
    }

    # Get subscription info for tier breakdown
    subscription_ids = [bill.subscription_id for bill in billing_records if bill.subscription_id]
    if subscription_ids:
        query = select(FamilySubscription).where(FamilySubscription.id.in_(subscription_ids))
        result = await db.execute(query)
        subscriptions = {sub.id: sub for sub in result.scalars().all()}
    else:
        subscriptions = {}

    for billing in billing_records:
        amount = float(billing.amount_due)

        if billing.paid:
            total_revenue += amount
            paid_count += 1

            # Add to tier breakdown
            subscription = subscriptions.get(billing.subscription_id)
            if subscription:
                tier_key = subscription.tier.value
                revenue_by_tier[tier_key] = revenue_by_tier.get(tier_key, 0) + amount

        if hasattr(billing, 'status'):
            if billing.status == 'pending':
                pending_count += 1
            elif billing.status == 'failed':
                failed_count += 1

    avg_invoice_value = total_revenue / paid_count if paid_count > 0 else 0.0

    return {
        "total_revenue": round(total_revenue, 2),
        "paid_invoices": paid_count,
        "pending_invoices": pending_count,
        "failed_invoices": failed_count,
        "average_invoice_value": round(avg_invoice_value, 2),
        "revenue_by_tier": {
            "starter": round(revenue_by_tier.get("starter", 0), 2),
            "professional": round(revenue_by_tier.get("professional", 0), 2),
            "enterprise": round(revenue_by_tier.get("enterprise", 0), 2)
        },
        "period": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat()
        }
    }


@router.get("/analytics/summary")
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get comprehensive analytics summary for dashboard

    Returns all key metrics in a single call:
        - MRR metrics
        - Subscription breakdown
        - Churn metrics
        - Revenue metrics (last 30 days)
    """

    # Get all metrics
    mrr = await get_mrr_metrics(db)
    subscriptions = await get_subscription_breakdown(db)
    churn = await get_churn_metrics(db)
    revenue = await get_revenue_metrics(db)

    return {
        "mrr": mrr,
        "subscriptions": subscriptions,
        "churn": churn,
        "revenue": revenue,
        "generated_at": datetime.utcnow().isoformat()
    }
