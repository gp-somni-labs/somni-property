"""
Intelligent Summary Layer API - Unified Dashboard for Property Management

Aggregates data from all integrated services:
- SomniProperty (work orders, tenants, properties)
- Novu (notifications)
- Vikunja (tasks)
- Cal.com (appointments)
- Homebox (assets, BOMs)
- Email/SMS communications
- Approval workflow

Provides:
- Real-time overview dashboard
- Predictive insights
- Multi-property summary
- Performance analytics
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

from db.database import get_db
from services.novu_client import get_novu_client
from services.vikunja_client import get_vikunja_client
from services.calcom_client import get_calcom_client, BookingStatus
from services.homebox_client import get_homebox_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/summary", tags=["Intelligent Summary"])


# ========================================
# Response Models
# ========================================

class WorkOrderStats(BaseModel):
    """Work order statistics breakdown"""
    total: int = 0
    emergency: int = 0
    high_priority: int = 0
    in_progress: int = 0

class HubStats(BaseModel):
    """Hub statistics"""
    total: int = 0
    online: int = 0
    offline: int = 0
    warning: int = 0

class DashboardOverview(BaseModel):
    """High-level dashboard summary"""
    # Work Orders
    pending_approvals: int
    open_work_orders: WorkOrderStats
    work_orders_this_week: int

    # Hubs (for SomniFamily mode)
    residential_hubs: HubStats
    property_hubs: HubStats

    # Tasks
    pending_tasks: int
    overdue_tasks: int
    completed_tasks_this_week: int

    # Appointments
    upcoming_appointments: int
    appointments_today: int

    # Communications
    unread_emails: int
    unread_sms: int
    pending_notifications: int

    # Assets
    assets_needing_maintenance: int
    warranties_expiring_soon: int

    # Financials
    estimated_pending_costs: float
    bom_total_this_month: float

    # Timestamps
    last_updated: datetime


class PredictiveInsights(BaseModel):
    """AI-driven predictive insights"""
    maintenance_predictions: List[Dict[str, Any]]
    cost_trend: str  # "increasing", "stable", "decreasing"
    busy_hours: List[int]  # Hours of day with most activity
    average_resolution_time: float  # In hours
    tenant_satisfaction_score: Optional[float] = None


class PropertySummary(BaseModel):
    """Summary for a single property"""
    property_id: str
    property_name: str
    total_units: int
    occupied_units: int
    occupancy_rate: float

    # Work orders
    open_work_orders: int
    urgent_work_orders: int

    # Financial
    monthly_rent_collected: float
    pending_payments: float

    # Maintenance
    upcoming_maintenance: int
    assets_count: int


class MultiPropertySummary(BaseModel):
    """Portfolio-level summary"""
    total_properties: int
    total_units: int
    overall_occupancy_rate: float
    total_open_work_orders: int
    total_pending_approvals: int
    properties: List[PropertySummary]


# ========================================
# Endpoints
# ========================================

@router.get("/dashboard", response_model=DashboardOverview)
async def get_dashboard_overview(
    property_id: Optional[str] = Query(None, description="Filter by property"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time dashboard overview

    Aggregates data from:
    - Approval workflow (pending actions)
    - Work orders (open, completed)
    - Vikunja (tasks)
    - Cal.com (appointments)
    - Email/SMS (unread messages)
    - Homebox (assets needing maintenance)
    """
    try:
        from db.models_approval import PendingAction
        from db.models import WorkOrder
        from db.models_comms import EmailMessage, SMSMessage

        # Pending Approvals
        approvals_query = select(func.count(PendingAction.id)).where(
            PendingAction.status == 'pending'
        )
        if property_id:
            approvals_query = approvals_query.where(PendingAction.property_id == property_id)

        result = await db.execute(approvals_query)
        pending_approvals = result.scalar() or 0

        # Open Work Orders (detailed stats)
        from sqlalchemy import case
        work_orders_stats_query = select(
            func.count(WorkOrder.id).label('total'),
            func.sum(case((WorkOrder.priority == 'emergency', 1), else_=0)).label('emergency'),
            func.sum(case((WorkOrder.priority == 'high', 1), else_=0)).label('high_priority'),
            func.sum(case((WorkOrder.status == 'in_progress', 1), else_=0)).label('in_progress')
        ).where(WorkOrder.status.in_(['submitted', 'in_progress']))

        if property_id:
            work_orders_stats_query = work_orders_stats_query.where(WorkOrder.property_id == property_id)

        result = await db.execute(work_orders_stats_query)
        wo_stats = result.first()
        open_work_orders = WorkOrderStats(
            total=wo_stats.total or 0,
            emergency=wo_stats.emergency or 0,
            high_priority=wo_stats.high_priority or 0,
            in_progress=wo_stats.in_progress or 0
        )

        # Work Orders This Week
        week_ago = datetime.now() - timedelta(days=7)
        work_orders_week_query = select(func.count(WorkOrder.id)).where(
            WorkOrder.created_at >= week_ago
        )
        if property_id:
            work_orders_week_query = work_orders_week_query.where(WorkOrder.property_id == property_id)

        result = await db.execute(work_orders_week_query)
        work_orders_this_week = result.scalar() or 0

        # Unread Communications
        unread_emails_query = select(func.count(EmailMessage.id)).where(
            and_(
                EmailMessage.direction == 'incoming',
                EmailMessage.ai_processed == False
            )
        )
        result = await db.execute(unread_emails_query)
        unread_emails = result.scalar() or 0

        unread_sms_query = select(func.count(SMSMessage.id)).where(
            and_(
                SMSMessage.direction == 'incoming',
                SMSMessage.ai_processed == False
            )
        )
        result = await db.execute(unread_sms_query)
        unread_sms = result.scalar() or 0

        # Estimated Pending Costs
        cost_query = select(func.sum(PendingAction.estimated_cost)).where(
            PendingAction.status == 'pending'
        )
        if property_id:
            cost_query = cost_query.where(PendingAction.property_id == property_id)

        result = await db.execute(cost_query)
        estimated_pending_costs = result.scalar() or 0.0

        # Vikunja Tasks (if configured)
        pending_tasks = 0
        overdue_tasks = 0
        completed_tasks_this_week = 0

        try:
            vikunja_client = get_vikunja_client()
            # TODO: Get project_id from configuration
            project_id = 1
            tasks = await vikunja_client.list_tasks(project_id, filter_done=False)
            pending_tasks = len(tasks)

            # Count overdue tasks
            now = datetime.now()
            overdue_tasks = sum(
                1 for task in tasks
                if task.due_date and task.due_date < now and not task.done
            )

            # Count completed tasks this week
            completed = await vikunja_client.list_tasks(project_id, filter_done=True)
            completed_tasks_this_week = sum(
                1 for task in completed
                if task.end_date and task.end_date >= week_ago
            )

        except Exception as e:
            logger.error(f"Failed to fetch Vikunja tasks: {e}")

        # Cal.com Appointments (if configured)
        upcoming_appointments = 0
        appointments_today = 0

        try:
            calcom_client = get_calcom_client()

            # Get upcoming appointments (next 30 days)
            now = datetime.now()
            future = now + timedelta(days=30)
            bookings = await calcom_client.list_bookings(
                status=BookingStatus.ACCEPTED,
                from_date=now,
                to_date=future
            )
            upcoming_appointments = len(bookings)

            # Appointments today
            today_end = now.replace(hour=23, minute=59, second=59)
            appointments_today = sum(
                1 for booking in bookings
                if booking.start_time.date() == now.date()
            )

        except Exception as e:
            logger.error(f"Failed to fetch Cal.com appointments: {e}")

        # Homebox Assets (if configured)
        assets_needing_maintenance = 0
        warranties_expiring_soon = 0

        try:
            homebox_client = get_homebox_client()

            # Get warranties expiring in next 60 days
            expiring = await homebox_client.get_warranty_expiring_soon(days=60)
            warranties_expiring_soon = len(expiring)

            # TODO: Determine assets needing maintenance based on service schedule

        except Exception as e:
            logger.error(f"Failed to fetch Homebox data: {e}")

        # Hub Statistics (for SomniFamily mode)
        from db.models import PropertyEdgeNode

        # Residential Hubs Stats
        residential_hubs_query = select(
            func.count(PropertyEdgeNode.id).label('total'),
            func.sum(case((PropertyEdgeNode.status == 'online', 1), else_=0)).label('online'),
            func.sum(case((PropertyEdgeNode.status == 'offline', 1), else_=0)).label('offline'),
            func.sum(case((PropertyEdgeNode.status.in_(['warning', 'error']), 1), else_=0)).label('warning')
        ).where(PropertyEdgeNode.hub_type == 'RESIDENTIAL')

        if property_id:
            residential_hubs_query = residential_hubs_query.where(PropertyEdgeNode.property_id == property_id)

        result = await db.execute(residential_hubs_query)
        res_stats = result.first()
        residential_hubs = HubStats(
            total=res_stats.total or 0,
            online=res_stats.online or 0,
            offline=res_stats.offline or 0,
            warning=res_stats.warning or 0
        )

        # Property Hubs Stats
        property_hubs_query = select(
            func.count(PropertyEdgeNode.id).label('total'),
            func.sum(case((PropertyEdgeNode.status == 'online', 1), else_=0)).label('online'),
            func.sum(case((PropertyEdgeNode.status == 'offline', 1), else_=0)).label('offline'),
            func.sum(case((PropertyEdgeNode.status.in_(['warning', 'error']), 1), else_=0)).label('warning')
        ).where(PropertyEdgeNode.hub_type == 'PROPERTY_HUB')

        if property_id:
            property_hubs_query = property_hubs_query.where(PropertyEdgeNode.property_id == property_id)

        result = await db.execute(property_hubs_query)
        prop_stats = result.first()
        property_hubs = HubStats(
            total=prop_stats.total or 0,
            online=prop_stats.online or 0,
            offline=prop_stats.offline or 0,
            warning=prop_stats.warning or 0
        )

        return DashboardOverview(
            pending_approvals=pending_approvals,
            open_work_orders=open_work_orders,
            work_orders_this_week=work_orders_this_week,
            residential_hubs=residential_hubs,
            property_hubs=property_hubs,
            pending_tasks=pending_tasks,
            overdue_tasks=overdue_tasks,
            completed_tasks_this_week=completed_tasks_this_week,
            upcoming_appointments=upcoming_appointments,
            appointments_today=appointments_today,
            unread_emails=unread_emails,
            unread_sms=unread_sms,
            pending_notifications=0,  # TODO: Get from Novu
            assets_needing_maintenance=assets_needing_maintenance,
            warranties_expiring_soon=warranties_expiring_soon,
            estimated_pending_costs=float(estimated_pending_costs),
            bom_total_this_month=0.0,  # TODO: Calculate from Homebox BOMs
            last_updated=datetime.now()
        )

    except Exception as e:
        logger.error(f"Failed to generate dashboard overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard: {str(e)}")


