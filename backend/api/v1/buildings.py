"""
Somni Property Manager - Buildings API
CRUD endpoints for building management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID

from db.database import get_db
from db.models import Building as BuildingModel, Property as PropertyModel
from api.schemas import Building, BuildingCreate, BuildingUpdate, BuildingList
from core.auth import AuthUser, require_admin, require_manager

router = APIRouter()


@router.post("", response_model=Building, status_code=201)
async def create_building(
    building_data: BuildingCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Create a new building (Admin only)"""
    # Verify property exists
    property_query = select(PropertyModel).where(PropertyModel.id == building_data.property_id)
    property_result = await db.execute(property_query)
    if not property_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Property not found")

    building_obj = BuildingModel(**building_data.model_dump())
    db.add(building_obj)
    await db.flush()
    await db.refresh(building_obj)
    return building_obj


@router.get("", response_model=BuildingList)
async def list_buildings(
    property_id: Optional[UUID] = Query(None, description="Filter by property ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """List all buildings with optional property filter (Admin/Manager only)"""
    # Build query
    query = select(BuildingModel)
    count_query = select(func.count()).select_from(BuildingModel)

    if property_id:
        query = query.where(BuildingModel.property_id == property_id)
        count_query = count_query.where(BuildingModel.property_id == property_id)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get buildings
    query = query.offset(skip).limit(limit).order_by(BuildingModel.created_at.desc())
    result = await db.execute(query)
    buildings = result.scalars().all()

    return BuildingList(total=total, items=buildings)


@router.get("/{building_id}", response_model=Building)
async def get_building(
    building_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a specific building by ID (Admin/Manager only)"""
    query = select(BuildingModel).where(BuildingModel.id == building_id)
    result = await db.execute(query)
    building_obj = result.scalar_one_or_none()

    if not building_obj:
        raise HTTPException(status_code=404, detail="Building not found")

    return building_obj


@router.put("/{building_id}", response_model=Building)
async def update_building(
    building_id: UUID,
    building_data: BuildingUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Update a building (Admin only)"""
    query = select(BuildingModel).where(BuildingModel.id == building_id)
    result = await db.execute(query)
    building_obj = result.scalar_one_or_none()

    if not building_obj:
        raise HTTPException(status_code=404, detail="Building not found")

    # Update only provided fields
    update_data = building_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(building_obj, key, value)

    await db.flush()
    await db.refresh(building_obj)
    return building_obj


@router.delete("/{building_id}", status_code=204)
async def delete_building(
    building_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Delete a building (and all associated units via CASCADE) (Admin only)"""
    query = select(BuildingModel).where(BuildingModel.id == building_id)
    result = await db.execute(query)
    building_obj = result.scalar_one_or_none()

    if not building_obj:
        raise HTTPException(status_code=404, detail="Building not found")

    await db.delete(building_obj)
    return None
