"""
Somni Property Manager - Service Packages API
CRUD endpoints for smart home service package management (Basic/Premium/Enterprise tiers)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Annotated
from uuid import UUID

from db.database import get_db
from db.models import ServicePackage as ServicePackageModel
from api.schemas import (
    ServicePackage,
    ServicePackageCreate,
    ServicePackageUpdate,
    ServicePackageListResponse
)
from core.auth import AuthUser, require_admin, require_manager

router = APIRouter()


@router.post("", response_model=ServicePackage, status_code=201)
async def create_service_package(
    package_data: ServicePackageCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Create a new service package (Admin only)

    Service packages define tiered smart home offerings:
    - Basic: Entry-level monitoring and support
    - Premium: Advanced automation and analytics
    - Enterprise: Unlimited devices with custom integration
    """
    package_obj = ServicePackageModel(**package_data.model_dump())
    db.add(package_obj)
    await db.flush()
    await db.refresh(package_obj)
    return package_obj


@router.get("", response_model=ServicePackageListResponse)
async def list_service_packages(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True, description="Only show active packages"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all service packages with pagination (Admin/Manager only)

    Query parameters:
    - active_only: Filter to only show active packages (default: true)
    - skip: Pagination offset
    - limit: Maximum number of items to return
    """
    # Build query with optional filters
    query_base = select(ServicePackageModel)
    if active_only:
        query_base = query_base.where(ServicePackageModel.active == True)

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get packages
    query = query_base.offset(skip).limit(limit).order_by(ServicePackageModel.monthly_fee.asc())
    result = await db.execute(query)
    packages = result.scalars().all()

    return ServicePackageListResponse(
        items=packages,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{package_id}", response_model=ServicePackage)
async def get_service_package(
    package_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a specific service package by ID (Admin/Manager only)"""
    query = select(ServicePackageModel).where(ServicePackageModel.id == package_id)
    result = await db.execute(query)
    package_obj = result.scalar_one_or_none()

    if not package_obj:
        raise HTTPException(status_code=404, detail="Service package not found")

    return package_obj


@router.put("/{package_id}", response_model=ServicePackage)
async def update_service_package(
    package_id: UUID,
    package_data: ServicePackageUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Update a service package (Admin only)

    Use this to modify pricing, features, or deactivate packages.
    Deactivating a package prevents new subscriptions but doesn't affect existing contracts.
    """
    query = select(ServicePackageModel).where(ServicePackageModel.id == package_id)
    result = await db.execute(query)
    package_obj = result.scalar_one_or_none()

    if not package_obj:
        raise HTTPException(status_code=404, detail="Service package not found")

    # Update only provided fields
    update_data = package_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(package_obj, key, value)

    await db.flush()
    await db.refresh(package_obj)
    return package_obj


@router.delete("/{package_id}", status_code=204)
async def delete_service_package(
    package_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Delete a service package (Admin only)

    WARNING: This is prevented if active contracts reference this package.
    Deactivate the package instead to prevent new subscriptions while preserving existing contracts.
    """
    query = select(ServicePackageModel).where(ServicePackageModel.id == package_id)
    result = await db.execute(query)
    package_obj = result.scalar_one_or_none()

    if not package_obj:
        raise HTTPException(status_code=404, detail="Service package not found")

    try:
        await db.delete(package_obj)
        await db.flush()
    except Exception as e:
        # Foreign key constraint violation (active contracts exist)
        raise HTTPException(
            status_code=400,
            detail="Cannot delete package with active contracts. Deactivate it instead."
        )

    return None
