"""
Leases API Endpoints
Lease management with role-based access control
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Optional, Annotated
from uuid import UUID
from datetime import date, timedelta

from db.database import get_db
from db.models import Lease, Tenant, Unit, Building
from api.schemas import LeaseCreate, LeaseUpdate, LeaseResponse, LeaseListResponse
from core.auth import get_auth_user, require_admin, require_manager, get_current_tenant, AuthUser, CurrentTenant

router = APIRouter()


# ============================================================================
# LEASE CRUD ENDPOINTS
# ============================================================================

@router.get("/active", response_model=LeaseListResponse)
async def get_active_leases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    auth_user: AuthUser = Depends(get_auth_user),
    current_tenant: Optional[CurrentTenant] = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active leases (convenience endpoint)

    **Permissions:**
    - Admin/Manager: Can view all active leases
    - Tenant: Can only view their own active leases
    """
    # Build query
    query = select(Lease).where(Lease.status == "active")

    # Apply role-based filtering
    if not (auth_user.is_admin or auth_user.is_manager):
        # Tenants can only see their own leases
        if current_tenant:
            query = query.where(Lease.tenant_id == UUID(current_tenant.id))
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenants can only view their own leases"
            )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Lease.start_date.desc())

    # Execute query
    result = await db.execute(query)
    leases = result.scalars().all()

    return LeaseListResponse(
        items=leases,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/expiring", response_model=LeaseListResponse)
async def get_expiring_leases_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    days: int = Query(30, ge=1, le=365, description="Days until expiration"),
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Get leases expiring within X days (manager/admin only)

    Useful for lease renewal notifications (convenience endpoint)
    """
    today = date.today()
    expiration_threshold = today + timedelta(days=days)

    query = select(Lease).where(
        and_(
            Lease.status == "active",
            Lease.end_date <= expiration_threshold,
            Lease.end_date >= today
        )
    )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Lease.end_date.asc())

    # Execute query
    result = await db.execute(query)
    leases = result.scalars().all()

    return LeaseListResponse(
        items=leases,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("", response_model=LeaseListResponse)
async def list_leases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, description="Filter by status: draft, active, expired, terminated"),
    unit_id: Optional[UUID] = Query(None, description="Filter by unit"),
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant"),
    building_id: Optional[UUID] = Query(None, description="Filter by building"),
    client_id: Optional[UUID] = Query(None, description="Filter by client (owner)"),
    active_only: bool = Query(False, description="Show only active leases"),
    auth_user: AuthUser = Depends(get_auth_user),
    current_tenant: Optional[CurrentTenant] = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    List all leases with filtering

    **Permissions:**
    - Admin/Manager: Can view all leases
    - Tenant: Can only view their own leases

    **Filters:**
    - building_id: Filter leases by building (for multi-unit properties)
    - client_id: Filter leases by client/owner (for portfolio management)
    """
    # Build query
    query = select(Lease)

    # Apply role-based filtering
    if not (auth_user.is_admin or auth_user.is_manager):
        # Tenants can only see their own leases
        if current_tenant:
            query = query.where(Lease.tenant_id == UUID(current_tenant.id))
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenants can only view their own leases"
            )

    # Apply filters
    if status_filter:
        query = query.where(Lease.status == status_filter)

    if unit_id:
        query = query.where(Lease.unit_id == unit_id)

    if tenant_id:
        # Managers/admins can filter by any tenant
        # Tenants can only filter by themselves
        if not (auth_user.is_admin or auth_user.is_manager):
            if not current_tenant or str(tenant_id) != current_tenant.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own leases"
                )
        query = query.where(Lease.tenant_id == tenant_id)

    if building_id:
        query = query.where(Lease.building_id == building_id)

    if client_id:
        query = query.where(Lease.client_id == client_id)

    if active_only:
        query = query.where(Lease.status == "active")

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Lease.start_date.desc())

    # Execute query
    result = await db.execute(query)
    leases = result.scalars().all()

    return LeaseListResponse(
        items=leases,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("", response_model=LeaseResponse, status_code=status.HTTP_201_CREATED)
async def create_lease(
    lease_data: LeaseCreate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new lease (manager/admin only)

    **Permissions:**
    - Admin/Manager: Can create leases
    - Tenant: Forbidden

    **Validation:**
    - Unit must exist
    - Tenant must exist
    - End date must be after start date
    - Checks for overlapping leases on the same unit
    """

    # Validate unit exists
    unit_result = await db.execute(
        select(Unit).where(Unit.id == lease_data.unit_id)
    )
    unit = unit_result.scalar_one_or_none()
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unit {lease_data.unit_id} not found"
        )

    # Validate tenant exists
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == lease_data.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {lease_data.tenant_id} not found"
        )

    # Validate dates
    if lease_data.end_date <= lease_data.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )

    # Check for overlapping leases on the same unit
    overlapping_result = await db.execute(
        select(Lease).where(
            and_(
                Lease.unit_id == lease_data.unit_id,
                Lease.status.in_(["active", "draft"]),
                or_(
                    # New lease starts during existing lease
                    and_(
                        Lease.start_date <= lease_data.start_date,
                        Lease.end_date >= lease_data.start_date
                    ),
                    # New lease ends during existing lease
                    and_(
                        Lease.start_date <= lease_data.end_date,
                        Lease.end_date >= lease_data.end_date
                    ),
                    # New lease completely encompasses existing lease
                    and_(
                        Lease.start_date >= lease_data.start_date,
                        Lease.end_date <= lease_data.end_date
                    )
                )
            )
        )
    )
    overlapping = overlapping_result.scalar_one_or_none()

    if overlapping:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Unit {lease_data.unit_id} already has an active lease from {overlapping.start_date} to {overlapping.end_date}"
        )

    # Create lease
    lease = Lease(**lease_data.model_dump())
    db.add(lease)

    # Update unit status to occupied if lease is active
    if lease_data.status == "active":
        unit.status = "occupied"

    # Update tenant status to active if lease is active
    if lease_data.status == "active" and tenant.status == "applicant":
        tenant.status = "active"

    await db.commit()
    await db.refresh(lease)

    return lease


@router.get("/{lease_id}", response_model=LeaseResponse)
async def get_lease(
    lease_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    current_tenant: Optional[CurrentTenant] = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Get lease by ID

    **Permissions:**
    - Admin/Manager: Can view any lease
    - Tenant: Can only view their own leases
    """
    result = await db.execute(
        select(Lease).where(Lease.id == lease_id)
    )
    lease = result.scalar_one_or_none()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lease not found"
        )

    # Check permissions
    if not (auth_user.is_admin or auth_user.is_manager):
        if not current_tenant or str(lease.tenant_id) != current_tenant.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own leases"
            )

    return lease


