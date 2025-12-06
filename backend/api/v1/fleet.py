"""
Somni Property Manager - Fleet Management API
Endpoints for deploying and managing Tier 2/3 Kubernetes hubs from Master Hub (Tier 1)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from db.database import get_db
from db.models import PropertyEdgeNode as EdgeNodeModel, FleetDeployment as FleetDeploymentModel
from services.fleet_deployment_service import fleet_deployment_service
from core.auth import AuthUser, require_admin
from core.security.rbac import require_permission, require_role, Role

router = APIRouter()


# ========================================================================
# Pydantic Schemas for Fleet Management API
# ========================================================================

class DeploymentRequest(BaseModel):
    """Request to deploy a service package to hub(s)"""
    hub_ids: Optional[List[UUID]] = Field(None, description="List of hub UUIDs (for custom filter)")
    hub_filter: str = Field(
        ...,
        description="Hub filter: 'all_tier_2', 'all_tier_3', 'all', 'custom'",
        pattern="^(all_tier_2|all_tier_3|all|custom)$"
    )
    service_package_id: UUID = Field(..., description="UUID of the ServicePackage to deploy")
    manifest_version: str = Field(..., description="Git commit SHA or version tag")


class DeploymentResponse(BaseModel):
    """Response after initiating deployment"""
    deployment_id: str = Field(..., description="UUID of the FleetDeployment record")
    status: str = Field(..., description="Deployment status: success|failed")
    message: str = Field(..., description="Human-readable message")
    duration_seconds: Optional[float] = Field(None, description="Deployment duration in seconds")


class BulkDeploymentResponse(BaseModel):
    """Response after bulk deployment to multiple hubs"""
    total_hubs: int = Field(..., description="Total number of hubs targeted")
    successful: int = Field(..., description="Number of successful deployments")
    failed: int = Field(..., description="Number of failed deployments")
    deployments: List[dict] = Field(..., description="Individual deployment results")


class FleetDeployment(BaseModel):
    """Fleet deployment record"""
    deployment_id: str
    hub_id: str
    service_package_id: str
    manifest_version: str
    status: str
    initiated_at: str
    completed_at: Optional[str]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    initiated_by: str

    class Config:
        from_attributes = True


class FleetDeploymentListResponse(BaseModel):
    """Paginated list of deployments"""
    items: List[FleetDeployment]
    total: int
    skip: int
    limit: int


class FleetStatusHub(BaseModel):
    """Status of a single hub in the fleet"""
    hub_id: str
    hostname: str
    hub_type: str
    status: str
    deployed_stack: Optional[str]
    manifest_version: Optional[str]
    sync_status: str
    last_sync: Optional[str]
    last_heartbeat: Optional[str]
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    device_count: int


class FleetStatusResponse(BaseModel):
    """Overall fleet status"""
    total_hubs: int
    tier_2_hubs: int
    tier_3_hubs: int
    online_hubs: int
    offline_hubs: int
    hubs_needing_sync: int
    hubs: List[FleetStatusHub]


class RemoteCommandRequest(BaseModel):
    """Request to execute remote command on hub(s)"""
    hub_ids: List[UUID] = Field(..., description="List of hub UUIDs to target")
    command: str = Field(
        ...,
        description="Command to execute: restart_service|update_manifest|sync_devices_now|restart_hub|collect_logs"
    )
    params: Optional[dict] = Field(None, description="Command parameters")


class RemoteCommandResponse(BaseModel):
    """Response after executing remote command"""
    total_hubs: int
    successful: int
    failed: int
    results: List[dict]


class RollbackRequest(BaseModel):
    """Request to rollback a hub to previous version"""
    hub_id: UUID = Field(..., description="UUID of the hub to rollback")
    previous_manifest_version: str = Field(..., description="Git commit SHA to rollback to")


# ========================================================================
# Fleet Management Endpoints
# ========================================================================

@router.post("/deploy", response_model=BulkDeploymentResponse, status_code=200)
@require_permission("deployments", "create")
async def deploy_to_fleet(
    deployment_request: DeploymentRequest,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Deploy a service package to selected hubs (Admin or Operator)

    RBAC: Requires 'create' permission on 'deployments' resource

    Supports:
    - Single hub deployments (hub_filter='custom', hub_ids=[uuid])
    - Tier-based bulk deployments (hub_filter='all_tier_2'|'all_tier_3'|'all')

    Process:
    1. Fetch service package manifest definition
    2. Get hub connection info (Tailscale IP, API token)
    3. Fetch manifests from Git repository
    4. Push manifests to hub's GitOps controller (ArgoCD/Flux)
    5. Monitor deployment status
    6. Record deployment results

    Returns:
        BulkDeploymentResponse with deployment results per hub
    """
    try:
        result = await fleet_deployment_service.bulk_deploy(
            hub_filter=deployment_request.hub_filter,
            service_package_id=str(deployment_request.service_package_id),
            manifest_version=deployment_request.manifest_version,
            initiated_by=auth_user.username,
            hub_ids=[str(hub_id) for hub_id in deployment_request.hub_ids] if deployment_request.hub_ids else None
        )

        return BulkDeploymentResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@router.get("/deployments", response_model=FleetDeploymentListResponse)
