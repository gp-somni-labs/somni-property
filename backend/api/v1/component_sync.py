"""
Somni Property Manager - Component Sync API
API endpoints for syncing Somni components and add-ons to customer infrastructure.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

from db.database import get_db
from db.models import ComponentSync, PropertyEdgeNode
from services.git_service import GitService
from services.component_sync_service import ComponentSyncService
from services.gitops_orchestration_service import GitOpsOrchestrationService
from core.auth import AuthUser, require_admin
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ComponentInfo(BaseModel):
    """Component information"""
    name: str
    path: str  # Changed from 'domain' to match frontend expectations
    type: str = "component"  # Added to match frontend expectations
    version: Optional[str] = None  # Made optional to match frontend
    description: Optional[str] = None  # Made optional to match frontend
    manifest: Optional[dict] = None  # Added to match frontend expectations


class AddonInfo(BaseModel):
    """Add-on information"""
    name: str
    path: str
    type: str = "addon"  # Added to match frontend expectations
    version: Optional[str] = None
    description: Optional[str] = None
    manifest: Optional[dict] = None  # Added to match frontend expectations


class ConfigInfo(BaseModel):
    """Configuration information"""
    name: str
    path: str
    type: str = "config"  # Added to match frontend expectations
    version: Optional[str] = None  # Added to match frontend expectations
    description: Optional[str] = None
    manifest: Optional[dict] = None  # Added to match frontend expectations


class SyncRequest(BaseModel):
    """Request to sync components to a hub"""
    hub_id: Optional[UUID] = Field(None, description="PropertyEdgeNode ID (for tracked hubs)")
    hub_host: str = Field(..., description="SSH host or Tailscale hostname")
    hub_type: str = Field(..., pattern="^(tier_0_standalone|tier_2_property|tier_3_residential)$")
    component_names: Optional[List[str]] = Field(None, description="Component names to sync (None = all)")
    addon_names: Optional[List[str]] = Field(None, description="Add-on names to sync")
    restart_ha: bool = Field(True, description="Restart Home Assistant after sync")
    custom_components_path: str = Field("/config/custom_components", description="Remote custom_components path")
    addons_path: str = Field("/addons", description="Remote addons path")


class GitOpsSyncRequest(BaseModel):
    """Request to sync via GitOps"""
    hub_id: Optional[UUID] = Field(None, description="PropertyEdgeNode ID (for tracked hubs)")
    repo_url: str = Field(..., description="Client's GitOps repository URL")
    repo_branch: str = Field("main", description="Git branch to commit to")
    component_names: List[str] = Field(..., description="Component names to deploy")


class RefreshReposRequest(BaseModel):
    """Request to refresh Git repositories"""
    repos: Optional[List[str]] = Field(None, description="Specific repos to refresh (None = all)")


class SyncHistoryResponse(BaseModel):
    """Component sync history response"""
    id: UUID
    target_hub_host: str
    target_hub_type: str
    sync_method: str
    sync_status: str
    components_requested: Optional[List[str]] = None
    components_synced: Optional[List[str]] = None
    addons_requested: Optional[List[str]] = None
    addons_synced: Optional[List[str]] = None
    sync_started_at: datetime
    sync_completed_at: Optional[datetime] = None
    error_messages: Optional[List[str]] = None
    initiated_by: Optional[str] = None

    class Config:
        from_attributes = True


class SyncHistoryListResponse(BaseModel):
    """Paginated sync history list"""
    items: List[SyncHistoryResponse]
    total: int
    skip: int
    limit: int


class InstalledComponentsUpdate(BaseModel):
    """Update installed Somni components"""
    installed_somni_components: dict = Field(
        ...,
        description="Dictionary of component names to installation status",
        example={
            "somni_property_sync": True,
            "somni_lights": True,
            "somni_occupancy": False,
            "somni_access": True
        }
    )


class InstalledComponentsResponse(BaseModel):
    """Response showing installed components"""
    hub_id: UUID
    hub_name: str
    installed_somni_components: dict
    last_component_sync_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ComponentCatalogItem(BaseModel):
    """Catalog item for available Somni components"""
    component_key: str
    display_name: str
    status: str  # production, beta, planned
    repository: str
    description: str
    category: str
    tier: int  # 1 = essential, 2 = recommended, 3 = optional
    version: Optional[str] = None
    min_ha_version: Optional[str] = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/components", response_model=List[ComponentInfo])
async def list_components(
    auth_user: AuthUser = Depends(require_admin)
):
    """
    List all available Somni components.
    Admin only.

    Returns hardcoded component catalog until Git repositories are configured.
    """
    # Return hardcoded catalog of Somni components
    # This matches the frontend ComponentInfo TypeScript interface
    components = [
        ComponentInfo(
            name="somni_property_sync",
            path="/custom_components/somni_property_sync",
            type="component",
            version="2.1.0",
            description="Sync Home Assistant devices/automations with SomniProperty platform"
        ),
        ComponentInfo(
            name="somni_lights",
            path="/custom_components/somni_lights",
            type="component",
            version="1.8.0",
            description="Advanced lighting control with occupancy sensing and circadian rhythm"
        ),
        ComponentInfo(
            name="somni_occupancy",
            path="/custom_components/somni_occupancy",
            type="component",
            version="1.5.2",
            description="Multi-sensor occupancy detection with ML-based presence prediction"
        ),
        ComponentInfo(
            name="somni_access",
            path="/custom_components/somni_access",
            type="component",
            version="2.0.0",
            description="Smart lock and access control management"
        ),
        ComponentInfo(
            name="somni_security",
            path="/custom_components/somni_security",
            type="component",
            version="1.9.5",
            description="Comprehensive security system integration"
        ),
        ComponentInfo(
            name="somni_climate",
            path="/custom_components/somni_climate",
            type="component",
            version="1.7.0",
            description="Intelligent HVAC control with energy optimization"
        ),
        ComponentInfo(
            name="somni_maintenance",
            path="/custom_components/somni_maintenance",
            type="component",
            version="1.4.0",
            description="Predictive maintenance and device health monitoring"
        ),
        ComponentInfo(
            name="somni_alerts",
            path="/custom_components/somni_alerts",
            type="component",
            version="1.6.1",
            description="Advanced alerting and notification system"
        ),
        ComponentInfo(
            name="somni_energy",
            path="/custom_components/somni_energy",
            type="component",
            version="0.9.0",
            description="Real-time energy monitoring and cost optimization (Beta)"
        ),
        ComponentInfo(
            name="somni_water",
            path="/custom_components/somni_water",
            type="component",
            version="0.8.5",
            description="Water leak detection and consumption monitoring (Beta)"
        ),
        ComponentInfo(
            name="somni_voice",
            path="/custom_components/somni_voice",
            type="component",
            version="1.3.0",
            description="Wyoming Protocol voice assistant integration"
        ),
        ComponentInfo(
            name="somni_lease_automation",
            path="/custom_components/somni_lease_automation",
            type="component",
            version="0.7.0",
            description="Automate smart home setup based on lease lifecycle (Beta)"
        ),
    ]
    return components


@router.get("/addons", response_model=List[AddonInfo])
async def list_addons(
    auth_user: AuthUser = Depends(require_admin)
):
    """
    List all available Home Assistant add-ons.
    Admin only.

    Returns hardcoded addon catalog until Git repositories are configured.
    """
    # Return catalog of common/useful Home Assistant add-ons
    # This matches the frontend ComponentInfo TypeScript interface
    addons = [
        AddonInfo(
            name="mosquitto",
            path="/addons/mosquitto",
            type="addon",
            version="6.4.0",
            description="MQTT broker for device communication"
        ),
        AddonInfo(
            name="zigbee2mqtt",
            path="/addons/zigbee2mqtt",
            type="addon",
            version="1.34.0",
            description="Zigbee to MQTT bridge for smart devices"
        ),
        AddonInfo(
            name="node-red",
            path="/addons/node-red",
            type="addon",
            version="16.2.1",
            description="Flow-based automation and integration platform"
        ),
        AddonInfo(
            name="vscode",
            path="/addons/vscode",
            type="addon",
            version="5.13.1",
            description="Web-based code editor for HA configuration"
        ),
        AddonInfo(
            name="file-editor",
            path="/addons/file-editor",
            type="addon",
            version="5.8.0",
            description="Simple file editor for HA configuration"
        ),
    ]
    return addons


@router.get("/configs", response_model=List[ConfigInfo])
async def list_configs(
    auth_user: AuthUser = Depends(require_admin)
):
    """
    List all available property configurations.
    Admin only.

    Returns hardcoded config templates until Git repositories are configured.
    """
    # Return catalog of common configuration templates
    # This matches the frontend ComponentInfo TypeScript interface
    configs = [
        ConfigInfo(
            name="multi_unit_property",
            path="/configs/multi_unit_property.yaml",
            type="config",
            description="Standard configuration for multi-unit residential properties"
        ),
        ConfigInfo(
            name="single_family",
            path="/configs/single_family.yaml",
            type="config",
            description="Configuration template for single-family homes"
        ),
        ConfigInfo(
            name="commercial_office",
            path="/configs/commercial_office.yaml",
            type="config",
            description="Office building automation configuration"
        ),
        ConfigInfo(
            name="vacation_rental",
            path="/configs/vacation_rental.yaml",
            type="config",
            description="Short-term rental property configuration with turnover automation"
        ),
    ]
    return configs


@router.post("/refresh-repos")
async def refresh_repos(
    request: RefreshReposRequest = RefreshReposRequest(repos=None),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Refresh Git repositories by pulling latest changes.
    Admin only.
    """
    try:
        git_service = GitService()
        results = git_service.refresh_all()
        return {
            "status": "completed",
            "results": results,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to refresh repos: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh repos: {str(e)}")


@router.post("/sync")
async def sync_components(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Sync components to a Tier 0 hub via rsync.
    Tier-aware: automatically handles Tier 0 (rsync) vs Tier 1/2 (GitOps).
    Admin only.
    """
    # Create sync record
    sync_record = ComponentSync(
        target_hub_id=request.hub_id,
        target_hub_host=request.hub_host,
        target_hub_type=request.hub_type,
        sync_method='rsync',
        sync_status='in_progress',
        components_requested=request.component_names,
        addons_requested=request.addon_names,
        initiated_by=auth_user.username if hasattr(auth_user, 'username') else 'admin',
    )

    db.add(sync_record)
    await db.flush()
    await db.refresh(sync_record)

    sync_id = sync_record.id

    # Run sync in background
    background_tasks.add_task(
        _perform_component_sync,
        sync_id=sync_id,
        hub_host=request.hub_host,
        component_names=request.component_names,
        addon_names=request.addon_names,
        custom_components_path=request.custom_components_path,
        addons_path=request.addons_path,
        restart_ha=request.restart_ha,
    )

    return {
        "status": "initiated",
        "sync_id": sync_id,
        "message": "Component sync started in background",
        "hub_host": request.hub_host,
    }


@router.post("/sync-gitops")
async def sync_components_gitops(
    request: GitOpsSyncRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Sync components via GitOps (Tier 1/2 deployments).
    Commits manifests to client's GitOps repo for FluxCD auto-deployment.
    Admin only.
    """
    # Determine hub type (default to tier_2 for GitOps)
    hub_type = "tier_2_property"
    if request.hub_id:
        # Get hub info from database
        query = select(PropertyEdgeNode).where(PropertyEdgeNode.id == request.hub_id)
        result = await db.execute(query)
        hub = result.scalar_one_or_none()
        if hub:
            hub_type = hub.hub_type

    # Create sync record
    sync_record = ComponentSync(
        target_hub_id=request.hub_id,
        target_hub_host=request.repo_url,
        target_hub_type=hub_type,
        sync_method='gitops',
        sync_status='in_progress',
        components_requested=request.component_names,
        gitops_repo_url=request.repo_url,
        gitops_branch=request.repo_branch,
        initiated_by=auth_user.username if hasattr(auth_user, 'username') else 'admin',
    )

    db.add(sync_record)
    await db.flush()
    await db.refresh(sync_record)

    sync_id = sync_record.id

    # Run GitOps sync in background
    background_tasks.add_task(
        _perform_gitops_sync,
        sync_id=sync_id,
        repo_url=request.repo_url,
        repo_branch=request.repo_branch,
        component_names=request.component_names,
    )

    return {
        "status": "initiated",
        "sync_id": sync_id,
        "message": "GitOps sync started in background",
        "repo_url": request.repo_url,
    }


@router.get("/sync-history", response_model=SyncHistoryListResponse)
async def get_sync_history(
    skip: int = 0,
    limit: int = 50,
    hub_id: Optional[UUID] = None,
    hub_type: Optional[str] = None,
    sync_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Get component sync history with optional filters.
    Admin only.
    """
    # Build query
    query = select(ComponentSync)

    # Apply filters
    if hub_id:
        query = query.where(ComponentSync.target_hub_id == hub_id)
    if hub_type:
        query = query.where(ComponentSync.target_hub_type == hub_type)
    if sync_status:
        query = query.where(ComponentSync.sync_status == sync_status)

    # Get total count
    count_query = select(func.count()).select_from(ComponentSync)
    if hub_id:
        count_query = count_query.where(ComponentSync.target_hub_id == hub_id)
    if hub_type:
        count_query = count_query.where(ComponentSync.target_hub_type == hub_type)
    if sync_status:
        count_query = count_query.where(ComponentSync.sync_status == sync_status)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get syncs
    query = query.offset(skip).limit(limit).order_by(desc(ComponentSync.sync_started_at))
    result = await db.execute(query)
    syncs = result.scalars().all()

    return SyncHistoryListResponse(
        items=[SyncHistoryResponse.model_validate(sync) for sync in syncs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/sync-history/{sync_id}")
async def get_sync_details(
    sync_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Get detailed information about a specific sync operation.
    Admin only.
    """
    query = select(ComponentSync).where(ComponentSync.id == sync_id)
    result = await db.execute(query)
    sync = result.scalar_one_or_none()

    if not sync:
        raise HTTPException(status_code=404, detail="Sync not found")

    return {
        "id": sync.id,
        "target_hub_host": sync.target_hub_host,
        "target_hub_type": sync.target_hub_type,
        "sync_method": sync.sync_method,
        "sync_status": sync.sync_status,
        "components_requested": sync.components_requested,
        "components_synced": sync.components_synced,
        "addons_requested": sync.addons_requested,
        "addons_synced": sync.addons_synced,
        "sync_logs": sync.sync_logs,
        "error_messages": sync.error_messages,
        "gitops_repo_url": sync.gitops_repo_url,
        "gitops_commit_sha": sync.gitops_commit_sha,
        "gitops_branch": sync.gitops_branch,
        "ha_restart_initiated": sync.ha_restart_initiated,
        "ha_restart_successful": sync.ha_restart_successful,
        "sync_started_at": sync.sync_started_at,
        "sync_completed_at": sync.sync_completed_at,
        "initiated_by": sync.initiated_by,
    }


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def _perform_component_sync(
    sync_id: UUID,
    hub_host: str,
    component_names: Optional[List[str]],
    addon_names: Optional[List[str]],
    custom_components_path: str,
    addons_path: str,
    restart_ha: bool,
):
    """Background task to perform component sync."""
    from db.database import get_async_session_maker
    from sqlalchemy import update

    async_session = get_async_session_maker()

    try:
        # Perform sync
        sync_service = ComponentSyncService()
        result = sync_service.sync_components_to_hub(
            hub_host=hub_host,
            component_names=component_names,
            addon_names=addon_names,
            custom_components_path=custom_components_path,
            addons_path=addons_path,
            restart_ha=restart_ha,
        )

        # Update sync record
        async with async_session() as db:
            await db.execute(
                update(ComponentSync)
                .where(ComponentSync.id == sync_id)
                .values(
                    sync_status=result["status"],
                    components_synced=result.get("components_synced", []),
                    addons_synced=result.get("addons_synced", []),
                    sync_logs="\n".join(result.get("logs", [])),
                    error_messages=result.get("errors", []),
                    sync_completed_at=datetime.utcnow(),
                    ha_restart_initiated=restart_ha and (result.get("components_synced") or result.get("addons_synced")),
                )
            )
            await db.commit()

        logger.info(f"Component sync {sync_id} completed with status: {result['status']}")

    except Exception as e:
        logger.error(f"Component sync {sync_id} failed: {e}")

        # Update sync record with error
        async with async_session() as db:
            await db.execute(
                update(ComponentSync)
                .where(ComponentSync.id == sync_id)
                .values(
                    sync_status='failed',
                    error_messages=[str(e)],
                    sync_completed_at=datetime.utcnow(),
                )
            )
            await db.commit()


async def _perform_gitops_sync(
    sync_id: UUID,
    repo_url: str,
    repo_branch: str,
    component_names: List[str],
):
    """Background task to perform GitOps sync."""
    from db.database import get_async_session_maker
    from sqlalchemy import update

    async_session = get_async_session_maker()

    try:
        # Perform GitOps sync
        gitops_service = GitOpsOrchestrationService()
        result = gitops_service.deploy_component_manifests(
            client_repo_url=repo_url,
            client_repo_branch=repo_branch,
            component_names=component_names,
        )

        # Update sync record
        async with async_session() as db:
            await db.execute(
                update(ComponentSync)
                .where(ComponentSync.id == sync_id)
                .values(
                    sync_status=result.get("status", "failed"),
                    components_synced=result.get("manifests_committed", []),
                    sync_logs="\n".join(result.get("logs", [])),
                    error_messages=result.get("errors", []),
                    gitops_commit_sha=result.get("commit_sha"),
                    sync_completed_at=datetime.utcnow(),
                )
            )
            await db.commit()

        logger.info(f"GitOps sync {sync_id} completed with status: {result.get('status')}")

    except Exception as e:
        logger.error(f"GitOps sync {sync_id} failed: {e}")

        # Update sync record with error
        async with async_session() as db:
            await db.execute(
                update(ComponentSync)
                .where(ComponentSync.id == sync_id)
                .values(
                    sync_status='failed',
                    error_messages=[str(e)],
                    sync_completed_at=datetime.utcnow(),
                )
            )
            await db.commit()


# ============================================================================
# INSTALLED COMPONENTS MANAGEMENT
# ============================================================================

@router.get("/hubs/{hub_id}/installed-components", response_model=InstalledComponentsResponse)
async def get_installed_components(
    hub_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Get list of installed Somni custom components for a specific hub.
    Returns checkbox-style status of which components are installed.

    Admin only.
    """
    try:
        # Fetch hub
        result = await db.execute(
            select(PropertyEdgeNode).where(PropertyEdgeNode.id == hub_id)
        )
        hub = result.scalar_one_or_none()

        if not hub:
            raise HTTPException(status_code=404, detail=f"Hub {hub_id} not found")

        return InstalledComponentsResponse(
            hub_id=hub.id,
            hub_name=hub.friendly_name or hub.ha_instance_url or str(hub.id),
            installed_somni_components=hub.installed_somni_components or {},
            last_component_sync_at=hub.last_component_sync_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get installed components for hub {hub_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get installed components: {str(e)}")


@router.patch("/hubs/{hub_id}/installed-components", response_model=InstalledComponentsResponse)
async def update_installed_components(
    hub_id: UUID,
    update: InstalledComponentsUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Update installed Somni components for a hub (checkbox interface).
    This triggers a component sync operation to install/uninstall components.

    The sync happens in the background via GitOps.

    Admin only.
    """
    try:
        # Fetch hub
        result = await db.execute(
            select(PropertyEdgeNode).where(PropertyEdgeNode.id == hub_id)
        )
        hub = result.scalar_one_or_none()

        if not hub:
            raise HTTPException(status_code=404, detail=f"Hub {hub_id} not found")

        # Get current state
        current_components = hub.installed_somni_components or {}
        new_components = update.installed_somni_components

        # Determine what changed
        components_to_install = [
            comp for comp, enabled in new_components.items()
            if enabled and not current_components.get(comp, False)
        ]
        components_to_remove = [
            comp for comp, enabled in current_components.items()
            if enabled and not new_components.get(comp, False)
        ]

        logger.info(f"Hub {hub_id} component changes: install={components_to_install}, remove={components_to_remove}")

        # Update database immediately
        from sqlalchemy import update
        await db.execute(
            update(PropertyEdgeNode)
            .where(PropertyEdgeNode.id == hub_id)
            .values(installed_somni_components=new_components)
        )
        await db.commit()
        await db.refresh(hub)

        # If there are changes, trigger sync in background
        if components_to_install or components_to_remove:
            # Create sync record
            sync_record = ComponentSync(
                target_hub_id=hub_id,
                target_hub_host=hub.ha_instance_url or hub.tailscale_hostname or "unknown",
                target_hub_type=hub.hub_type or "tier_2_property",
                sync_method="gitops",
                sync_status="pending",
                components_requested=components_to_install,
                initiated_by=auth_user.username
            )
            db.add(sync_record)
            await db.commit()
            await db.refresh(sync_record)

            # TODO: Trigger actual GitOps sync in background
            # This would call the GitOps orchestration service to:
            # 1. Clone client's config repo
            # 2. Update custom_components in git
            # 3. Commit and push
            # 4. Wait for ArgoCD to sync (or trigger webhook)

            logger.info(f"Created component sync {sync_record.id} for hub {hub_id}")

        return InstalledComponentsResponse(
            hub_id=hub.id,
            hub_name=hub.friendly_name or hub.ha_instance_url or str(hub.id),
            installed_somni_components=hub.installed_somni_components or {},
            last_component_sync_at=hub.last_component_sync_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update installed components for hub {hub_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update installed components: {str(e)}")


@router.get("/component-catalog", response_model=List[ComponentCatalogItem])
async def get_component_catalog(
    auth_user: AuthUser = Depends(require_admin)
):
    """
    Get catalog of available Somni custom Home Assistant components.
    Returns metadata about each component including status, category, and tier.

    Based on SOMNI_HA_COMPONENTS_CATALOG.md

    Admin only.
    """
    try:
        # Component catalog from documentation
        catalog = [
            {
                "component_key": "somni_property_sync",
                "display_name": "Somni Property Sync",
                "status": "production",
                "repository": "https://github.com/gp-somni-labs/somni_property_sync",
                "description": "Sync Home Assistant devices/automations with SomniProperty platform",
                "category": "Property Management Integration",
                "tier": 1,
                "version": "2.1.0",
                "min_ha_version": "2024.11.0"
            },
            {
                "component_key": "somni_lights",
                "display_name": "Somni Lights",
                "status": "production",
                "repository": "https://github.com/gp-somni-labs/somni_lights",
                "description": "Advanced lighting control with occupancy sensing and circadian rhythm",
                "category": "Lighting & Occupancy",
                "tier": 1,
                "version": "1.8.0",
                "min_ha_version": "2024.9.0"
            },
            {
                "component_key": "somni_occupancy",
                "display_name": "Somni Occupancy",
                "status": "production",
                "repository": "https://github.com/gp-somni-labs/somni_occupancy",
                "description": "Multi-sensor occupancy detection with ML-based presence prediction",
                "category": "Lighting & Occupancy",
                "tier": 2,
                "version": "1.5.2",
                "min_ha_version": "2024.10.0"
            },
            {
                "component_key": "somni_access",
                "display_name": "Somni Access",
                "status": "production",
                "repository": "https://github.com/gp-somni-labs/somni_access",
                "description": "Smart lock and access control management",
                "category": "Security & Access",
                "tier": 1,
                "version": "2.0.0",
                "min_ha_version": "2024.11.0"
            },
            {
                "component_key": "somni_security",
                "display_name": "Somni Security",
                "status": "production",
                "repository": "https://github.com/gp-somni-labs/somni_security",
                "description": "Comprehensive security system integration",
                "category": "Security & Access",
                "tier": 1,
                "version": "1.9.5",
                "min_ha_version": "2024.8.0"
            },
            {
                "component_key": "somni_climate",
                "display_name": "Somni Climate",
                "status": "production",
                "repository": "https://github.com/gp-somni-labs/somni_climate",
                "description": "Intelligent HVAC control with energy optimization",
                "category": "Climate & Energy",
                "tier": 2,
                "version": "1.7.0",
                "min_ha_version": "2024.9.0"
            },
            {
                "component_key": "somni_maintenance",
                "display_name": "Somni Maintenance",
                "status": "production",
                "repository": "https://github.com/gp-somni-labs/somni_maintenance",
                "description": "Predictive maintenance and device health monitoring",
                "category": "Monitoring & Maintenance",
                "tier": 2,
                "version": "1.4.0",
                "min_ha_version": "2024.10.0"
            },
            {
                "component_key": "somni_alerts",
                "display_name": "Somni Alerts",
                "status": "production",
                "repository": "https://github.com/gp-somni-labs/somni_alerts",
                "description": "Advanced alerting and notification system",
                "category": "Monitoring & Maintenance",
                "tier": 2,
                "version": "1.6.1",
                "min_ha_version": "2024.9.0"
            },
            {
                "component_key": "somni_energy",
                "display_name": "Somni Energy",
                "status": "beta",
                "repository": "https://github.com/gp-somni-labs/somni_energy",
                "description": "Real-time energy monitoring and cost optimization",
                "category": "Climate & Energy",
                "tier": 3,
                "version": "0.9.0",
                "min_ha_version": "2024.11.0"
            },
            {
                "component_key": "somni_water",
                "display_name": "Somni Water",
                "status": "beta",
                "repository": "https://github.com/gp-somni-labs/somni_water",
                "description": "Water leak detection and consumption monitoring",
                "category": "Water & Environmental",
                "tier": 3,
                "version": "0.8.5",
                "min_ha_version": "2024.10.0"
            },
            {
                "component_key": "somni_voice",
                "display_name": "Somni Voice",
                "status": "production",
                "repository": "https://github.com/gp-somni-labs/somni_voice",
                "description": "Wyoming Protocol voice assistant integration",
                "category": "Voice & AI",
                "tier": 3,
                "version": "1.3.0",
                "min_ha_version": "2024.11.0"
            },
            {
                "component_key": "somni_lease_automation",
                "display_name": "Somni Lease Automation",
                "status": "beta",
                "repository": "https://github.com/gp-somni-labs/somni_lease_automation",
                "description": "Automate smart home setup based on lease lifecycle",
                "category": "Property Management Integration",
                "tier": 3,
                "version": "0.7.0",
                "min_ha_version": "2024.10.0"
            }
        ]

        return [ComponentCatalogItem(**item) for item in catalog]

    except Exception as e:
        logger.error(f"Failed to get component catalog: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get component catalog: {str(e)}")
