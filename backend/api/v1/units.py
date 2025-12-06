"""
Somni Property Manager - Units API
CRUD endpoints for unit management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID

from db.database import get_db
from db.models import Unit as UnitModel, Building as BuildingModel
from api.schemas import Unit, UnitCreate, UnitUpdate, UnitList
from core.auth import AuthUser, require_admin, require_manager

router = APIRouter()


@router.post("", response_model=Unit, status_code=201)
async def create_unit(
    unit_data: UnitCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Create a new unit (Admin only)"""
    # Verify building exists
    building_query = select(BuildingModel).where(BuildingModel.id == unit_data.building_id)
    building_result = await db.execute(building_query)
    if not building_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Building not found")

    # Check for duplicate unit number in same building
    duplicate_query = select(UnitModel).where(
        UnitModel.building_id == unit_data.building_id,
        UnitModel.unit_number == unit_data.unit_number
    )
    duplicate_result = await db.execute(duplicate_query)
    if duplicate_result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Unit {unit_data.unit_number} already exists in this building"
        )

    unit_obj = UnitModel(**unit_data.model_dump())
    db.add(unit_obj)
    await db.flush()
    await db.refresh(unit_obj)
    return unit_obj


@router.get("", response_model=UnitList)
async def list_units(
    building_id: Optional[UUID] = Query(None, description="Filter by building ID"),
    status: Optional[str] = Query(None, description="Filter by status (vacant/occupied/maintenance/unavailable)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """List all units with optional filters (Admin/Manager only)"""
    # Build query
    query = select(UnitModel)
    count_query = select(func.count()).select_from(UnitModel)

    if building_id:
        query = query.where(UnitModel.building_id == building_id)
        count_query = count_query.where(UnitModel.building_id == building_id)

    if status:
        query = query.where(UnitModel.status == status)
        count_query = count_query.where(UnitModel.status == status)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get units
    query = query.offset(skip).limit(limit).order_by(UnitModel.unit_number)
    result = await db.execute(query)
    units = result.scalars().all()

    return UnitList(total=total, items=units)


@router.get("/available", response_model=UnitList)
async def list_available_units(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """List all available (vacant) units ready for rent (Admin/Manager only)"""
    # Query from database VIEW (defined in schema)
    from sqlalchemy import text

    count_query = text("SELECT COUNT(*) FROM available_units_view")
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get units
    query = text(f"""
        SELECT * FROM available_units_view
        ORDER BY monthly_rent
        LIMIT :limit OFFSET :skip
    """)
    result = await db.execute(query, {"limit": limit, "skip": skip})
    units = result.fetchall()

    # Convert to dict for Pydantic
    units_list = [dict(row._mapping) for row in units]

    return {"total": total, "items": units_list}


@router.get("/{unit_id}", response_model=Unit)
async def get_unit(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a specific unit by ID (Admin/Manager only)"""
    query = select(UnitModel).where(UnitModel.id == unit_id)
    result = await db.execute(query)
    unit_obj = result.scalar_one_or_none()

    if not unit_obj:
        raise HTTPException(status_code=404, detail="Unit not found")

    return unit_obj


@router.put("/{unit_id}", response_model=Unit)
async def update_unit(
    unit_id: UUID,
    unit_data: UnitUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Update a unit (Admin only)"""
    query = select(UnitModel).where(UnitModel.id == unit_id)
    result = await db.execute(query)
    unit_obj = result.scalar_one_or_none()

    if not unit_obj:
        raise HTTPException(status_code=404, detail="Unit not found")

    # Check for duplicate unit number if updating unit_number
    if unit_data.unit_number and unit_data.unit_number != unit_obj.unit_number:
        duplicate_query = select(UnitModel).where(
            UnitModel.building_id == unit_obj.building_id,
            UnitModel.unit_number == unit_data.unit_number,
            UnitModel.id != unit_id
        )
        duplicate_result = await db.execute(duplicate_query)
        if duplicate_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Unit {unit_data.unit_number} already exists in this building"
            )

    # Update only provided fields
    update_data = unit_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(unit_obj, key, value)

    await db.flush()
    await db.refresh(unit_obj)
    return unit_obj


@router.patch("/{unit_id}/status", response_model=Unit)
async def update_unit_status(
    unit_id: UUID,
    status: str = Query(..., pattern="^(vacant|occupied|maintenance|unavailable)$"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Update only the unit status (Admin only)"""
    query = select(UnitModel).where(UnitModel.id == unit_id)
    result = await db.execute(query)
    unit_obj = result.scalar_one_or_none()

    if not unit_obj:
        raise HTTPException(status_code=404, detail="Unit not found")

    unit_obj.status = status
    await db.flush()
    await db.refresh(unit_obj)
    return unit_obj


@router.delete("/{unit_id}", status_code=204)
async def delete_unit(
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Delete a unit (Admin only)"""
    query = select(UnitModel).where(UnitModel.id == unit_id)
    result = await db.execute(query)
    unit_obj = result.scalar_one_or_none()

    if not unit_obj:
        raise HTTPException(status_code=404, detail="Unit not found")

    await db.delete(unit_obj)
    return None
