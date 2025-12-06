"""
Somni Property Manager - Service Contracts API
CRUD endpoints for smart home service contract management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import date

from db.database import get_db
from db.models import ServiceContract as ServiceContractModel
from api.schemas import (
    ServiceContract,
    ServiceContractCreate,
    ServiceContractUpdate,
    ServiceContractListResponse
)
from core.auth import AuthUser, require_admin, require_manager

router = APIRouter()


@router.post("", response_model=ServiceContract, status_code=201)
async def create_service_contract(
    contract_data: ServiceContractCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Create a new service contract (Admin only)

    Service contracts manage smart home service subscriptions:
    - Links client (tenant) to service package
    - Tracks installation status
    - Manages monthly/annual billing
    - Auto-renewal settings
    """
    contract_obj = ServiceContractModel(**contract_data.model_dump())
    db.add(contract_obj)
    await db.flush()
    await db.refresh(contract_obj)
    return contract_obj


@router.get("", response_model=ServiceContractListResponse)
async def list_service_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    property_id: Optional[UUID] = Query(None, description="Filter by property ID"),
    package_id: Optional[UUID] = Query(None, description="Filter by service package ID"),
    status: Optional[str] = Query(None, description="Filter by status (draft/active/paused/cancelled/completed)"),
    contract_type: Optional[str] = Query(None, description="Filter by contract type (monthly/annual/project)"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all service contracts with pagination and filtering (Admin/Manager only)

    Query parameters:
    - client_id: Filter contracts for specific client
    - property_id: Filter contracts for specific property
    - package_id: Filter contracts using specific package
    - status: Filter by contract status
    - contract_type: Filter by contract type
    - skip: Pagination offset
    - limit: Maximum number of items to return
    """
    # Build query with optional filters
    query_base = select(ServiceContractModel)

    if client_id:
        query_base = query_base.where(ServiceContractModel.client_id == client_id)
    if property_id:
        query_base = query_base.where(ServiceContractModel.property_id == property_id)
    if package_id:
        query_base = query_base.where(ServiceContractModel.package_id == package_id)
    if status:
        query_base = query_base.where(ServiceContractModel.status == status)
    if contract_type:
        query_base = query_base.where(ServiceContractModel.contract_type == contract_type)

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get contracts
    query = query_base.offset(skip).limit(limit).order_by(ServiceContractModel.created_at.desc())
    result = await db.execute(query)
    contracts = result.scalars().all()

    return ServiceContractListResponse(
        items=contracts,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/active", response_model=ServiceContractListResponse)
async def list_active_service_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all active service contracts (Admin/Manager only)

    Returns contracts with status='active' ordered by start date.
    """
    query_base = select(ServiceContractModel).where(ServiceContractModel.status == "active")

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get contracts
    query = query_base.offset(skip).limit(limit).order_by(ServiceContractModel.start_date.desc())
    result = await db.execute(query)
    contracts = result.scalars().all()

    return ServiceContractListResponse(
        items=contracts,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{contract_id}", response_model=ServiceContract)
async def get_service_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a specific service contract by ID (Admin/Manager only)"""
    query = select(ServiceContractModel).where(ServiceContractModel.id == contract_id)
    result = await db.execute(query)
    contract_obj = result.scalar_one_or_none()

    if not contract_obj:
        raise HTTPException(status_code=404, detail="Service contract not found")

    return contract_obj


@router.put("/{contract_id}", response_model=ServiceContract)
async def update_service_contract(
    contract_id: UUID,
    contract_data: ServiceContractUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Update a service contract (Admin only)

    Use this to:
    - Update contract dates
    - Change monthly fees
    - Mark installation as completed
    - Update contract status
    """
    query = select(ServiceContractModel).where(ServiceContractModel.id == contract_id)
    result = await db.execute(query)
    contract_obj = result.scalar_one_or_none()

    if not contract_obj:
        raise HTTPException(status_code=404, detail="Service contract not found")

    # Update only provided fields
    update_data = contract_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contract_obj, key, value)

    await db.flush()
    await db.refresh(contract_obj)
    return contract_obj


@router.post("/{contract_id}/cancel", response_model=ServiceContract)
async def cancel_service_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Cancel a service contract (Admin only)

    Sets status to 'cancelled' and prevents auto-renewal.
    Contract remains in system for records.
    """
    query = select(ServiceContractModel).where(ServiceContractModel.id == contract_id)
    result = await db.execute(query)
    contract_obj = result.scalar_one_or_none()

    if not contract_obj:
        raise HTTPException(status_code=404, detail="Service contract not found")

    if contract_obj.status == "cancelled":
        raise HTTPException(status_code=400, detail="Contract is already cancelled")

    contract_obj.status = "cancelled"
    contract_obj.auto_renew = False

    await db.flush()
    await db.refresh(contract_obj)
    return contract_obj


@router.post("/{contract_id}/pause", response_model=ServiceContract)
async def pause_service_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Pause a service contract (Admin only)

    Sets status to 'paused'. Service temporarily suspended but can be reactivated.
    """
    query = select(ServiceContractModel).where(ServiceContractModel.id == contract_id)
    result = await db.execute(query)
    contract_obj = result.scalar_one_or_none()

    if not contract_obj:
        raise HTTPException(status_code=404, detail="Service contract not found")

    if contract_obj.status != "active":
        raise HTTPException(status_code=400, detail="Only active contracts can be paused")

    contract_obj.status = "paused"

    await db.flush()
    await db.refresh(contract_obj)
    return contract_obj


@router.post("/{contract_id}/resume", response_model=ServiceContract)
async def resume_service_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Resume a paused service contract (Admin only)

    Sets status back to 'active'.
    """
    query = select(ServiceContractModel).where(ServiceContractModel.id == contract_id)
    result = await db.execute(query)
    contract_obj = result.scalar_one_or_none()

    if not contract_obj:
        raise HTTPException(status_code=404, detail="Service contract not found")

    if contract_obj.status != "paused":
        raise HTTPException(status_code=400, detail="Only paused contracts can be resumed")

    contract_obj.status = "active"

    await db.flush()
    await db.refresh(contract_obj)
    return contract_obj


@router.delete("/{contract_id}", status_code=204)
async def delete_service_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Delete a service contract (Admin only)

    WARNING: This will also delete associated installations and devices via CASCADE.
    Consider cancelling the contract instead to preserve records.
    """
    query = select(ServiceContractModel).where(ServiceContractModel.id == contract_id)
    result = await db.execute(query)
    contract_obj = result.scalar_one_or_none()

    if not contract_obj:
        raise HTTPException(status_code=404, detail="Service contract not found")

    await db.delete(contract_obj)
    await db.flush()
    return None
