"""
Utility Monitoring API Endpoints
Per-unit electricity, water, and gas monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime, timedelta
from decimal import Decimal

from db.database import get_db
from db.models import UtilityMeter, UtilityReading, UtilityAnomaly, Unit
from services.utility_monitor import utility_monitor
from core.auth import AuthUser, require_admin, require_manager

router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class MeterCreate(BaseModel):
    unit_id: str
    meter_type: str  # electricity, water, gas
    meter_identifier: str
    device_entity_id: Optional[str] = None
    installation_date: str
    mqtt_topic: Optional[str] = None
    calibration_factor: Optional[Decimal] = Decimal("1.0")
    notes: Optional[str] = None


class ReadingIngest(BaseModel):
    meter_id: str
    reading_value: Decimal
    reading_timestamp: Optional[datetime] = None
    reading_type: str = "automatic"


class UsageQuery(BaseModel):
    start_date: datetime
    end_date: datetime


# ============================================================================
# METER MANAGEMENT
# ============================================================================

@router.post("/meters")
async def create_meter(
    meter_data: MeterCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Register a new utility meter
    """
    # Verify unit exists
    unit_query = select(Unit).where(Unit.id == meter_data.unit_id)
    unit_result = await db.execute(unit_query)
    unit = unit_result.scalar_one_or_none()

    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Check for existing meter of same type
    existing_query = select(UtilityMeter).where(
        and_(
            UtilityMeter.unit_id == meter_data.unit_id,
            UtilityMeter.meter_type == meter_data.meter_type
        )
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"{meter_data.meter_type} meter already exists for this unit"
        )

    meter = UtilityMeter(**meter_data.model_dump())
    db.add(meter)
    await db.flush()
    await db.commit()

    return {
        "id": str(meter.id),
        "unit_id": str(meter.unit_id),
        "meter_type": meter.meter_type,
        "meter_identifier": meter.meter_identifier,
        "installation_date": meter.installation_date,
        "is_active": meter.is_active
    }


