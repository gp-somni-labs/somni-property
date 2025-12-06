"""
Somni Property Manager - Properties API
CRUD endpoints for property management

DEPRECATED: This API is deprecated. Use /buildings instead.
Properties and Buildings were redundant concepts. Buildings is now the single source of truth.
This endpoint is maintained for backwards compatibility only.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Annotated
from uuid import UUID

from db.database import get_db
from db.models import Property as PropertyModel
from api.schemas import Property, PropertyCreate, PropertyUpdate, PropertyList
from core.auth import AuthUser, require_admin, require_manager

router = APIRouter()


def add_deprecation_header(response: Response):
    """Add deprecation header to all responses"""
    response.headers["X-Deprecated"] = "Use /buildings instead"
    return response


@router.post("", response_model=Property, status_code=201)
async def create_property(
    property_data: PropertyCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Create a new property (Admin only)

    DEPRECATED: Use POST /buildings instead. Properties and Buildings were redundant.
    """
    add_deprecation_header(response)
    property_obj = PropertyModel(**property_data.model_dump())
    db.add(property_obj)
    await db.flush()
    await db.refresh(property_obj)
    return property_obj


@router.get("", response_model=PropertyList)
async def list_properties(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all properties with pagination (Admin/Manager only)

    DEPRECATED: Use GET /buildings instead. Properties and Buildings were redundant.
    """
    add_deprecation_header(response)
    # Get total count
    count_query = select(func.count()).select_from(PropertyModel)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get properties
    query = select(PropertyModel).offset(skip).limit(limit).order_by(PropertyModel.created_at.desc())
    result = await db.execute(query)
    properties = result.scalars().all()

    return PropertyList(total=total, items=properties)


@router.get("/{property_id}", response_model=Property)
async def get_property(
    property_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get a specific property by ID (Admin/Manager only)

    DEPRECATED: Use GET /buildings/{id} instead. Properties and Buildings were redundant.
    """
    add_deprecation_header(response)
    query = select(PropertyModel).where(PropertyModel.id == property_id)
    result = await db.execute(query)
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    return property_obj


@router.put("/{property_id}", response_model=Property)
async def update_property(
    property_id: UUID,
    property_data: PropertyUpdate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Update a property (Admin only)

    DEPRECATED: Use PUT /buildings/{id} instead. Properties and Buildings were redundant.
    """
    add_deprecation_header(response)
    query = select(PropertyModel).where(PropertyModel.id == property_id)
    result = await db.execute(query)
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    # Update only provided fields
    update_data = property_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(property_obj, key, value)

    await db.flush()
    await db.refresh(property_obj)
    return property_obj


@router.delete("/{property_id}", status_code=204)
async def delete_property(
    property_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Delete a property (and all associated buildings/units via CASCADE) (Admin only)

    DEPRECATED: Use DELETE /buildings/{id} instead. Properties and Buildings were redundant.
    """
    add_deprecation_header(response)
    query = select(PropertyModel).where(PropertyModel.id == property_id)
    result = await db.execute(query)
    property_obj = result.scalar_one_or_none()

    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    await db.delete(property_obj)
    return None