@router.put("/{lease_id}", response_model=LeaseResponse)
async def update_lease(
    lease_id: UUID,
    lease_data: LeaseUpdate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Update lease by ID (manager/admin only)

    **Permissions:**
    - Admin/Manager: Can update any lease
    - Tenant: Forbidden
    """
    result = await db.execute(
        select(Lease).where(Lease.id == lease_id)
    )
    lease = result.scalar_one_or_none()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lease not found"
        )

    # Update fields
    update_data = lease_data.model_dump(exclude_unset=True)

    # Validate end date if being updated
    if "end_date" in update_data:
        if update_data["end_date"] <= lease.start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )

    for key, value in update_data.items():
        setattr(lease, key, value)

    # Update unit status based on lease status
    if "status" in update_data:
        unit_result = await db.execute(
            select(Unit).where(Unit.id == lease.unit_id)
        )
        unit = unit_result.scalar_one_or_none()

        if unit:
            if update_data["status"] == "active":
                unit.status = "occupied"
            elif update_data["status"] in ["expired", "terminated"]:
                # Check if there are other active leases for this unit
                other_active = await db.execute(
                    select(Lease).where(
                        and_(
                            Lease.unit_id == lease.unit_id,
                            Lease.id != lease_id,
                            Lease.status == "active"
                        )
                    )
                )
                if not other_active.scalar_one_or_none():
                    unit.status = "vacant"

    await db.commit()
    await db.refresh(lease)

    return lease


@router.delete("/{lease_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lease(
    lease_id: UUID,
    auth_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete lease by ID (admin only)

    **Permissions:**
    - Admin only

    **Note:** This will cascade delete all related rent payments
    """
    result = await db.execute(
        select(Lease).where(Lease.id == lease_id)
    )
    lease = result.scalar_one_or_none()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lease not found"
        )

    await db.delete(lease)
    await db.commit()

    return None