@router.get("/list")
async def list_meters(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    unit_id: Optional[str] = None,
    property_id: Optional[str] = None,
    meter_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all utility meters with optional filtering
    """
    # Build query with filters
    query = select(UtilityMeter)
    conditions = []

    if unit_id:
        conditions.append(UtilityMeter.unit_id == unit_id)
    if meter_type:
        conditions.append(UtilityMeter.meter_type == meter_type)
    if is_active is not None:
        conditions.append(UtilityMeter.is_active == is_active)

    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count()).select_from(UtilityMeter)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(desc(UtilityMeter.created_at))
    result = await db.execute(query)
    meters = result.scalars().all()

    return {
        "total": total,
        "meters": [
            {
                "id": str(meter.id),
                "unit_id": str(meter.unit_id),
                "meter_type": meter.meter_type,
                "meter_identifier": meter.meter_identifier,
                "installation_date": str(meter.installation_date),
                "is_active": meter.is_active,
                "device_entity_id": meter.device_entity_id,
                "mqtt_topic": meter.mqtt_topic,
                "calibration_factor": float(meter.calibration_factor) if meter.calibration_factor else 1.0,
                "last_reading_at": meter.last_reading_at.isoformat() if meter.last_reading_at else None,
                "created_at": meter.created_at.isoformat() if meter.created_at else None
            }
            for meter in meters
        ]
    }


@router.get("/meters/unit/{unit_id}")
async def get_unit_meters(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get all meters for a unit
    """
    query = select(UtilityMeter).where(UtilityMeter.unit_id == unit_id)
    result = await db.execute(query)
    meters = result.scalars().all()

    return {
        "unit_id": str(unit_id),
        "meters": [
            {
                "id": str(meter.id),
                "meter_type": meter.meter_type,
                "meter_identifier": meter.meter_identifier,
                "installation_date": meter.installation_date,
                "last_reading_date": meter.last_reading_date,
                "is_active": meter.is_active,
                "mqtt_topic": meter.mqtt_topic
            }
            for meter in meters
        ]
    }


# ============================================================================
# READING INGESTION
# ============================================================================

@router.post("/readings/ingest")
async def ingest_reading(
    reading: ReadingIngest,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Ingest a utility reading (called by MQTT handler or manual entry)
    """
    try:
        timestamp = reading.reading_timestamp or datetime.now()

        result = await utility_monitor.ingest_reading(
            meter_id=reading.meter_id,
            reading_value=reading.reading_value,
            reading_timestamp=timestamp,
            db=db,
            reading_type=reading.reading_type
        )

        return {
            "id": str(result.id),
            "meter_id": str(result.meter_id),
            "reading_value": float(result.reading_value),
            "reading_timestamp": result.reading_timestamp,
            "ingested": True
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ingesting reading: {str(e)}")


@router.post("/readings/bulk-ingest")
async def bulk_ingest_readings(
    readings: List[ReadingIngest],
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Bulk ingest multiple readings at once
    """
    results = []
    errors = []

    for reading in readings:
        try:
            timestamp = reading.reading_timestamp or datetime.now()
            result = await utility_monitor.ingest_reading(
                meter_id=reading.meter_id,
                reading_value=reading.reading_value,
                reading_timestamp=timestamp,
                db=db,
                reading_type=reading.reading_type
            )
            results.append(str(result.id))
        except Exception as e:
            errors.append({
                "meter_id": reading.meter_id,
                "error": str(e)
            })

    return {
        "ingested": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors if errors else None
    }


# ============================================================================
# USAGE QUERIES
# ============================================================================

@router.get("/usage/unit/{unit_id}")
async def get_unit_usage(
    unit_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get utility usage summary for a unit
    """
    # Default to current billing period (last 30 days)
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    try:
        summary = await utility_monitor.get_unit_usage_summary(
            unit_id=str(unit_id),
            start_date=start_date,
            end_date=end_date,
            db=db
        )

        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating usage: {str(e)}")


@router.get("/usage/meter/{meter_id}/history")
async def get_meter_history(
    meter_id: UUID,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    Get reading history for a meter
    """
    start_date = datetime.now() - timedelta(days=days)

    query = select(UtilityReading).where(
        and_(
            UtilityReading.meter_id == meter_id,
            UtilityReading.reading_timestamp >= start_date
        )
    ).order_by(UtilityReading.reading_timestamp)

    result = await db.execute(query)
    readings = result.scalars().all()

    return {
        "meter_id": str(meter_id),
        "period_days": days,
        "readings_count": len(readings),
        "readings": [
            {
                "timestamp": r.reading_timestamp,
                "value": float(r.reading_value),
                "type": r.reading_type,
                "cost": float(r.total_cost) if r.total_cost else None
            }
            for r in readings
        ]
    }


@router.get("/usage/building/{building_id}/summary")
async def get_building_usage_summary(
    building_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get aggregated usage for entire building
    """
    # Get all units in building
    from db.models import Building

    units_query = select(Unit).where(Unit.building_id == building_id)
    units_result = await db.execute(units_query)
    units = units_result.scalars().all()

    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    building_summary = {
        "building_id": str(building_id),
        "period_start": start_date,
        "period_end": end_date,
        "units_count": len(units),
        "total_electricity_cost": 0,
        "total_water_cost": 0,
        "total_gas_cost": 0,
        "total_cost": 0,
        "units": []
    }

    for unit in units:
        try:
            unit_summary = await utility_monitor.get_unit_usage_summary(
                unit_id=str(unit.id),
                start_date=start_date,
                end_date=end_date,
                db=db
            )

            building_summary["units"].append({
                "unit_number": unit.unit_number,
                "total_cost": unit_summary["total_cost"],
                "utilities": unit_summary["utilities"]
            })

            # Aggregate costs
            for utility_type, data in unit_summary["utilities"].items():
                if utility_type == "electricity":
                    building_summary["total_electricity_cost"] += data["total_cost"]
                elif utility_type == "water":
                    building_summary["total_water_cost"] += data["total_cost"]
                elif utility_type == "gas":
                    building_summary["total_gas_cost"] += data["total_cost"]

            building_summary["total_cost"] += unit_summary["total_cost"]

        except Exception as e:
            print(f"Error calculating usage for unit {unit.id}: {e}")

    return building_summary


# ============================================================================
# ANOMALY DETECTION
# ============================================================================

@router.get("/anomalies/unit/{unit_id}")
async def get_unit_anomalies(
    unit_id: UUID,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get anomalies for a specific unit
    """
    query = select(UtilityAnomaly).where(UtilityAnomaly.unit_id == unit_id)

    if status:
        query = query.where(UtilityAnomaly.status == status)

    if severity:
        query = query.where(UtilityAnomaly.severity == severity)

    query = query.order_by(desc(UtilityAnomaly.detected_at)).limit(limit)

    result = await db.execute(query)
    anomalies = result.scalars().all()

    return {
        "unit_id": str(unit_id),
        "total": len(anomalies),
        "anomalies": [
            {
                "id": str(a.id),
                "anomaly_type": a.anomaly_type,
                "severity": a.severity,
                "detected_at": a.detected_at,
                "description": a.description,
                "expected_value": float(a.expected_value) if a.expected_value else None,
                "actual_value": float(a.actual_value) if a.actual_value else None,
                "deviation_percent": float(a.deviation_percent) if a.deviation_percent else None,
                "status": a.status,
                "work_order_id": str(a.work_order_id) if a.work_order_id else None
            }
            for a in anomalies
        ]
    }


@router.get("/anomalies/active")
async def get_active_anomalies(
    severity: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active anomalies across all units
    """
    query = select(UtilityAnomaly).where(
        UtilityAnomaly.status.in_(["open", "investigating"])
    )

    if severity:
        query = query.where(UtilityAnomaly.severity == severity)

    query = query.order_by(
        UtilityAnomaly.severity.desc(),
        UtilityAnomaly.detected_at.desc()
    ).limit(limit)

    result = await db.execute(query)
    anomalies = result.scalars().all()

    return {
        "total": len(anomalies),
        "anomalies": [
            {
                "id": str(a.id),
                "unit_id": str(a.unit_id),
                "anomaly_type": a.anomaly_type,
                "severity": a.severity,
                "detected_at": a.detected_at,
                "description": a.description,
                "status": a.status
            }
            for a in anomalies
        ]
    }


@router.patch("/anomalies/{anomaly_id}/resolve")
async def resolve_anomaly(
    anomaly_id: UUID,
    resolution_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Mark an anomaly as resolved
    """
    query = select(UtilityAnomaly).where(UtilityAnomaly.id == anomaly_id)
    result = await db.execute(query)
    anomaly = result.scalar_one_or_none()

    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    anomaly.status = "resolved"
    anomaly.resolved_at = datetime.now()
    anomaly.resolution_notes = resolution_notes

    await db.commit()

    return {
        "anomaly_id": str(anomaly_id),
        "status": "resolved",
        "resolved_at": anomaly.resolved_at
    }


# ============================================================================
# REAL-TIME MONITORING
# ============================================================================

@router.get("/live/unit/{unit_id}")
async def get_live_usage(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get current/latest usage for a unit (for live dashboard)
    """
    # Get all meters for unit
    meters_query = select(UtilityMeter).where(
        and_(
            UtilityMeter.unit_id == unit_id,
            UtilityMeter.is_active == True
        )
    )

    meters_result = await db.execute(meters_query)
    meters = meters_result.scalars().all()

    live_data = {
        "unit_id": str(unit_id),
        "timestamp": datetime.now(),
        "utilities": {}
    }

    for meter in meters:
        # Get latest reading
        latest_query = select(UtilityReading).where(
            UtilityReading.meter_id == meter.id
        ).order_by(desc(UtilityReading.reading_timestamp)).limit(1)

        latest_result = await db.execute(latest_query)
        latest_reading = latest_result.scalar_one_or_none()

        if latest_reading:
            live_data["utilities"][meter.meter_type] = {
                "current_value": float(latest_reading.reading_value),
                "last_updated": latest_reading.reading_timestamp,
                "meter_id": str(meter.id)
            }

    return live_data