@router.get("/insights", response_model=PredictiveInsights)
async def get_predictive_insights(
    property_id: Optional[str] = Query(None, description="Filter by property"),
    days: int = Query(30, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-driven predictive insights

    Analyzes historical data to provide:
    - Maintenance predictions (appliances likely to fail soon)
    - Cost trends
    - Busy hours (when most requests come in)
    - Average resolution time
    - Tenant satisfaction score
    """
    try:
        from db.models import WorkOrder
        from db.models_comms import EmailMessage, SMSMessage

        cutoff_date = datetime.now() - timedelta(days=days)

        # Analyze work orders for patterns
        work_orders_query = select(WorkOrder).where(
            WorkOrder.created_at >= cutoff_date
        )
        if property_id:
            work_orders_query = work_orders_query.where(WorkOrder.property_id == property_id)

        result = await db.execute(work_orders_query)
        work_orders = result.scalars().all()

        # Cost trend analysis
        if len(work_orders) >= 2:
            # Split into two halves
            mid = len(work_orders) // 2
            first_half_avg = sum(wo.estimated_cost or 0 for wo in work_orders[:mid]) / mid if mid > 0 else 0
            second_half_avg = sum(wo.estimated_cost or 0 for wo in work_orders[mid:]) / (len(work_orders) - mid) if (len(work_orders) - mid) > 0 else 0

            if second_half_avg > first_half_avg * 1.1:
                cost_trend = "increasing"
            elif second_half_avg < first_half_avg * 0.9:
                cost_trend = "decreasing"
            else:
                cost_trend = "stable"
        else:
            cost_trend = "insufficient_data"

        # Busy hours analysis (when most emails/SMS come in)
        emails_query = select(EmailMessage).where(
            and_(
                EmailMessage.direction == 'incoming',
                EmailMessage.received_at >= cutoff_date
            )
        )
        result = await db.execute(emails_query)
        emails = result.scalars().all()

        sms_query = select(SMSMessage).where(
            and_(
                SMSMessage.direction == 'incoming',
                SMSMessage.received_at >= cutoff_date
            )
        )
        result = await db.execute(sms_query)
        sms_messages = result.scalars().all()

        # Count messages by hour
        hourly_counts = {}
        for email in emails:
            hour = email.received_at.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

        for sms in sms_messages:
            hour = sms.received_at.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

        # Get top 3 busy hours
        busy_hours = sorted(hourly_counts.keys(), key=lambda h: hourly_counts[h], reverse=True)[:3]

        # Average resolution time
        completed_work_orders = [wo for wo in work_orders if wo.completed_at]
        if completed_work_orders:
            total_resolution_time = sum(
                (wo.completed_at - wo.created_at).total_seconds() / 3600
                for wo in completed_work_orders
            )
            average_resolution_time = total_resolution_time / len(completed_work_orders)
        else:
            average_resolution_time = 0.0

        # Maintenance predictions (using Homebox data)
        maintenance_predictions = []

        try:
            homebox_client = get_homebox_client()

            # Get all assets
            assets = await homebox_client.search_assets()

            for asset in assets:
                # Get maintenance history
                history = await homebox_client.get_maintenance_history(asset.id)

                if history:
                    # Calculate average time between maintenance
                    sorted_history = sorted(history, key=lambda h: h.date)
                    if len(sorted_history) >= 2:
                        intervals = []
                        for i in range(1, len(sorted_history)):
                            interval_days = (sorted_history[i].date - sorted_history[i-1].date).days
                            intervals.append(interval_days)

                        avg_interval = sum(intervals) / len(intervals)
                        last_maintenance = sorted_history[-1].date
                        days_since_last = (datetime.now() - last_maintenance).days

                        # Predict if maintenance is due soon
                        if days_since_last >= avg_interval * 0.8:
                            maintenance_predictions.append({
                                'asset_id': asset.id,
                                'asset_name': asset.name,
                                'last_maintenance': last_maintenance.isoformat(),
                                'days_since_last': days_since_last,
                                'predicted_due_in_days': int(avg_interval - days_since_last),
                                'confidence': 'high' if days_since_last >= avg_interval * 0.9 else 'medium'
                            })

        except Exception as e:
            logger.error(f"Failed to generate maintenance predictions: {e}")

        return PredictiveInsights(
            maintenance_predictions=maintenance_predictions,
            cost_trend=cost_trend,
            busy_hours=busy_hours,
            average_resolution_time=round(average_resolution_time, 2)
        )

    except Exception as e:
        logger.error(f"Failed to generate insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


@router.get("/multi-property", response_model=MultiPropertySummary)
async def get_multi_property_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Get portfolio-level summary across all properties

    Provides high-level overview for property managers with multiple properties
    """
    try:
        from db.models import Property, Unit, WorkOrder

        # Get all properties
        properties_query = select(Property)
        result = await db.execute(properties_query)
        properties = result.scalars().all()

        property_summaries = []
        total_units = 0
        total_open_work_orders = 0
        total_pending_approvals = 0

        for prop in properties:
            # Count units
            units_query = select(func.count(Unit.id)).where(Unit.property_id == prop.id)
            result = await db.execute(units_query)
            unit_count = result.scalar() or 0
            total_units += unit_count

            # Count occupied units
            occupied_query = select(func.count(Unit.id)).where(
                and_(
                    Unit.property_id == prop.id,
                    Unit.tenant_id.isnot(None)
                )
            )
            result = await db.execute(occupied_query)
            occupied_count = result.scalar() or 0

            occupancy_rate = (occupied_count / unit_count * 100) if unit_count > 0 else 0

            # Count open work orders
            wo_query = select(func.count(WorkOrder.id)).where(
                and_(
                    WorkOrder.property_id == prop.id,
                    WorkOrder.status.in_(['submitted', 'in_progress'])
                )
            )
            result = await db.execute(wo_query)
            open_wo = result.scalar() or 0
            total_open_work_orders += open_wo

            # Count urgent work orders
            urgent_query = select(func.count(WorkOrder.id)).where(
                and_(
                    WorkOrder.property_id == prop.id,
                    WorkOrder.priority == 'urgent',
                    WorkOrder.status.in_(['submitted', 'in_progress'])
                )
            )
            result = await db.execute(urgent_query)
            urgent_wo = result.scalar() or 0

            property_summaries.append(PropertySummary(
                property_id=str(prop.id),
                property_name=prop.name,
                total_units=unit_count,
                occupied_units=occupied_count,
                occupancy_rate=round(occupancy_rate, 2),
                open_work_orders=open_wo,
                urgent_work_orders=urgent_wo,
                monthly_rent_collected=0.0,  # TODO: Calculate from payments
                pending_payments=0.0,  # TODO: Calculate from lease agreements
                upcoming_maintenance=0,  # TODO: Calculate from scheduled maintenance
                assets_count=0  # TODO: Count Homebox assets for this property
            ))

        # Count total pending approvals
        from db.models_approval import PendingAction
        approvals_query = select(func.count(PendingAction.id)).where(
            PendingAction.status == 'pending'
        )
        result = await db.execute(approvals_query)
        total_pending_approvals = result.scalar() or 0

        # Calculate overall occupancy rate
        overall_occupancy = (
            sum(ps.occupied_units for ps in property_summaries) / total_units * 100
        ) if total_units > 0 else 0

        return MultiPropertySummary(
            total_properties=len(properties),
            total_units=total_units,
            overall_occupancy_rate=round(overall_occupancy, 2),
            total_open_work_orders=total_open_work_orders,
            total_pending_approvals=total_pending_approvals,
            properties=property_summaries
        )

    except Exception as e:
        logger.error(f"Failed to generate multi-property summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@router.get("/health")
async def health_check():
    """Check health of all integrated services"""
    health_status = {
        "somniproperty": "healthy",
        "novu": "unknown",
        "vikunja": "unknown",
        "calcom": "unknown",
        "homebox": "unknown"
    }

    # Check Novu
    try:
        novu_client = get_novu_client()
        workflows = await novu_client.list_workflows()
        health_status["novu"] = "healthy" if workflows is not None else "unhealthy"
    except Exception as e:
        health_status["novu"] = f"unhealthy: {str(e)}"

    # Check Vikunja
    try:
        vikunja_client = get_vikunja_client()
        if await vikunja_client.login():
            health_status["vikunja"] = "healthy"
        else:
            health_status["vikunja"] = "unhealthy: login failed"
    except Exception as e:
        health_status["vikunja"] = f"unhealthy: {str(e)}"

    # Check Cal.com
    try:
        calcom_client = get_calcom_client()
        event_types = await calcom_client.list_event_types()
        health_status["calcom"] = "healthy" if event_types is not None else "unhealthy"
    except Exception as e:
        health_status["calcom"] = f"unhealthy: {str(e)}"

    # Check Homebox
    try:
        homebox_client = get_homebox_client()
        locations = await homebox_client.list_locations()
        health_status["homebox"] = "healthy" if locations is not None else "unhealthy"
    except Exception as e:
        health_status["homebox"] = f"unhealthy: {str(e)}"

    return health_status
