"""
Dashboard Statistics API

Aggregated statistics endpoint for SomniProperty dashboard cards.
Returns metrics for:
- Property Hubs and Residential Hubs (by status)
- Open Work Orders (by priority)
- Critical Alerts (24h)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Dict
from pydantic import BaseModel

from db.database import get_db
from db.models import PropertyEdgeNode, WorkOrder, Alert


router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class HubBreakdown(BaseModel):
    """Hub status breakdown"""
    total: int = 0
    healthy: int = 0
    degraded: int = 0
    offline: int = 0


class DashboardStats(BaseModel):
    """Dashboard statistics response"""
    property_hubs: HubBreakdown
    residential_hubs: HubBreakdown
    open_work_orders: Dict[str, int]  # {"low": 4, "medium": 7, "high": 2, "emergency": 1}
    critical_alerts_24h: int
    timestamp: datetime


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("", response_model=DashboardStats)
@router.get("/", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Get aggregated dashboard statistics

    Returns:
    - Property Hub breakdown (total, healthy, degraded, offline)
    - Residential Hub breakdown (total, healthy, degraded, offline)
    - Open work orders by priority
    - Critical alerts in last 24 hours
    """

    # Initialize response with zeros
    stats = DashboardStats(
        property_hubs=HubBreakdown(),
        residential_hubs=HubBreakdown(),
        open_work_orders={"low": 0, "medium": 0, "high": 0, "emergency": 0},
        critical_alerts_24h=0,
        timestamp=datetime.utcnow()
    )

    # ========================================================================
    # 1. Property Hubs (PROPERTY_HUB type)
    # ========================================================================
    property_hubs_query = select(
        PropertyEdgeNode.status,
        func.count(PropertyEdgeNode.id).label('count')
    ).where(
        PropertyEdgeNode.hub_type == 'PROPERTY_HUB'
    ).group_by(PropertyEdgeNode.status)

    result = await db.execute(property_hubs_query)
    property_hub_stats = result.all()

    for status, count in property_hub_stats:
        stats.property_hubs.total += count
        if status == 'online':
            stats.property_hubs.healthy = count
        elif status == 'error':
            stats.property_hubs.degraded = count
        elif status == 'offline':
            stats.property_hubs.offline = count

    # ========================================================================
    # 2. Residential Hubs (RESIDENTIAL type)
    # ========================================================================
    residential_hubs_query = select(
        PropertyEdgeNode.status,
        func.count(PropertyEdgeNode.id).label('count')
    ).where(
        PropertyEdgeNode.hub_type == 'RESIDENTIAL'
    ).group_by(PropertyEdgeNode.status)

    result = await db.execute(residential_hubs_query)
    residential_hub_stats = result.all()

    for status, count in residential_hub_stats:
        stats.residential_hubs.total += count
        if status == 'online':
            stats.residential_hubs.healthy = count
        elif status == 'error':
            stats.residential_hubs.degraded = count
        elif status == 'offline':
            stats.residential_hubs.offline = count

    # ========================================================================
    # 3. Open Work Orders by Priority
    # ========================================================================
    work_orders_query = select(
        WorkOrder.priority,
        func.count(WorkOrder.id).label('count')
    ).where(
        WorkOrder.status.in_(['open', 'assigned', 'in_progress'])
    ).group_by(WorkOrder.priority)

    result = await db.execute(work_orders_query)
    work_order_stats = result.all()

    for priority, count in work_order_stats:
        if priority in stats.open_work_orders:
            stats.open_work_orders[priority] = count

    # ========================================================================
    # 4. Critical Alerts (24h)
    # ========================================================================
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    alerts_query = select(func.count(Alert.id)).where(
        Alert.severity == 'critical',
        Alert.occurred_at >= twenty_four_hours_ago,
        Alert.status != 'resolved'
    )
    result = await db.execute(alerts_query)
    stats.critical_alerts_24h = result.scalar() or 0

    return stats


@router.get("/health")
async def dashboard_health():
    """
    Dashboard endpoint health check
    """
    return {
        "status": "healthy",
        "endpoint": "dashboard",
        "timestamp": datetime.utcnow()
    }
