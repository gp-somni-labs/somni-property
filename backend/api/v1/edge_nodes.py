"""
Somni Property Manager - Property Edge Nodes API
CRUD endpoints for managing property edge nodes (Home Assistant instances)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta

from db.database import get_db
from db.models import PropertyEdgeNode as EdgeNodeModel
from api.schemas import (
    PropertyEdgeNode,
    PropertyEdgeNodeCreate,
    PropertyEdgeNodeUpdate,
    PropertyEdgeNodeListResponse
)
from core.auth import AuthUser, require_admin, require_manager

router = APIRouter()


@router.post("", response_model=PropertyEdgeNode, status_code=201)
async def create_edge_node(
    node_data: PropertyEdgeNodeCreate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Create a new property edge node (Admin only)

    Edge nodes are Home Assistant instances (one per property) that:
    - Manage local smart home devices
    - Report to SomniProperty via MQTT
    - Run automations locally
    - Provide real-time IoT monitoring
    """
    # Check if property already has an edge node (one-to-one relationship)
    existing_query = select(EdgeNodeModel).where(EdgeNodeModel.property_id == node_data.property_id)
    existing_result = await db.execute(existing_query)
    existing_node = existing_result.scalar_one_or_none()

    if existing_node:
        raise HTTPException(
            status_code=400,
            detail=f"Property {node_data.property_id} already has an edge node"
        )

    node_obj = EdgeNodeModel(**node_data.model_dump())
    db.add(node_obj)
    await db.commit()
    await db.refresh(node_obj)
    return node_obj


