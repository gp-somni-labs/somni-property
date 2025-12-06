"""
Somni Property Manager - Smart Devices API
CRUD endpoints for smart device inventory management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import datetime

from db.database import get_db
from db.models import SmartDevice as SmartDeviceModel
from api.schemas import (
    SmartDevice,
    SmartDeviceCreate,
    SmartDeviceUpdate,
    SmartDeviceListResponse
)
from core.auth import AuthUser, require_admin, require_manager

router = APIRouter()


@router.post("", response_model=SmartDevice, status_code=201)
async def create_smart_device(
    device_data: SmartDeviceCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Create a new smart device in inventory (Admin only)

    Smart devices track:
    - Installation location and owner
    - Integration with MQTT and Home Assistant
    - Health status and warranty
    - Firmware version and lifecycle
    """
    device_obj = SmartDeviceModel(**device_data.model_dump())
    db.add(device_obj)
    await db.flush()
    await db.refresh(device_obj)
    return device_obj


@router.get("", response_model=SmartDeviceListResponse)
async def list_smart_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    property_id: Optional[UUID] = Query(None, description="Filter by property ID"),
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    contract_id: Optional[UUID] = Query(None, description="Filter by service contract ID"),
    edge_node_id: Optional[UUID] = Query(None, description="Filter by edge node ID"),
    device_type: Optional[str] = Query(None, description="Filter by device type"),
    status: Optional[str] = Query(None, description="Filter by status (active/inactive/maintenance/failed/retired)"),
    health_status: Optional[str] = Query(None, description="Filter by health (healthy/warning/critical/unknown)"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all smart devices with pagination and filtering (Admin/Manager only)

    Query parameters:
    - property_id: Filter devices at specific property
    - client_id: Filter devices owned by specific client
    - contract_id: Filter devices under specific contract
    - edge_node_id: Filter devices managed by specific edge node
    - device_type: Filter by type (sensor, switch, camera, etc.)
    - status: Filter by operational status
    - health_status: Filter by health status
    - skip: Pagination offset
    - limit: Maximum number of items to return
    """
    # Build query with optional filters
    query_base = select(SmartDeviceModel)

    if property_id:
        query_base = query_base.where(SmartDeviceModel.property_id == property_id)
    if client_id:
        query_base = query_base.where(SmartDeviceModel.client_id == client_id)
    if contract_id:
        query_base = query_base.where(SmartDeviceModel.service_contract_id == contract_id)
    if edge_node_id:
        query_base = query_base.where(SmartDeviceModel.edge_node_id == edge_node_id)
    if device_type:
        query_base = query_base.where(SmartDeviceModel.device_type == device_type)
    if status:
        query_base = query_base.where(SmartDeviceModel.status == status)
    if health_status:
        query_base = query_base.where(SmartDeviceModel.health_status == health_status)

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get devices
    query = query_base.offset(skip).limit(limit).order_by(SmartDeviceModel.created_at.desc())
    result = await db.execute(query)
    devices = result.scalars().all()

    return SmartDeviceListResponse(
        items=devices,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/failing", response_model=SmartDeviceListResponse)
async def list_failing_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List devices with health issues (Admin/Manager only)

    Returns devices with status='failed' or health_status='critical'.
    Useful for maintenance dashboards.
    """
    query_base = select(SmartDeviceModel).where(
        (SmartDeviceModel.status == "failed") |
        (SmartDeviceModel.health_status == "critical")
    )

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get devices
    query = query_base.offset(skip).limit(limit).order_by(SmartDeviceModel.last_seen.asc())
    result = await db.execute(query)
    devices = result.scalars().all()

    return SmartDeviceListResponse(
        items=devices,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{device_id}", response_model=SmartDevice)
async def get_smart_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a specific smart device by ID (Admin/Manager only)"""
    query = select(SmartDeviceModel).where(SmartDeviceModel.id == device_id)
    result = await db.execute(query)
    device_obj = result.scalar_one_or_none()

    if not device_obj:
        raise HTTPException(status_code=404, detail="Smart device not found")

    return device_obj


@router.put("/{device_id}", response_model=SmartDevice)
async def update_smart_device(
    device_id: UUID,
    device_data: SmartDeviceUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Update a smart device (Admin only)

    Use this to:
    - Update device status
    - Record firmware updates
    - Change health status
    - Update MQTT/HA integration details
    """
    query = select(SmartDeviceModel).where(SmartDeviceModel.id == device_id)
    result = await db.execute(query)
    device_obj = result.scalar_one_or_none()

    if not device_obj:
        raise HTTPException(status_code=404, detail="Smart device not found")

    # Update only provided fields
    update_data = device_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(device_obj, key, value)

    await db.flush()
    await db.refresh(device_obj)
    return device_obj


@router.post("/{device_id}/heartbeat", response_model=SmartDevice)
async def update_device_heartbeat(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Update device heartbeat timestamp (Admin/Manager only)

    Called by MQTT integration when device sends heartbeat.
    Updates last_heartbeat and last_seen, sets health to 'healthy'.
    """
    query = select(SmartDeviceModel).where(SmartDeviceModel.id == device_id)
    result = await db.execute(query)
    device_obj = result.scalar_one_or_none()

    if not device_obj:
        raise HTTPException(status_code=404, detail="Smart device not found")

    device_obj.last_heartbeat = datetime.utcnow()
    device_obj.last_seen = datetime.utcnow()
    device_obj.health_status = "healthy"

    # If device was failed/inactive, mark as active
    if device_obj.status in ["failed", "inactive"]:
        device_obj.status = "active"

    await db.flush()
    await db.refresh(device_obj)
    return device_obj


@router.post("/{device_id}/mark-failed", response_model=SmartDevice)
async def mark_device_failed(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Mark device as failed (Admin only)

    Sets status='failed' and health_status='critical'.
    Triggers work order creation in MQTT service.
    """
    query = select(SmartDeviceModel).where(SmartDeviceModel.id == device_id)
    result = await db.execute(query)
    device_obj = result.scalar_one_or_none()

    if not device_obj:
        raise HTTPException(status_code=404, detail="Smart device not found")

    device_obj.status = "failed"
    device_obj.health_status = "critical"

    await db.flush()
    await db.refresh(device_obj)
    return device_obj


@router.post("/{device_id}/retire", response_model=SmartDevice)
async def retire_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Retire a smart device (Admin only)

    Sets status='retired'. Device remains in inventory for records.
    """
    query = select(SmartDeviceModel).where(SmartDeviceModel.id == device_id)
    result = await db.execute(query)
    device_obj = result.scalar_one_or_none()

    if not device_obj:
        raise HTTPException(status_code=404, detail="Smart device not found")

    device_obj.status = "retired"

    await db.flush()
    await db.refresh(device_obj)
    return device_obj


@router.delete("/{device_id}", status_code=204)
async def delete_smart_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Delete a smart device from inventory (Admin only)

    Permanently removes device. Consider retiring instead to preserve records.
    """
    query = select(SmartDeviceModel).where(SmartDeviceModel.id == device_id)
    result = await db.execute(query)
    device_obj = result.scalar_one_or_none()

    if not device_obj:
        raise HTTPException(status_code=404, detail="Smart device not found")

    await db.delete(device_obj)
    await db.flush()
    return None
