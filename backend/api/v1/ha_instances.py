"""
Somni Property Manager - HA Instances API
CRUD endpoints for managing Home Assistant instances.

This API supports the unified Flutter app for HA management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from db.database import get_db
from db.models import HAInstance, HATerminalSession, HALogAnalysis, HACommandApproval
from api.schemas_ha_instance import (
    HAInstanceCreate,
    HAInstanceUpdate,
    HAInstanceResponse,
    HAInstanceListResponse,
    HAInstanceStatus,
    HAInstanceBulkStatusRequest,
    HAInstanceBulkStatusResponse,
    HALogAnalysisRequest,
    HALogAnalysisResponse,
    HALogAnalysisListResponse,
    HACommandApprovalRequest,
    HACommandApprovalResponse,
    HAPendingCommandsResponse
)
from core.auth import AuthUser, require_admin, require_manager
from services.ha_instance_service import HAInstanceService

router = APIRouter()

# Service instance
ha_service = HAInstanceService()


# ============================================================================
# CRUD OPERATIONS
# ============================================================================

@router.post("", response_model=HAInstanceResponse, status_code=201)
async def create_ha_instance(
    instance_data: HAInstanceCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Create a new HA Instance (Admin only)

    Creates a standalone Home Assistant instance entry for the Flutter app.
    This is separate from PropertyEdgeNode - used for family homes not in property management.
    """
    # Check for duplicate host
    existing_query = select(HAInstance).where(HAInstance.host == instance_data.host)
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"HA Instance with host {instance_data.host} already exists"
        )

    # Extract API token for encryption (if provided)
    api_token = instance_data.ha_api_token
    instance_dict = instance_data.model_dump(exclude={"ha_api_token"})

    # Encrypt token if provided
    if api_token:
        encrypted_token = ha_service.encrypt_api_token(api_token)
        instance_dict["ha_api_token_encrypted"] = encrypted_token

    instance_dict["created_by"] = auth_user.username

    instance = HAInstance(**instance_dict)
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    return instance


