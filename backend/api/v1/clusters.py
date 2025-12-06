"""
Property Mode Cluster Management API
Real K8s cluster management for multi-property deployments
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import uuid
import logging

from db.database import get_db
from core.auth import get_auth_user, require_admin, AuthUser
from core.config import settings
from core.exceptions import KubernetesError, ServiceUnavailableError
from services.k8s_cluster_service import (
    get_k8s_service, K8sClusterService,
    NodeInfo, DeploymentInfo, PodInfo, ServiceInfo, IngressInfo,
    ArgoCDApp, ClusterResources
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ClusterOverview(BaseModel):
    """Cluster overview summary."""
    id: str
    name: str
    type: str  # master, property, edge
    description: Optional[str] = None
    endpoint: Optional[str] = None
    status: str  # healthy, degraded, critical, offline
    version: Optional[str] = None
    nodes: int = 0
    ready_nodes: int = 0
    namespaces: int = 0
    deployments: int = 0
    pods_running: int = 0
    pods_total: int = 0
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    storage_usage_percent: Optional[float] = None
    last_heartbeat: Optional[datetime] = None
    created_at: Optional[datetime] = None


class NodeResponse(BaseModel):
    """Node response model."""
    id: str
    name: str
    cluster_name: str
    role: str
    status: str
    cpu_cores: Optional[int] = None
    memory_gb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    pods_running: Optional[int] = None
    pods_capacity: Optional[int] = None
    ip_address: Optional[str] = None
    os: Optional[str] = None
    kernel: Optional[str] = None
    container_runtime: Optional[str] = None
    kubelet_version: Optional[str] = None
    labels: Dict[str, str] = {}
    last_heartbeat: Optional[datetime] = None


class DeploymentResponse(BaseModel):
    """Deployment response model."""
    id: str
    name: str
    namespace: str
    cluster_name: str
    replicas_desired: int
    replicas_ready: int
    replicas_available: int
    status: str
    image: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ArgoCDAppResponse(BaseModel):
    """ArgoCD application response model."""
    id: str
    name: str
    namespace: str
    project: str
    sync_status: str
    health_status: str
    repo_url: Optional[str] = None
    path: Optional[str] = None
    target_revision: str
    auto_sync: bool
    last_sync: Optional[datetime] = None


class ResourcesSummary(BaseModel):
    """Cluster resources summary."""
    total_clusters: int = 1
    total_nodes: int
    ready_nodes: int
    total_pods: int
    running_pods: int
    cpu: Dict[str, Any]
    memory: Dict[str, Any]
    storage: Dict[str, Any]
    health_summary: Dict[str, int]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_k8s_service() -> K8sClusterService:
    """Get K8s service instance."""
    return get_k8s_service()


def _node_to_response(node: NodeInfo, cluster_name: str = "somni-cluster") -> NodeResponse:
    """Convert NodeInfo to NodeResponse."""
    return NodeResponse(
        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, node.name)),
        name=node.name,
        cluster_name=cluster_name,
        role=node.role,
        status=node.status,
        cpu_cores=node.cpu_cores,
        memory_gb=node.memory_gb,
        cpu_usage_percent=node.cpu_usage_percent,
        memory_usage_percent=node.memory_usage_percent,
        disk_usage_percent=node.disk_usage_percent,
        pods_running=node.pods_running,
        pods_capacity=node.pods_capacity,
        ip_address=node.ip_address,
        os=node.os,
        kernel=node.kernel,
        container_runtime=node.container_runtime,
        kubelet_version=node.kubelet_version,
        labels=node.labels,
        last_heartbeat=node.last_heartbeat
    )


def _deployment_to_response(dep: DeploymentInfo, cluster_name: str = "somni-cluster") -> DeploymentResponse:
    """Convert DeploymentInfo to DeploymentResponse."""
    return DeploymentResponse(
        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{dep.namespace}/{dep.name}")),
        name=dep.name,
        namespace=dep.namespace,
        cluster_name=cluster_name,
        replicas_desired=dep.replicas_desired,
        replicas_ready=dep.replicas_ready,
        replicas_available=dep.replicas_available,
        status=dep.status,
        image=dep.image,
        created_at=dep.created_at,
        updated_at=dep.updated_at
    )


def _argocd_to_response(app: ArgoCDApp) -> ArgoCDAppResponse:
    """Convert ArgoCDApp to ArgoCDAppResponse."""
    return ArgoCDAppResponse(
        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, app.name)),
        name=app.name,
        namespace=app.namespace,
        project=app.project,
        sync_status=app.sync_status,
        health_status=app.health_status,
        repo_url=app.repo_url,
        path=app.path,
        target_revision=app.target_revision,
        auto_sync=app.auto_sync,
        last_sync=app.last_sync
    )


# ============================================================================
# CLUSTER OVERVIEW
# ============================================================================

@router.get("/clusters")
async def list_clusters(
    skip: int = 0,
    limit: int = Query(default=50, le=500),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """List all K8s clusters in the property portfolio."""
    k8s = _get_k8s_service()

    try:
        # Get cluster resources
        resources = await k8s.get_cluster_resources()
        nodes = await k8s.get_nodes()
        deployments = await k8s.get_deployments()
        pods = await k8s.get_pods()

        # Determine cluster health
        if resources.ready_nodes == resources.total_nodes and resources.ready_nodes > 0:
            status = "healthy"
        elif resources.ready_nodes > 0:
            status = "degraded"
        else:
            status = "critical"

        # Get kubelet version from first node
        version = nodes[0].kubelet_version if nodes else "unknown"

        # Get unique namespaces
        namespaces = len(set(d.namespace for d in deployments))

        cluster = ClusterOverview(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, "somni-cluster")),
            name="somni-cluster",
            type="master",
            description="SomniCluster - K3s Master Cluster",
            endpoint=f"https://{settings.K8S_KUBECONFIG_PATH or '192.168.1.246'}:6443",
            status=status,
            version=version,
            nodes=resources.total_nodes,
            ready_nodes=resources.ready_nodes,
            namespaces=namespaces,
            deployments=len(deployments),
            pods_running=resources.running_pods,
            pods_total=resources.total_pods,
            cpu_usage_percent=resources.cpu_percent,
            memory_usage_percent=resources.memory_percent,
            last_heartbeat=datetime.utcnow(),
            created_at=datetime.utcnow()
        )

        return {
            "total": 1,
            "clusters": [cluster.dict()]
        }

    except KubernetesError as e:
        logger.error(f"K8s error listing clusters: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error listing clusters: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cluster information"
        )


@router.get("/clusters/{cluster_id}")
async def get_cluster_details(
    cluster_id: str,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed cluster information."""
    k8s = _get_k8s_service()

    try:
        resources = await k8s.get_cluster_resources()
        nodes = await k8s.get_nodes()
        deployments = await k8s.get_deployments()
        services = await k8s.get_services()
        ingresses = await k8s.get_ingresses()

        # Build detailed response
        return {
            "id": cluster_id,
            "name": "somni-cluster",
            "type": "master",
            "description": "SomniCluster - K3s Master Cluster",
            "endpoint": f"https://192.168.1.246:6443",
            "status": "healthy" if resources.ready_nodes == resources.total_nodes else "degraded",
            "version": nodes[0].kubelet_version if nodes else "unknown",
            "nodes": [_node_to_response(n).dict() for n in nodes],
            "namespaces": len(set(d.namespace for d in deployments)),
            "deployments": len(deployments),
            "pods_running": resources.running_pods,
            "pods_total": resources.total_pods,
            "services": len(services),
            "ingresses": len(ingresses),
            "resource_usage": {
                "cpu_cores_total": resources.cpu_total_cores,
                "cpu_cores_used": resources.cpu_used_cores,
                "cpu_percent": resources.cpu_percent,
                "memory_gb_total": resources.memory_total_gb,
                "memory_gb_used": resources.memory_used_gb,
                "memory_percent": resources.memory_percent
            },
            "created_at": datetime.utcnow().isoformat(),
            "last_heartbeat": datetime.utcnow().isoformat()
        }

    except KubernetesError as e:
        logger.error(f"K8s error getting cluster: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error getting cluster details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cluster details"
        )


