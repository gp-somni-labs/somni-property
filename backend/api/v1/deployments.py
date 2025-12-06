"""
Deployments API - GitOps Orchestration

Handles GitOps-based deployments to client hubs:
- Deploy service packages via git commits
- Monitor deployment status via ArgoCD
- Rollback deployments
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
import logging

from db.database import get_db
from db.models import PropertyEdgeNode, ServicePackage
from core.auth import get_auth_user, require_admin, AuthUser
from services.gitops_orchestration_service import GitOpsOrchestrationService
from core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class DeploymentRequest(BaseModel):
    """Request to deploy to a hub"""
    hub_id: UUID
    components: List[Dict[str, str]]  # [{"name": "ha", "version": "2025.11.2"}]
    commit_message: Optional[str] = None


class DeploymentResponse(BaseModel):
    """Deployment result"""
    deployment_id: str
    hub_id: UUID
    status: str
    commit_sha: Optional[str] = None
    manifests_committed: List[str]
    started_at: datetime
    completed_at: Optional[datetime] = None
    errors: List[str] = []
    logs: List[str] = []


class DeploymentStatus(BaseModel):
    """Deployment status check"""
    hub_id: UUID
    hub_name: str
    deployment_status: str
    sync_status: Optional[str] = None
    health_status: Optional[str] = None
    last_sync: Optional[datetime] = None
    components: List[Dict[str, Any]] = []


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    deployment: DeploymentRequest,
    auth_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Deploy components to a hub via GitOps

    Creates a git commit with component manifests and pushes to the hub's
    GitOps repository. ArgoCD will automatically sync the changes.

    **Requires admin role**
    """
    # Get hub
    hub_result = await db.execute(
        select(PropertyEdgeNode).where(PropertyEdgeNode.id == deployment.hub_id)
    )
    hub = hub_result.scalar_one_or_none()

    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hub {deployment.hub_id} not found"
        )

    # Validate components
    if not deployment.components:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one component is required"
        )

    try:
        gitops_service = GitOpsOrchestrationService()

        # Build manifests dict (simplified for now)
        manifests = {}
        for component in deployment.components:
            name = component.get("name")
            version = component.get("version")

            if not name or not version:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each component must have 'name' and 'version'"
                )

            # Generate manifest content (placeholder)
            manifest_content = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: {name}-{version.replace('.', '-')}
  namespace: default
data:
  version: "{version}"
  component: "{name}"
"""
            manifests[f"{name}.yaml"] = manifest_content

        # Determine commit message
        commit_msg = deployment.commit_message or f"Deploy {len(deployment.components)} components to {hub.hostname}"

        # TODO: Get actual client repo URL from hub or config
        # For now, use placeholder
        client_repo_url = hub.manifest_repo_url or "https://github.com/gp-somni-labs/client-gitops-repo"
        client_repo_branch = "main"
        service_package_name = "custom-deployment"

        logger.info(f"Deploying to hub {hub.id}: {deployment.components}")

        # Execute GitOps deployment
        result = gitops_service.deploy_stack_to_client(
            client_repo_url=client_repo_url,
            client_repo_branch=client_repo_branch,
            service_package_name=service_package_name,
            manifests=manifests,
            commit_message=commit_msg
        )

        # Update hub deployment status
        hub.deployment_status = result.get("status")
        hub.deployment_completed_at = datetime.utcnow() if result.get("status") == "success" else None
        hub.deployment_manifest_version = result.get("commit_sha")

        await db.commit()

        return DeploymentResponse(
            deployment_id=str(hub.id),
            hub_id=hub.id,
            status=result.get("status", "unknown"),
            commit_sha=result.get("commit_sha"),
            manifests_committed=result.get("manifests_committed", []),
            started_at=datetime.fromisoformat(result.get("started_at")),
            completed_at=datetime.fromisoformat(result["completed_at"]) if result.get("completed_at") else None,
            errors=result.get("errors", []),
            logs=result.get("logs", [])
        )

    except Exception as e:
        logger.error(f"Deployment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}"
        )


@router.get("/status", response_model=List[DeploymentStatus])
async def get_deployment_status(
    hub_id: Optional[UUID] = Query(None, description="Filter by hub ID"),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get deployment status for hubs

    Returns current deployment and sync status from ArgoCD.
    Can be filtered by hub_id.
    """
    from sqlalchemy import select

    # Build query
    query = select(PropertyEdgeNode)
    if hub_id:
        query = query.where(PropertyEdgeNode.id == hub_id)

    result = await db.execute(query)
    hubs = result.scalars().all()

    statuses = []
    for hub in hubs:
        status_obj = DeploymentStatus(
            hub_id=hub.id,
            hub_name=hub.hostname,
            deployment_status=hub.deployment_status or "unknown",
            sync_status=hub.sync_status,
            health_status=hub.status,
            last_sync=hub.last_sync,
            components=[]  # TODO: Parse from deployed_components JSONB
        )
        statuses.append(status_obj)

    return statuses


@router.get("/health")
async def deployments_health():
    """Health check for deployments service"""
    return {
        "status": "healthy",
        "service": "deployments",
        "gitops_configured": bool(settings.GIT_USER_NAME),
        "timestamp": datetime.utcnow()
    }
