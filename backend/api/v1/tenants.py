"""
Tenants API Endpoints
Tenant management with role-based access control
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, Annotated
from uuid import UUID
from datetime import date

from db.database import get_db
from db.models import Tenant, Lease
from api.schemas import TenantCreate, TenantUpdate, TenantResponse, TenantListResponse
from core.auth import get_auth_user, require_admin, require_manager, get_current_tenant, AuthUser, CurrentTenant, can_access_tenant_data

router = APIRouter()


# ============================================================================
# TENANT CRUD ENDPOINTS
# ============================================================================

@router.get("", response_model=TenantListResponse)
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[str] = Query(None, description="Filter by status: active, former, applicant"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all tenants (admin/manager only)

    **Permissions:**
    - Admin: Can view all tenants
    - Manager: Can view all tenants
    - Tenant: Forbidden
    """
    # Require admin or manager role
    if not (auth_user.is_admin or auth_user.is_manager):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and managers can list all tenants"
        )

    # Build query
    query = select(Tenant)

    # Apply filters
    if status_filter:
        query = query.where(Tenant.status == status_filter)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Tenant.first_name.ilike(search_pattern)) |
            (Tenant.last_name.ilike(search_pattern)) |
            (Tenant.email.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Tenant.created_at.desc())

    # Execute query
    result = await db.execute(query)
    tenants = result.scalars().all()

    return TenantListResponse(
        items=tenants,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new tenant (manager/admin only)

    **Permissions:**
    - Admin: Can create tenants
    - Manager: Can create tenants
    - Tenant: Forbidden
    """

    # Check if email already exists
    existing = await db.execute(
        select(Tenant).where(Tenant.email == tenant_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with email {tenant_data.email} already exists"
        )

    # Create tenant
    tenant = Tenant(**tenant_data.model_dump())
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    return tenant


@router.get("/me", response_model=TenantResponse)
async def get_my_profile(
    current_tenant: CurrentTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated tenant's profile

    **Permissions:**
    - Any authenticated tenant can access their own profile
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == UUID(current_tenant.id))
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant profile not found"
        )

    return tenant


@router.put("/me", response_model=TenantResponse)
async def update_my_profile(
    tenant_data: TenantUpdate,
    current_tenant: CurrentTenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current authenticated tenant's profile

    **Permissions:**
    - Tenants can only update their own profile
    - Cannot change: status, portal_enabled, auth_user_id (admin-only fields)
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == UUID(current_tenant.id))
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant profile not found"
        )

    # Update only allowed fields (exclude admin-only fields)
    update_data = tenant_data.model_dump(exclude_unset=True, exclude={'status', 'portal_enabled', 'auth_user_id'})

    for key, value in update_data.items():
        setattr(tenant, key, value)

    await db.commit()
    await db.refresh(tenant)

    return tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    current_tenant: Optional[CurrentTenant] = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Get tenant by ID

    **Permissions:**
    - Admin/Manager: Can view any tenant
    - Tenant: Can only view their own profile (use /me instead)
    """
    # Check permissions
    if not can_access_tenant_data(auth_user, str(tenant_id), current_tenant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own profile"
        )

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    auth_user: AuthUser = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Update tenant by ID (manager/admin only)

    **Permissions:**
    - Admin/Manager: Can update any tenant
    - Tenant: Use /me endpoint instead
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    # Update all provided fields (managers can change admin fields)
    update_data = tenant_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(tenant, key, value)

    await db.commit()
    await db.refresh(tenant)

    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    auth_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete tenant by ID (admin only)

    **Permissions:**
    - Admin only

    **Note:** This will cascade delete all related leases, work orders, and documents
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )

    await db.delete(tenant)
    await db.commit()

    return None


# ============================================================================
# TENANT RELATIONSHIPS
# ============================================================================

@router.get("/{tenant_id}/leases")
async def get_tenant_leases(
    tenant_id: UUID,
    active_only: bool = Query(False, description="Show only active leases"),
    auth_user: AuthUser = Depends(get_auth_user),
    current_tenant: Optional[CurrentTenant] = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all leases for a tenant

    **Permissions:**
    - Admin/Manager: Can view any tenant's leases
    - Tenant: Can only view their own leases
    """
    # Check permissions
    if not can_access_tenant_data(auth_user, str(tenant_id), current_tenant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own leases"
        )

    # Build query
    query = select(Lease).where(Lease.tenant_id == tenant_id)

    if active_only:
        query = query.where(Lease.status == "active")

    query = query.order_by(Lease.start_date.desc())

    result = await db.execute(query)
    leases = result.scalars().all()

    return {"items": leases, "total": len(leases)}


@router.get("/{tenant_id}/work-orders")
async def get_tenant_work_orders(
    tenant_id: UUID,
    auth_user: AuthUser = Depends(get_auth_user),
    current_tenant: Optional[CurrentTenant] = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all work orders created by a tenant

    **Permissions:**
    - Admin/Manager: Can view any tenant's work orders
    - Tenant: Can only view their own work orders
    """
    # Check permissions
    if not can_access_tenant_data(auth_user, str(tenant_id), current_tenant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own work orders"
        )

    # TODO: Import WorkOrder model when work orders API is implemented
    # For now, return placeholder
    return {"items": [], "total": 0, "message": "Work orders API not yet implemented"}