# ============================================================================
# LEASE ACTIONS
# ============================================================================

@router.post("/{lease_id}/renew", response_model=LeaseResponse)
async def renew_lease(
    lease_id: UUID,
    new_end_date: date = Query(..., description="New lease end date"),
    new_monthly_rent: Optional[float] = Query(None, description="Updated monthly rent"),
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Renew an existing lease (manager/admin only)

    Creates a new lease record with updated dates and optionally new rent
    Original lease is marked as terminated
    """
    result = await db.execute(
        select(Lease).where(Lease.id == lease_id)
    )
    original_lease = result.scalar_one_or_none()

    if not original_lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lease not found"
        )

    if original_lease.status not in ["active", "expired"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot renew lease with status: {original_lease.status}"
        )

    # Validate new end date
    new_start_date = original_lease.end_date + timedelta(days=1)
    if new_end_date <= new_start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New end date must be after current lease end date"
        )

    # Mark original lease as terminated
    original_lease.status = "terminated"

    # Create renewed lease
    renewed_lease = Lease(
        unit_id=original_lease.unit_id,
        tenant_id=original_lease.tenant_id,
        start_date=new_start_date,
        end_date=new_end_date,
        monthly_rent=new_monthly_rent or original_lease.monthly_rent,
        security_deposit=original_lease.security_deposit,
        rent_due_day=original_lease.rent_due_day,
        late_fee_amount=original_lease.late_fee_amount,
        late_fee_grace_days=original_lease.late_fee_grace_days,
        utilities_included=original_lease.utilities_included,
        status="active"
    )

    db.add(renewed_lease)
    await db.commit()
    await db.refresh(renewed_lease)

    return renewed_lease


@router.post("/{lease_id}/terminate", response_model=LeaseResponse)
async def terminate_lease(
    lease_id: UUID,
    termination_date: date = Query(..., description="Lease termination date"),
    reason: Optional[str] = Query(None, description="Termination reason"),
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Terminate a lease early (manager/admin only)

    **Permissions:**
    - Admin/Manager only
    """
    result = await db.execute(
        select(Lease).where(Lease.id == lease_id)
    )
    lease = result.scalar_one_or_none()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lease not found"
        )

    if lease.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot terminate lease with status: {lease.status}"
        )

    # Validate termination date
    if termination_date < lease.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Termination date cannot be before lease start date"
        )

    # Update lease
    lease.status = "terminated"
    lease.end_date = termination_date

    # Update unit status to vacant
    unit_result = await db.execute(
        select(Unit).where(Unit.id == lease.unit_id)
    )
    unit = unit_result.scalar_one_or_none()
    if unit:
        unit.status = "vacant"
        unit.available_date = termination_date

    await db.commit()
    await db.refresh(lease)

    return lease


# ============================================================================
# LEASE UTILITIES
# ============================================================================

@router.get("/expiring-soon", response_model=LeaseListResponse)
async def get_expiring_leases(
    days: int = Query(30, ge=1, le=365, description="Days until expiration"),
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Get leases expiring within X days (manager/admin only)

    Useful for lease renewal notifications
    """
    today = date.today()
    expiration_threshold = today + timedelta(days=days)

    result = await db.execute(
        select(Lease).where(
            and_(
                Lease.status == "active",
                Lease.end_date <= expiration_threshold,
                Lease.end_date >= today
            )
        ).order_by(Lease.end_date.asc())
    )
    leases = result.scalars().all()

    return LeaseListResponse(
        items=leases,
        total=len(leases),
        skip=0,
        limit=len(leases)
    )