# ============================================================================
# NODES
# ============================================================================

@router.get("/clusters/nodes", response_model=Dict[str, Any])
async def list_all_nodes(
    cluster_id: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """List all nodes across all clusters or specific cluster."""
    k8s = _get_k8s_service()

    try:
        nodes = await k8s.get_nodes()

        return {
            "total": len(nodes),
            "nodes": [_node_to_response(n).dict() for n in nodes[skip:skip+limit]]
        }

    except KubernetesError as e:
        logger.error(f"K8s error listing nodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error listing nodes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get nodes"
        )


@router.get("/clusters/{cluster_id}/nodes")
async def get_cluster_nodes(
    cluster_id: str,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get nodes for a specific cluster."""
    return await list_all_nodes(cluster_id=cluster_id, auth_user=auth_user, db=db)


# ============================================================================
# DEPLOYMENTS
# ============================================================================

@router.get("/clusters/deployments", response_model=Dict[str, Any])
async def list_deployments(
    cluster_id: Optional[str] = None,
    namespace: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """List all deployments across clusters."""
    k8s = _get_k8s_service()

    try:
        deployments = await k8s.get_deployments(namespace=namespace)

        return {
            "total": len(deployments),
            "deployments": [_deployment_to_response(d).dict() for d in deployments[skip:skip+limit]]
        }

    except KubernetesError as e:
        logger.error(f"K8s error listing deployments: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error listing deployments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get deployments"
        )


@router.post("/clusters/deployments/{namespace}/{deployment_name}/scale")
async def scale_deployment(
    namespace: str,
    deployment_name: str,
    replicas: int = Query(..., ge=0, le=10),
    auth_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Scale a deployment to specified replicas."""
    k8s = _get_k8s_service()

    try:
        await k8s.scale_deployment(deployment_name, namespace, replicas)
        return {
            "status": "success",
            "message": f"Deployment {namespace}/{deployment_name} scaled to {replicas} replicas",
            "deployment": deployment_name,
            "namespace": namespace,
            "replicas": replicas
        }

    except KubernetesError as e:
        logger.error(f"K8s error scaling deployment: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error scaling deployment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to scale deployment"
        )


@router.post("/clusters/deployments/{namespace}/{deployment_name}/restart")
async def restart_deployment(
    namespace: str,
    deployment_name: str,
    auth_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Restart a deployment (rolling restart)."""
    k8s = _get_k8s_service()

    try:
        await k8s.restart_deployment(deployment_name, namespace)
        return {
            "status": "success",
            "message": f"Deployment {namespace}/{deployment_name} restarting",
            "deployment": deployment_name,
            "namespace": namespace
        }

    except KubernetesError as e:
        logger.error(f"K8s error restarting deployment: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error restarting deployment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restart deployment"
        )


# ============================================================================
# ARGOCD INTEGRATION
# ============================================================================

@router.get("/clusters/argocd/applications")
async def list_argocd_apps(
    cluster_id: Optional[str] = None,
    sync_status: Optional[str] = None,
    health_status: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """List ArgoCD applications."""
    k8s = _get_k8s_service()

    try:
        apps = await k8s.get_argocd_apps()

        # Apply filters
        if sync_status:
            apps = [a for a in apps if a.sync_status.lower() == sync_status.lower()]
        if health_status:
            apps = [a for a in apps if a.health_status.lower() == health_status.lower()]

        return {
            "total": len(apps),
            "applications": [_argocd_to_response(a).dict() for a in apps[skip:skip+limit]]
        }

    except KubernetesError as e:
        logger.error(f"K8s error listing ArgoCD apps: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error listing ArgoCD apps: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ArgoCD applications"
        )


@router.post("/clusters/argocd/applications/{app_name}/sync")
async def sync_argocd_app(
    app_name: str,
    prune: bool = False,
    dry_run: bool = False,
    auth_user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Trigger ArgoCD application sync."""
    k8s = _get_k8s_service()

    try:
        result = await k8s.sync_argocd_app(app_name, prune=prune, dry_run=dry_run)
        return {
            **result,
            "operation_id": str(uuid.uuid4()),
            "started_at": datetime.utcnow().isoformat(),
            "triggered_by": auth_user.username
        }

    except ServiceUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ArgoCD API not configured. Set ARGOCD_TOKEN environment variable."
        )
    except KubernetesError as e:
        logger.error(f"K8s error syncing ArgoCD app: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error syncing ArgoCD app: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync ArgoCD application"
        )


# ============================================================================
# RESOURCES & MONITORING
# ============================================================================

@router.get("/clusters/resources", response_model=ResourcesSummary)
async def get_cluster_resources_summary(
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregated resource usage across all clusters."""
    k8s = _get_k8s_service()

    try:
        resources = await k8s.get_cluster_resources()
        nodes = await k8s.get_nodes()

        # Calculate health summary
        healthy = len([n for n in nodes if n.status == "Ready"])
        degraded = len([n for n in nodes if n.status != "Ready" and n.status != "Unknown"])
        offline = len([n for n in nodes if n.status == "Unknown"])

        return ResourcesSummary(
            total_clusters=1,
            total_nodes=resources.total_nodes,
            ready_nodes=resources.ready_nodes,
            total_pods=resources.total_pods,
            running_pods=resources.running_pods,
            cpu={
                "total_cores": resources.cpu_total_cores,
                "used_cores": resources.cpu_used_cores,
                "percent_used": resources.cpu_percent
            },
            memory={
                "total_gb": resources.memory_total_gb,
                "used_gb": resources.memory_used_gb,
                "percent_used": resources.memory_percent
            },
            storage={
                "total_gb": resources.storage_total_gb,
                "used_gb": resources.storage_used_gb,
                "percent_used": resources.storage_percent
            },
            health_summary={
                "healthy": healthy,
                "degraded": degraded,
                "critical": 0,
                "offline": offline
            }
        )

    except KubernetesError as e:
        logger.error(f"K8s error getting resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error getting cluster resources: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cluster resources"
        )


@router.get("/clusters/{cluster_id}/resources")
async def get_cluster_resources(
    cluster_id: str,
    auth_user: AuthUser = Depends(get_auth_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed resource usage for specific cluster."""
    k8s = _get_k8s_service()

    try:
        resources = await k8s.get_cluster_resources()
        pods = await k8s.get_pods()

        # Count pod statuses
        pending = len([p for p in pods if p.status == "Pending"])
        failed = len([p for p in pods if p.status == "Failed"])

        return {
            "cluster_id": cluster_id,
            "cluster_name": "somni-cluster",
            "timestamp": datetime.utcnow().isoformat(),
            "nodes": resources.total_nodes,
            "pods_running": resources.running_pods,
            "pods_pending": pending,
            "pods_failed": failed,
            "cpu": {
                "total_cores": resources.cpu_total_cores,
                "used_cores": resources.cpu_used_cores,
                "percent_used": resources.cpu_percent
            },
            "memory": {
                "total_gb": resources.memory_total_gb,
                "used_gb": resources.memory_used_gb,
                "percent_used": resources.memory_percent
            },
            "storage": {
                "total_gb": resources.storage_total_gb,
                "used_gb": resources.storage_used_gb,
                "percent_used": resources.storage_percent
            }
        }

    except KubernetesError as e:
        logger.error(f"K8s error getting cluster resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e.message)
        )
    except Exception as e:
        logger.error(f"Error getting cluster resources: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cluster resources"
        )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/clusters/health")
async def clusters_health(
    auth_user: AuthUser = Depends(get_auth_user)
):
    """Health check for cluster management service."""
    k8s = _get_k8s_service()

    try:
        health = await k8s.health_check()
        return {
            **health,
            "timestamp": datetime.utcnow().isoformat(),
            "argocd_configured": bool(settings.ARGOCD_TOKEN)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "kubernetes",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
