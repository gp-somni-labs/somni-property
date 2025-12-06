"""
Alerts and Incidents API
Aggregates alerts from Home Assistant and MQTT events
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
import logging

from db.database import get_db
from db.models import Alert, PropertyEdgeNode
from api.schemas import (
    AlertCreate,
    AlertUpdate,
    Alert as AlertSchema,
    AlertListResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# ALERT ENDPOINTS
# ============================================================================

@router.get("", response_model=AlertListResponse)
async def list_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    severity: Optional[str] = Query(None, pattern="^(info|warning|critical)$"),
    status: Optional[str] = Query(None, pattern="^(open|acknowledged|resolved)$"),
    hub_id: Optional[UUID] = None,
    category: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List alerts with optional filtering

    Filters:
    - **severity**: info, warning, critical
    - **status**: open, acknowledged, resolved
    - **hub_id**: Filter by specific hub
    - **category**: leak, fire, security, hvac, etc.
    - **source**: home_assistant, mqtt, system
    - **start_date**: Filter alerts after this date
    - **end_date**: Filter alerts before this date
    """
    query = select(Alert)

    # Apply filters
    if severity:
        query = query.where(Alert.severity == severity)

    if status:
        query = query.where(Alert.status == status)

    if hub_id:
        query = query.where(Alert.hub_id == hub_id)

    if category:
        query = query.where(Alert.category == category)

    if source:
        query = query.where(Alert.source == source)

    if start_date:
        query = query.where(Alert.occurred_at >= start_date)

    if end_date:
        query = query.where(Alert.occurred_at <= end_date)

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Get paginated results (ordered by most recent first)
    query = query.offset(skip).limit(limit).order_by(desc(Alert.occurred_at))
    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        items=[AlertSchema.model_validate(alert) for alert in alerts],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/critical-24h", response_model=int)
async def get_critical_alerts_count(
    db: AsyncSession = Depends(get_db)
):
    """
    Get count of critical unresolved alerts in the last 24 hours
    Used by dashboard for quick stats
    """
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    query = select(func.count(Alert.id)).where(
        Alert.severity == 'critical',
        Alert.occurred_at >= twenty_four_hours_ago,
        Alert.status != 'resolved'
    )
    result = await db.execute(query)
    return result.scalar() or 0


@router.get("/{alert_id}", response_model=AlertSchema)
async def get_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific alert by ID"""
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )

    return AlertSchema.model_validate(alert)


@router.post("", response_model=AlertSchema, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new alert (typically called from HA/MQTT ingestion services)

    Required fields:
    - **severity**: info, warning, or critical
    - **source**: home_assistant, mqtt, or system
    - **category**: leak, fire, security, hvac, etc.
    - **message**: Alert message text
    """
    # Validate hub exists if provided
    if alert_data.hub_id:
        hub_result = await db.execute(
            select(PropertyEdgeNode).where(PropertyEdgeNode.id == alert_data.hub_id)
        )
        hub = hub_result.scalar_one_or_none()
        if not hub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Hub {alert_data.hub_id} not found"
            )

    # Create alert
    alert = Alert(**alert_data.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    logger.info(f"Created alert {alert.id}: {alert.severity} - {alert.message}")

    return AlertSchema.model_validate(alert)


@router.patch("/{alert_id}/acknowledge", response_model=AlertSchema)
async def acknowledge_alert(
    alert_id: UUID,
    acknowledged_by: str = Query(..., description="Username or ID of person acknowledging"),
    db: AsyncSession = Depends(get_db)
):
    """
    Acknowledge an alert

    Sets status to 'acknowledged' and records who acknowledged it and when
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )

    # Update alert
    alert.status = 'acknowledged'
    alert.acknowledged_by = acknowledged_by
    alert.acknowledged_at = datetime.utcnow()

    await db.commit()
    await db.refresh(alert)

    logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")

    return AlertSchema.model_validate(alert)


@router.patch("/{alert_id}/resolve", response_model=AlertSchema)
async def resolve_alert(
    alert_id: UUID,
    resolved_by: str = Query(..., description="Username or ID of person resolving"),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolve an alert

    Sets status to 'resolved'
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )

    # Update alert
    alert.status = 'resolved'
    if not alert.acknowledged_by:
        alert.acknowledged_by = resolved_by
        alert.acknowledged_at = datetime.utcnow()

    await db.commit()
    await db.refresh(alert)

    logger.info(f"Alert {alert_id} resolved by {resolved_by}")

    return AlertSchema.model_validate(alert)


@router.patch("/bulk/acknowledge", response_model=List[AlertSchema])
async def bulk_acknowledge_alerts(
    alert_ids: List[UUID],
    acknowledged_by: str = Query(..., description="Username or ID of person acknowledging"),
    db: AsyncSession = Depends(get_db)
):
    """
    Acknowledge multiple alerts at once

    Useful for bulk operations in the UI
    """
    if len(alert_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot acknowledge more than 100 alerts at once"
        )

    result = await db.execute(
        select(Alert).where(Alert.id.in_(alert_ids))
    )
    alerts = result.scalars().all()

    if not alerts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No alerts found with provided IDs"
        )

    # Update all alerts
    now = datetime.utcnow()
    for alert in alerts:
        alert.status = 'acknowledged'
        alert.acknowledged_by = acknowledged_by
        alert.acknowledged_at = now

    await db.commit()

    # Refresh all alerts
    for alert in alerts:
        await db.refresh(alert)

    logger.info(f"Bulk acknowledged {len(alerts)} alerts by {acknowledged_by}")

    return [AlertSchema.model_validate(alert) for alert in alerts]


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an alert

    This is typically only used for cleanup or test data.
    In production, alerts should be resolved rather than deleted.
    """
    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found"
        )

    await db.delete(alert)
    await db.commit()

    logger.info(f"Deleted alert {alert_id}")

    return None