@router.get("", response_model=PropertyEdgeNodeListResponse)
async def list_edge_nodes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    property_id: Optional[UUID] = Query(None, description="Filter by property ID"),
    node_type: Optional[str] = Query(None, description="Filter by node type (home_assistant/mqtt/custom)"),
    hub_type: Optional[str] = Query(None, description="Filter by hub type (tier_0/tier_1/tier_2/tier_3_residential/tier_2_property_hub)"),
    status: Optional[str] = Query(None, description="Filter by status (online/offline/error/maintenance)"),
    parent_hub_id: Optional[UUID] = Query(None, description="Filter by parent hub ID"),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all property edge nodes with pagination and filtering (Admin/Manager only)

    Query parameters:
    - property_id: Get edge node for specific property
    - node_type: Filter by node type
    - hub_type: Filter by hub type (PROPERTY_HUB or RESIDENTIAL)
    - status: Filter by connection status
    - parent_hub_id: Filter by parent hub (get children of specific hub)
    - skip: Pagination offset
    - limit: Maximum number of items to return
    """
    # Build query with optional filters
    query_base = select(EdgeNodeModel)

    if property_id:
        query_base = query_base.where(EdgeNodeModel.property_id == property_id)
    if node_type:
        query_base = query_base.where(EdgeNodeModel.node_type == node_type)
    if hub_type:
        query_base = query_base.where(EdgeNodeModel.hub_type == hub_type)
    if status:
        query_base = query_base.where(EdgeNodeModel.status == status)
    if parent_hub_id:
        query_base = query_base.where(EdgeNodeModel.parent_hub_id == parent_hub_id)

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get edge nodes
    query = query_base.offset(skip).limit(limit).order_by(EdgeNodeModel.created_at.desc())
    result = await db.execute(query)
    nodes = result.scalars().all()

    return PropertyEdgeNodeListResponse(
        items=nodes,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/online", response_model=PropertyEdgeNodeListResponse)
async def list_online_edge_nodes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all online edge nodes (Admin/Manager only)

    Returns nodes with status='online' ordered by last heartbeat.
    """
    query_base = select(EdgeNodeModel).where(EdgeNodeModel.status == "online")

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get nodes
    query = query_base.offset(skip).limit(limit).order_by(EdgeNodeModel.last_heartbeat.desc())
    result = await db.execute(query)
    nodes = result.scalars().all()

    return PropertyEdgeNodeListResponse(
        items=nodes,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/offline", response_model=PropertyEdgeNodeListResponse)
async def list_offline_edge_nodes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    List all offline edge nodes (Admin/Manager only)

    Returns nodes with status='offline' or 'error' ordered by last heartbeat.
    Useful for monitoring dashboards.
    """
    query_base = select(EdgeNodeModel).where(
        (EdgeNodeModel.status == "offline") |
        (EdgeNodeModel.status == "error")
    )

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get nodes
    query = query_base.offset(skip).limit(limit).order_by(EdgeNodeModel.last_heartbeat.asc())
    result = await db.execute(query)
    nodes = result.scalars().all()

    return PropertyEdgeNodeListResponse(
        items=nodes,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{node_id}", response_model=PropertyEdgeNode)
async def get_edge_node(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Get a specific property edge node by ID (Admin/Manager only)"""
    query = select(EdgeNodeModel).where(EdgeNodeModel.id == node_id)
    result = await db.execute(query)
    node_obj = result.scalar_one_or_none()

    if not node_obj:
        raise HTTPException(status_code=404, detail="Edge node not found")

    return node_obj


@router.get("/{node_id}/children", response_model=PropertyEdgeNodeListResponse)
async def get_edge_node_children(
    node_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get all child edge nodes for a property hub (Admin/Manager only)

    Returns all residential hubs that have this node as their parent_hub_id.
    Useful for showing property hub -> unit hierarchy in multi-unit buildings.
    """
    # Verify parent hub exists
    parent_query = select(EdgeNodeModel).where(EdgeNodeModel.id == node_id)
    parent_result = await db.execute(parent_query)
    parent_node = parent_result.scalar_one_or_none()

    if not parent_node:
        raise HTTPException(status_code=404, detail="Parent hub not found")

    # Get children
    query_base = select(EdgeNodeModel).where(EdgeNodeModel.parent_hub_id == node_id)

    # Get total count
    count_query = select(func.count()).select_from(query_base.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get child nodes
    query = query_base.offset(skip).limit(limit).order_by(EdgeNodeModel.created_at.asc())
    result = await db.execute(query)
    children = result.scalars().all()

    return PropertyEdgeNodeListResponse(
        items=children,
        total=total,
        skip=skip,
        limit=limit
    )


@router.put("/{node_id}", response_model=PropertyEdgeNode)
async def update_edge_node(
    node_id: UUID,
    node_data: PropertyEdgeNodeUpdate,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Update a property edge node (Admin only)

    Use this to:
    - Update connection details (hostname, IP, API token)
    - Change MQTT configuration
    - Update firmware version
    - Modify resource usage metrics
    """
    query = select(EdgeNodeModel).where(EdgeNodeModel.id == node_id)
    result = await db.execute(query)
    node_obj = result.scalar_one_or_none()

    if not node_obj:
        raise HTTPException(status_code=404, detail="Edge node not found")

    # Update only provided fields
    update_data = node_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(node_obj, key, value)

    await db.commit()
    await db.refresh(node_obj)
    return node_obj


@router.post("/{node_id}/heartbeat", response_model=PropertyEdgeNode)
async def update_node_heartbeat(
    node_id: UUID,
    device_count: Optional[int] = Query(None, description="Current device count"),
    automation_count: Optional[int] = Query(None, description="Current automation count"),
    uptime_hours: Optional[int] = Query(None, description="Uptime in hours"),
    resource_usage: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Update edge node heartbeat (Admin/Manager only)

    Called by edge node or MQTT service to report health.
    Updates last_heartbeat, sets status to 'online', and optionally updates metrics.
    """
    query = select(EdgeNodeModel).where(EdgeNodeModel.id == node_id)
    result = await db.execute(query)
    node_obj = result.scalar_one_or_none()

    if not node_obj:
        raise HTTPException(status_code=404, detail="Edge node not found")

    node_obj.last_heartbeat = datetime.utcnow()
    node_obj.status = "online"

    if device_count is not None:
        node_obj.device_count = device_count
    if automation_count is not None:
        node_obj.automation_count = automation_count
    if uptime_hours is not None:
        node_obj.uptime_hours = uptime_hours
    if resource_usage is not None:
        node_obj.resource_usage = resource_usage

    await db.commit()
    await db.refresh(node_obj)
    return node_obj


@router.post("/{node_id}/sync", response_model=PropertyEdgeNode)
async def sync_edge_node(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Trigger manual sync of edge node data (Admin only)

    Updates last_sync timestamp and triggers data synchronization from edge node.
    """
    query = select(EdgeNodeModel).where(EdgeNodeModel.id == node_id)
    result = await db.execute(query)
    node_obj = result.scalar_one_or_none()

    if not node_obj:
        raise HTTPException(status_code=404, detail="Edge node not found")

    if node_obj.status != "online":
        raise HTTPException(status_code=400, detail="Cannot sync offline node")

    node_obj.last_sync = datetime.utcnow()

    await db.commit()
    await db.refresh(node_obj)

    # TODO: Trigger actual sync with Home Assistant API
    # This will be implemented in the HA integration service

    return node_obj


@router.post("/{node_id}/mark-offline", response_model=PropertyEdgeNode)
async def mark_node_offline(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Mark edge node as offline (Admin only)

    Sets status='offline'. Used for manual maintenance or troubleshooting.
    """
    query = select(EdgeNodeModel).where(EdgeNodeModel.id == node_id)
    result = await db.execute(query)
    node_obj = result.scalar_one_or_none()

    if not node_obj:
        raise HTTPException(status_code=404, detail="Edge node not found")

    node_obj.status = "offline"

    await db.commit()
    await db.refresh(node_obj)
    return node_obj


@router.post("/{node_id}/mark-maintenance", response_model=PropertyEdgeNode)
async def mark_node_maintenance(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Mark edge node as under maintenance (Admin only)

    Sets status='maintenance'. Suppresses offline alerts.
    """
    query = select(EdgeNodeModel).where(EdgeNodeModel.id == node_id)
    result = await db.execute(query)
    node_obj = result.scalar_one_or_none()

    if not node_obj:
        raise HTTPException(status_code=404, detail="Edge node not found")

    node_obj.status = "maintenance"

    await db.commit()
    await db.refresh(node_obj)
    return node_obj


@router.delete("/{node_id}", status_code=204)
async def delete_edge_node(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Delete a property edge node (Admin only)

    WARNING: This will also unlink all smart devices from this node (SET NULL).
    Consider marking as offline/maintenance instead.
    """
    query = select(EdgeNodeModel).where(EdgeNodeModel.id == node_id)
    result = await db.execute(query)
    node_obj = result.scalar_one_or_none()

    if not node_obj:
        raise HTTPException(status_code=404, detail="Edge node not found")

    await db.delete(node_obj)
    await db.commit()
    return None


@router.post("/{node_id}/deploy", response_model=dict)
async def deploy_edge_node(
    node_id: UUID,
    deployment_config: dict,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Trigger deployment for a registered hub (Admin only)

    Deploys appropriate stack based on hub_type:
    - Tier 2/3: Deploy k3s cluster with Home Assistant, EMQX, monitoring
    - Tier 0: Deploy SomniProperty integration to existing HA instance

    Request body examples:

    Tier 2/3 (k3s deployment):
    {
        "ssh_host": "192.168.1.100",
        "ssh_port": 22,
        "ssh_user": "admin",
        "ssh_key": "-----BEGIN PRIVATE KEY-----\\n..."
    }

    Tier 0 (HA integration):
    {
        "ha_url": "http://192.168.1.50:8123",
        "ha_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    """
    from services.deployment_orchestrator import DeploymentOrchestrator

    # Get edge node
    query = select(EdgeNodeModel).where(EdgeNodeModel.id == node_id)
    result = await db.execute(query)
    node_obj = result.scalar_one_or_none()

    if not node_obj:
        raise HTTPException(status_code=404, detail="Edge node not found")

    # Check if already deployed
    if node_obj.deployment_status == 'deployed':
        raise HTTPException(
            status_code=400,
            detail="Hub is already deployed. Use redeploy endpoint to redeploy."
        )

    # Check if deployment is in progress
    if node_obj.deployment_status == 'in_progress':
        raise HTTPException(
            status_code=400,
            detail="Deployment is already in progress"
        )

    # Trigger deployment in background
    orchestrator = DeploymentOrchestrator(db)

    # Start deployment asynchronously (don't await - run in background)
    import asyncio
    asyncio.create_task(orchestrator.deploy_hub(node_obj, deployment_config))

    # Return immediately with deployment started status
    return {
        "deployment_id": str(node_id),
        "status": "in_progress",
        "message": "Deployment started in background",
        "check_status_url": f"/api/v1/edge-nodes/{node_id}/deployment-status"
    }


@router.get("/{node_id}/deployment-status", response_model=dict)
async def get_deployment_status(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """
    Get current deployment status for a hub (Admin/Manager only)

    Returns deployment progress, current step, logs, and errors
    """
    from services.deployment_orchestrator import DeploymentOrchestrator

    orchestrator = DeploymentOrchestrator(db)

    try:
        status = await orchestrator.get_deployment_status(node_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