@router.get("", response_model=HAInstanceListResponse)
async def list_ha_instances(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by status"),
    instance_type: Optional[str] = Query(None, description="Filter by instance type"),
    is_enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    search: Optional[str] = Query(None, description="Search by name or location"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all HA Instances with pagination and filtering (Manager+)

    Returns instances the Flutter app can manage.
    """
    query_base = select(HAInstance)

    # Apply filters
    if status:
        query_base = query_base.where(HAInstance.status == status)
    if instance_type:
        query_base = query_base.where(HAInstance.instance_type == instance_type)
    if is_enabled is not None:
        query_base = query_base.where(HAInstance.is_enabled == is_enabled)
    if search:
        search_pattern = f"%{search}%"
        query_base = query_base.where(
            (HAInstance.name.ilike(search_pattern)) |
            (HAInstance.location.ilike(search_pattern))
        )

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get instances
    query = query_base.offset(skip).limit(limit).order_by(HAInstance.name)
    result = await db.execute(query)
    instances = result.scalars().all()

    return HAInstanceListResponse(
        items=instances,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/online", response_model=HAInstanceListResponse)
async def list_online_instances(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """List all online HA Instances"""
    query_base = select(HAInstance).where(
        HAInstance.status == "online",
        HAInstance.is_enabled == True
    )

    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query_base.offset(skip).limit(limit).order_by(HAInstance.last_seen_at.desc())
    result = await db.execute(query)
    instances = result.scalars().all()

    return HAInstanceListResponse(items=instances, total=total, skip=skip, limit=limit)


@router.get("/{instance_id}", response_model=HAInstanceResponse)
async def get_ha_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a single HA Instance by ID"""
    query = select(HAInstance).where(HAInstance.id == instance_id)
    result = await db.execute(query)
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="HA Instance not found")

    return instance


@router.put("/{instance_id}", response_model=HAInstanceResponse)
async def update_ha_instance(
    instance_id: UUID,
    instance_data: HAInstanceUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Update an HA Instance (Admin only)"""
    query = select(HAInstance).where(HAInstance.id == instance_id)
    result = await db.execute(query)
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="HA Instance not found")

    # Check for duplicate host if changing
    if instance_data.host and instance_data.host != instance.host:
        existing_query = select(HAInstance).where(
            HAInstance.host == instance_data.host,
            HAInstance.id != instance_id
        )
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"HA Instance with host {instance_data.host} already exists"
            )

    # Update fields
    update_dict = instance_data.model_dump(exclude_unset=True, exclude={"ha_api_token"})

    # Handle API token update
    if instance_data.ha_api_token:
        encrypted_token = ha_service.encrypt_api_token(instance_data.ha_api_token)
        update_dict["ha_api_token_encrypted"] = encrypted_token

    for key, value in update_dict.items():
        setattr(instance, key, value)

    instance.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(instance)
    return instance


@router.delete("/{instance_id}")
async def delete_ha_instance(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Delete an HA Instance (Admin only)"""
    query = select(HAInstance).where(HAInstance.id == instance_id)
    result = await db.execute(query)
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="HA Instance not found")

    await db.delete(instance)
    await db.commit()

    return {"message": f"HA Instance '{instance.name}' deleted successfully"}


# ============================================================================
# STATUS OPERATIONS
# ============================================================================

@router.get("/{instance_id}/status", response_model=HAInstanceStatus)
async def check_instance_status(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Check HA Instance status via SSH

    Connects to the instance and retrieves HA version, health, and uptime.
    """
    query = select(HAInstance).where(HAInstance.id == instance_id)
    result = await db.execute(query)
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="HA Instance not found")

    # Check status
    status = await ha_service.check_instance_status(instance)

    # Update database with status
    now = datetime.now(timezone.utc)
    update_values = {
        "last_status_check_at": now,
        "status": "online" if status.online else "offline",
    }

    if status.online:
        update_values["last_seen_at"] = now
        update_values["ha_version"] = status.ha_version
        update_values["supervisor_version"] = status.supervisor_version
        update_values["os_type"] = status.os_type
        update_values["uptime_seconds"] = status.uptime_seconds
        update_values["status_message"] = f"Connected, HA version {status.ha_version}"
    else:
        update_values["status_message"] = status.error or "Connection failed"

    await db.execute(
        update(HAInstance)
        .where(HAInstance.id == instance_id)
        .values(**update_values)
    )
    await db.commit()

    return status


@router.post("/bulk-status", response_model=HAInstanceBulkStatusResponse)
async def check_bulk_status(
    request: HAInstanceBulkStatusRequest,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Check status of multiple HA Instances

    Useful for dashboard refresh - checks up to 50 instances in parallel.
    """
    # Get instances
    query = select(HAInstance).where(HAInstance.id.in_(request.instance_ids))
    result = await db.execute(query)
    instances = result.scalars().all()

    if not instances:
        raise HTTPException(status_code=404, detail="No instances found")

    # Check status in parallel
    results = await ha_service.check_multiple_status(instances)

    # Update database
    now = datetime.now(timezone.utc)
    for instance in instances:
        status = results.get(str(instance.id))
        if status:
            update_values = {
                "last_status_check_at": now,
                "status": "online" if status.online else "offline",
            }
            if status.online:
                update_values["last_seen_at"] = now
                update_values["ha_version"] = status.ha_version

            await db.execute(
                update(HAInstance)
                .where(HAInstance.id == instance.id)
                .values(**update_values)
            )

    await db.commit()

    return HAInstanceBulkStatusResponse(
        results=results,
        checked_at=now
    )


@router.post("/{instance_id}/refresh-components")
async def refresh_instance_components(
    instance_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Refresh installed Somni components on an instance

    Scans the HA instance for installed Somni custom components.
    """
    query = select(HAInstance).where(HAInstance.id == instance_id)
    result = await db.execute(query)
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="HA Instance not found")

    # Get installed components
    components = await ha_service.get_installed_components(instance)

    # Update database
    await db.execute(
        update(HAInstance)
        .where(HAInstance.id == instance_id)
        .values(
            installed_somni_components=components,
            last_component_sync_at=datetime.now(timezone.utc)
        )
    )
    await db.commit()

    return {
        "instance_id": str(instance_id),
        "installed_components": components,
        "refreshed_at": datetime.now(timezone.utc).isoformat()
    }


# ============================================================================
# LOG ANALYSIS (Phase 2)
# ============================================================================

@router.post("/{instance_id}/logs/analyze", response_model=HALogAnalysisResponse)
async def analyze_logs(
    instance_id: UUID,
    request: HALogAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Submit log analysis request

    Uses Claude to analyze HA logs and suggest fixes.
    Analysis runs in background - poll for results.
    """
    # Verify instance exists
    query = select(HAInstance).where(HAInstance.id == instance_id)
    result = await db.execute(query)
    instance = result.scalar_one_or_none()

    if not instance:
        raise HTTPException(status_code=404, detail="HA Instance not found")

    # Create analysis record
    analysis = HALogAnalysis(
        instance_id=instance_id,
        question=request.question,
        additional_instance_ids=request.additional_instance_ids,
        log_types=request.log_types,
        time_range_hours=request.time_range_hours,
        analysis_status="pending",
        submitted_by=auth_user.username
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Queue background task
    background_tasks.add_task(
        ha_service.perform_log_analysis,
        analysis_id=analysis.id,
        question=request.question,
        instance_ids=[instance_id] + request.additional_instance_ids
    )

    return analysis


@router.get("/{instance_id}/logs/analyses", response_model=HALogAnalysisListResponse)
async def list_log_analyses(
    instance_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """List log analyses for an instance"""
    query_base = select(HALogAnalysis).where(HALogAnalysis.instance_id == instance_id)

    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query_base.offset(skip).limit(limit).order_by(HALogAnalysis.submitted_at.desc())
    result = await db.execute(query)
    analyses = result.scalars().all()

    return HALogAnalysisListResponse(items=analyses, total=total, skip=skip, limit=limit)


@router.get("/logs/analysis/{analysis_id}", response_model=HALogAnalysisResponse)
async def get_log_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a specific log analysis result"""
    query = select(HALogAnalysis).where(HALogAnalysis.id == analysis_id)
    result = await db.execute(query)
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Log analysis not found")

    return analysis


# ============================================================================
# COMMAND APPROVAL (Phase 2)
# ============================================================================

@router.get("/commands/pending", response_model=HAPendingCommandsResponse)
async def get_pending_commands(
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """Get all pending commands awaiting approval"""
    query = select(HACommandApproval).where(
        HACommandApproval.approval_status == "pending"
    ).order_by(HACommandApproval.created_at.desc())

    result = await db.execute(query)
    commands = result.scalars().all()

    return HAPendingCommandsResponse(
        commands=commands,
        total_pending=len(commands)
    )


@router.post("/commands/{command_id}/approve", response_model=HACommandApprovalResponse)
async def approve_command(
    command_id: UUID,
    request: HACommandApprovalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Approve or reject a suggested command

    If approved, the command will be executed on the target instance.
    """
    query = select(HACommandApproval).where(HACommandApproval.id == command_id)
    result = await db.execute(query)
    command = result.scalar_one_or_none()

    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    if command.approval_status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Command already {command.approval_status}"
        )

    now = datetime.now(timezone.utc)

    if request.approved:
        command.approval_status = "approved"
        command.approved_by = auth_user.username
        command.approved_at = now

        # Execute command in background
        background_tasks.add_task(
            ha_service.execute_approved_command,
            command_id=command.id
        )
    else:
        command.approval_status = "rejected"
        command.approved_by = auth_user.username
        command.approved_at = now
        command.rejection_reason = request.rejection_reason

    await db.commit()
    await db.refresh(command)

    return command