async def list_deployments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    hub_id: Optional[UUID] = Query(None, description="Filter by hub ID"),
    status: Optional[str] = Query(None, description="Filter by status (pending/deploying/success/failed)"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    List all fleet deployments with pagination and filtering (Admin only)

    Query parameters:
    - hub_id: Filter deployments for specific hub
    - status: Filter by deployment status
    - skip: Pagination offset
    - limit: Maximum number of items to return
    """
    # Build query with optional filters
    query_base = select(FleetDeploymentModel)

    if hub_id:
        query_base = query_base.where(FleetDeploymentModel.target_hub_id == hub_id)
    if status:
        query_base = query_base.where(FleetDeploymentModel.deployment_status == status)

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get deployments
    query = query_base.offset(skip).limit(limit).order_by(FleetDeploymentModel.initiated_at.desc())
    result = await db.execute(query)
    deployments = result.scalars().all()

    # Convert to response models
    items = []
    for deployment in deployments:
        duration = None
        if deployment.completed_at:
            duration = (deployment.completed_at - deployment.initiated_at).total_seconds()

        items.append(FleetDeployment(
            deployment_id=str(deployment.id),
            hub_id=str(deployment.target_hub_id),
            service_package_id=str(deployment.service_package_id),
            manifest_version=deployment.manifest_version,
            status=deployment.deployment_status,
            initiated_at=deployment.initiated_at.isoformat(),
            completed_at=deployment.completed_at.isoformat() if deployment.completed_at else None,
            duration_seconds=duration,
            error_message=deployment.error_message,
            initiated_by=deployment.initiated_by
        ))

    return FleetDeploymentListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/deployments/{deployment_id}", response_model=FleetDeployment)
async def get_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Get details of a specific deployment (Admin only)

    Includes:
    - Deployment status
    - Deployment logs
    - Error messages (if failed)
    - Duration
    """
    try:
        result = await fleet_deployment_service.get_deployment_status(str(deployment_id))
        return FleetDeployment(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get deployment: {str(e)}")


@router.get("/status", response_model=FleetStatusResponse)
async def get_fleet_status(
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Get overall fleet status (Admin only)

    Returns:
    - Total hubs (Tier 2 vs Tier 3 breakdown)
    - Online/offline status
    - Hubs needing sync
    - Resource utilization per hub
    """
    # Get all managed hubs
    stmt = select(EdgeNodeModel).where(EdgeNodeModel.managed_by_tier1 == True)
    result = await db.execute(stmt)
    all_hubs = result.scalars().all()

    # Calculate statistics
    total_hubs = len(all_hubs)
    tier_2_hubs = sum(1 for hub in all_hubs if hub.hub_type == 'tier_2_property')
    tier_3_hubs = sum(1 for hub in all_hubs if hub.hub_type == 'tier_3_residential')
    online_hubs = sum(1 for hub in all_hubs if hub.status == 'online')
    offline_hubs = total_hubs - online_hubs
    hubs_needing_sync = sum(1 for hub in all_hubs if hub.sync_status in ['never_synced', 'error'])

    # Build hub list
    hubs = []
    for hub in all_hubs:
        hubs.append(FleetStatusHub(
            hub_id=str(hub.id),
            hostname=hub.hostname,
            hub_type=hub.hub_type,
            status=hub.status,
            deployed_stack=hub.deployed_stack,
            manifest_version=hub.manifest_version,
            sync_status=hub.sync_status,
            last_sync=hub.last_sync.isoformat() if hub.last_sync else None,
            last_heartbeat=hub.last_heartbeat.isoformat() if hub.last_heartbeat else None,
            cpu_usage=hub.cpu_usage,
            memory_usage=hub.memory_usage,
            device_count=hub.device_count or 0
        ))

    return FleetStatusResponse(
        total_hubs=total_hubs,
        tier_2_hubs=tier_2_hubs,
        tier_3_hubs=tier_3_hubs,
        online_hubs=online_hubs,
        offline_hubs=offline_hubs,
        hubs_needing_sync=hubs_needing_sync,
        hubs=hubs
    )


@router.post("/command", response_model=RemoteCommandResponse, status_code=200)
async def execute_remote_command(
    command_request: RemoteCommandRequest,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Execute remote command on selected hubs (Admin only)

    Supported commands:
    - restart_service: Restart a specific service (requires params.service_name)
    - update_manifest: Update to latest manifest version
    - sync_devices_now: Trigger immediate device sync
    - restart_hub: Restart the entire hub
    - collect_logs: Collect logs from hub

    Returns:
        RemoteCommandResponse with results per hub
    """
    # TODO: Implement remote command execution
    # This would involve making API calls to each hub's management API

    # Validate command
    valid_commands = ['restart_service', 'update_manifest', 'sync_devices_now', 'restart_hub', 'collect_logs']
    if command_request.command not in valid_commands:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid command. Must be one of: {', '.join(valid_commands)}"
        )

    # Placeholder implementation
    results = []
    for hub_id in command_request.hub_ids:
        # In production, this would make an API call to the hub
        results.append({
            "hub_id": str(hub_id),
            "status": "success",
            "message": f"[PLACEHOLDER] Command '{command_request.command}' executed successfully"
        })

    return RemoteCommandResponse(
        total_hubs=len(command_request.hub_ids),
        successful=len(command_request.hub_ids),
        failed=0,
        results=results
    )


@router.post("/rollback", response_model=DeploymentResponse, status_code=200)
async def rollback_hub(
    rollback_request: RollbackRequest,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Rollback a hub to a previous manifest version (Admin only)

    Process:
    1. Get hub's previous manifest version
    2. Deploy previous version to hub
    3. Monitor rollback status
    4. Record rollback as new deployment

    Returns:
        DeploymentResponse with rollback results
    """
    try:
        result = await fleet_deployment_service.rollback_deployment(
            hub_id=str(rollback_request.hub_id),
            previous_manifest_version=rollback_request.previous_manifest_version,
            initiated_by=auth_user.username
        )

        return DeploymentResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")
