"""
Kubernetes Cluster Management Service for SomniProperty

Provides real-time cluster monitoring and management:
- Node status and health
- Deployment management
- Pod monitoring
- Resource usage metrics
- ArgoCD application status

Designed for SomniCluster's enterprise-grade homelab environment.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
import httpx

from core.config import settings
from core.exceptions import KubernetesError, ServiceUnavailableError

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

class NodeInfo(BaseModel):
    """Kubernetes node information."""
    name: str
    status: str  # Ready, NotReady, Unknown
    role: str  # control-plane, worker, inference, edge
    ip_address: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_gb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    pods_running: Optional[int] = None
    pods_capacity: Optional[int] = None
    os: Optional[str] = None
    kernel: Optional[str] = None
    container_runtime: Optional[str] = None
    kubelet_version: Optional[str] = None
    labels: Dict[str, str] = {}
    conditions: List[Dict[str, Any]] = []
    last_heartbeat: Optional[datetime] = None


class DeploymentInfo(BaseModel):
    """Kubernetes deployment information."""
    name: str
    namespace: str
    replicas_desired: int
    replicas_ready: int
    replicas_available: int
    status: str  # healthy, degraded, failed
    image: Optional[str] = None
    labels: Dict[str, str] = {}
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PodInfo(BaseModel):
    """Kubernetes pod information."""
    name: str
    namespace: str
    status: str  # Running, Pending, Failed, Succeeded
    node: Optional[str] = None
    ip: Optional[str] = None
    containers: List[str] = []
    restarts: int = 0
    created_at: Optional[datetime] = None


class ServiceInfo(BaseModel):
    """Kubernetes service information."""
    name: str
    namespace: str
    type: str  # ClusterIP, NodePort, LoadBalancer
    cluster_ip: Optional[str] = None
    external_ip: Optional[str] = None
    ports: List[Dict[str, Any]] = []


class IngressInfo(BaseModel):
    """Kubernetes ingress information."""
    name: str
    namespace: str
    hosts: List[str] = []
    paths: List[str] = []
    tls: bool = False


class ArgoCDApp(BaseModel):
    """ArgoCD application information."""
    name: str
    namespace: str = "argocd"
    project: str = "default"
    sync_status: str  # Synced, OutOfSync, Unknown
    health_status: str  # Healthy, Degraded, Missing, Unknown
    repo_url: Optional[str] = None
    path: Optional[str] = None
    target_revision: str = "main"
    auto_sync: bool = False
    last_sync: Optional[datetime] = None


class ClusterResources(BaseModel):
    """Cluster resource summary."""
    total_nodes: int = 0
    ready_nodes: int = 0
    total_pods: int = 0
    running_pods: int = 0
    cpu_total_cores: float = 0
    cpu_used_cores: float = 0
    cpu_percent: float = 0
    memory_total_gb: float = 0
    memory_used_gb: float = 0
    memory_percent: float = 0
    storage_total_gb: float = 0
    storage_used_gb: float = 0
    storage_percent: float = 0


# =============================================================================
# KUBERNETES CLIENT SERVICE
# =============================================================================

class K8sClusterService:
    """
    Kubernetes cluster management service.

    Uses the Kubernetes Python client when running in-cluster,
    or kubeconfig for local development.
    """

    def __init__(self):
        """Initialize Kubernetes client."""
        self._initialized = False
        self._core_v1 = None
        self._apps_v1 = None
        self._networking_v1 = None
        self._custom = None
        self._metrics = None

    async def _init_client(self):
        """Lazy initialization of Kubernetes client."""
        if self._initialized:
            return

        try:
            from kubernetes import client, config
            from kubernetes.client.rest import ApiException

            # Try in-cluster config first
            if settings.K8S_IN_CLUSTER:
                try:
                    config.load_incluster_config()
                    logger.info("Loaded in-cluster Kubernetes config")
                except Exception:
                    # Fall back to kubeconfig
                    config.load_kube_config(config_file=settings.K8S_KUBECONFIG_PATH)
                    logger.info("Loaded kubeconfig from file")
            else:
                config.load_kube_config(config_file=settings.K8S_KUBECONFIG_PATH)
                logger.info("Loaded kubeconfig from file")

            self._core_v1 = client.CoreV1Api()
            self._apps_v1 = client.AppsV1Api()
            self._networking_v1 = client.NetworkingV1Api()
            self._custom = client.CustomObjectsApi()

            # Try to load metrics API (may not be available)
            try:
                self._metrics = client.CustomObjectsApi()
            except Exception:
                logger.warning("Metrics API not available")

            self._initialized = True

        except ImportError:
            logger.error("kubernetes package not installed. Run: pip install kubernetes")
            raise ServiceUnavailableError("Kubernetes")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            raise KubernetesError(
                message="Failed to connect to Kubernetes cluster",
                original_error=str(e)
            )

    # =========================================================================
    # NODES
    # =========================================================================

    async def get_nodes(self) -> List[NodeInfo]:
        """Get all cluster nodes with status and metrics."""
        await self._init_client()

        try:
            nodes = self._core_v1.list_node()
            node_list = []

            for node in nodes.items:
                # Parse node info
                name = node.metadata.name
                labels = dict(node.metadata.labels or {})

                # Determine role
                role = "worker"
                if "node-role.kubernetes.io/control-plane" in labels:
                    role = "control-plane"
                elif "node-role.kubernetes.io/master" in labels:
                    role = "control-plane"
                elif labels.get("role") == "inference":
                    role = "inference"
                elif labels.get("role") == "edge":
                    role = "edge"

                # Get status
                status = "Unknown"
                for condition in node.status.conditions or []:
                    if condition.type == "Ready":
                        status = "Ready" if condition.status == "True" else "NotReady"
                        break

                # Get addresses
                ip_address = None
                for address in node.status.addresses or []:
                    if address.type == "InternalIP":
                        ip_address = address.address
                        break

                # Get capacity
                capacity = node.status.capacity or {}
                cpu_cores = int(capacity.get("cpu", "0"))
                memory_str = capacity.get("memory", "0")
                memory_gb = self._parse_memory(memory_str) / (1024 ** 3)

                # Get node info
                node_info = node.status.node_info
                os_image = node_info.os_image if node_info else None
                kernel = node_info.kernel_version if node_info else None
                container_runtime = node_info.container_runtime_version if node_info else None
                kubelet_version = node_info.kubelet_version if node_info else None

                # Get pod capacity
                pods_capacity = int(capacity.get("pods", "110"))

                # Get running pods count
                pods = self._core_v1.list_pod_for_all_namespaces(
                    field_selector=f"spec.nodeName={name},status.phase=Running"
                )
                pods_running = len(pods.items)

                node_list.append(NodeInfo(
                    name=name,
                    status=status,
                    role=role,
                    ip_address=ip_address,
                    cpu_cores=cpu_cores,
                    memory_gb=round(memory_gb, 1),
                    pods_running=pods_running,
                    pods_capacity=pods_capacity,
                    os=os_image,
                    kernel=kernel,
                    container_runtime=container_runtime,
                    kubelet_version=kubelet_version,
                    labels=labels,
                    last_heartbeat=datetime.utcnow()
                ))

            return node_list

        except Exception as e:
            logger.error(f"Error getting nodes: {e}")
            raise KubernetesError(message="Failed to get cluster nodes", original_error=str(e))

    async def get_node(self, node_name: str) -> Optional[NodeInfo]:
        """Get a specific node by name."""
        nodes = await self.get_nodes()
        return next((n for n in nodes if n.name == node_name), None)

    # =========================================================================
    # DEPLOYMENTS
    # =========================================================================

    async def get_deployments(self, namespace: Optional[str] = None) -> List[DeploymentInfo]:
        """Get deployments, optionally filtered by namespace."""
        await self._init_client()

        try:
            if namespace:
                deployments = self._apps_v1.list_namespaced_deployment(namespace)
            else:
                deployments = self._apps_v1.list_deployment_for_all_namespaces()

            dep_list = []
            for dep in deployments.items:
                # Determine status
                desired = dep.spec.replicas or 0
                ready = dep.status.ready_replicas or 0
                available = dep.status.available_replicas or 0

                if ready >= desired and available >= desired:
                    status = "healthy"
                elif ready > 0:
                    status = "degraded"
                else:
                    status = "failed"

                # Get image from first container
                image = None
                if dep.spec.template.spec.containers:
                    image = dep.spec.template.spec.containers[0].image

                dep_list.append(DeploymentInfo(
                    name=dep.metadata.name,
                    namespace=dep.metadata.namespace,
                    replicas_desired=desired,
                    replicas_ready=ready,
                    replicas_available=available,
                    status=status,
                    image=image,
                    labels=dict(dep.metadata.labels or {}),
                    created_at=dep.metadata.creation_timestamp,
                    updated_at=dep.status.conditions[-1].last_update_time if dep.status.conditions else None
                ))

            return dep_list

        except Exception as e:
            logger.error(f"Error getting deployments: {e}")
            raise KubernetesError(message="Failed to get deployments", original_error=str(e))

    async def get_deployment(self, name: str, namespace: str) -> Optional[DeploymentInfo]:
        """Get a specific deployment."""
        deployments = await self.get_deployments(namespace)
        return next((d for d in deployments if d.name == name), None)

    async def scale_deployment(self, name: str, namespace: str, replicas: int) -> bool:
        """Scale a deployment to specified replicas."""
        await self._init_client()

        try:
            body = {"spec": {"replicas": replicas}}
            self._apps_v1.patch_namespaced_deployment_scale(
                name=name,
                namespace=namespace,
                body=body
            )
            logger.info(f"Scaled deployment {namespace}/{name} to {replicas} replicas")
            return True

        except Exception as e:
            logger.error(f"Error scaling deployment {namespace}/{name}: {e}")
            raise KubernetesError(
                message=f"Failed to scale deployment {name}",
                original_error=str(e)
            )

    async def restart_deployment(self, name: str, namespace: str) -> bool:
        """Restart a deployment by updating its annotation."""
        await self._init_client()

        try:
            # Add/update restart annotation to trigger rollout
            body = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": datetime.utcnow().isoformat()
                            }
                        }
                    }
                }
            }
            self._apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=body
            )
            logger.info(f"Restarted deployment {namespace}/{name}")
            return True

        except Exception as e:
            logger.error(f"Error restarting deployment {namespace}/{name}: {e}")
            raise KubernetesError(
                message=f"Failed to restart deployment {name}",
                original_error=str(e)
            )

    # =========================================================================
    # PODS
    # =========================================================================

    async def get_pods(self, namespace: Optional[str] = None, label_selector: Optional[str] = None) -> List[PodInfo]:
        """Get pods, optionally filtered by namespace and labels."""
        await self._init_client()

        try:
            kwargs = {}
            if label_selector:
                kwargs["label_selector"] = label_selector

            if namespace:
                pods = self._core_v1.list_namespaced_pod(namespace, **kwargs)
            else:
                pods = self._core_v1.list_pod_for_all_namespaces(**kwargs)

            pod_list = []
            for pod in pods.items:
                containers = [c.name for c in pod.spec.containers]

                # Calculate total restarts
                restarts = 0
                if pod.status.container_statuses:
                    restarts = sum(c.restart_count for c in pod.status.container_statuses)

                pod_list.append(PodInfo(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    status=pod.status.phase,
                    node=pod.spec.node_name,
                    ip=pod.status.pod_ip,
                    containers=containers,
                    restarts=restarts,
                    created_at=pod.metadata.creation_timestamp
                ))

            return pod_list

        except Exception as e:
            logger.error(f"Error getting pods: {e}")
            raise KubernetesError(message="Failed to get pods", original_error=str(e))

    async def delete_pod(self, name: str, namespace: str) -> bool:
        """Delete a pod (triggers restart if managed by deployment)."""
        await self._init_client()

        try:
            self._core_v1.delete_namespaced_pod(name=name, namespace=namespace)
            logger.info(f"Deleted pod {namespace}/{name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting pod {namespace}/{name}: {e}")
            raise KubernetesError(
                message=f"Failed to delete pod {name}",
                original_error=str(e)
            )

    # =========================================================================
    # SERVICES
    # =========================================================================

    async def get_services(self, namespace: Optional[str] = None) -> List[ServiceInfo]:
        """Get services, optionally filtered by namespace."""
        await self._init_client()

        try:
            if namespace:
                services = self._core_v1.list_namespaced_service(namespace)
            else:
                services = self._core_v1.list_service_for_all_namespaces()

            svc_list = []
            for svc in services.items:
                ports = []
                for port in svc.spec.ports or []:
                    ports.append({
                        "name": port.name,
                        "port": port.port,
                        "target_port": str(port.target_port),
                        "protocol": port.protocol
                    })

                external_ip = None
                if svc.status.load_balancer and svc.status.load_balancer.ingress:
                    external_ip = svc.status.load_balancer.ingress[0].ip

                svc_list.append(ServiceInfo(
                    name=svc.metadata.name,
                    namespace=svc.metadata.namespace,
                    type=svc.spec.type,
                    cluster_ip=svc.spec.cluster_ip,
                    external_ip=external_ip,
                    ports=ports
                ))

            return svc_list

        except Exception as e:
            logger.error(f"Error getting services: {e}")
            raise KubernetesError(message="Failed to get services", original_error=str(e))

    # =========================================================================
    # INGRESSES
    # =========================================================================

    async def get_ingresses(self, namespace: Optional[str] = None) -> List[IngressInfo]:
        """Get ingresses, optionally filtered by namespace."""
        await self._init_client()

        try:
            if namespace:
                ingresses = self._networking_v1.list_namespaced_ingress(namespace)
            else:
                ingresses = self._networking_v1.list_ingress_for_all_namespaces()

            ing_list = []
            for ing in ingresses.items:
                hosts = []
                paths = []

                for rule in ing.spec.rules or []:
                    if rule.host:
                        hosts.append(rule.host)
                    if rule.http:
                        for path in rule.http.paths or []:
                            paths.append(path.path or "/")

                tls = bool(ing.spec.tls)

                ing_list.append(IngressInfo(
                    name=ing.metadata.name,
                    namespace=ing.metadata.namespace,
                    hosts=hosts,
                    paths=paths,
                    tls=tls
                ))

            return ing_list

        except Exception as e:
            logger.error(f"Error getting ingresses: {e}")
            raise KubernetesError(message="Failed to get ingresses", original_error=str(e))

    # =========================================================================
    # ARGOCD
    # =========================================================================

    async def get_argocd_apps(self) -> List[ArgoCDApp]:
        """Get ArgoCD applications."""
        await self._init_client()

        try:
            apps = self._custom.list_namespaced_custom_object(
                group="argoproj.io",
                version="v1alpha1",
                namespace="argocd",
                plural="applications"
            )

            app_list = []
            for app in apps.get("items", []):
                spec = app.get("spec", {})
                status = app.get("status", {})
                source = spec.get("source", {})

                sync_status = "Unknown"
                health_status = "Unknown"

                if status.get("sync"):
                    sync_status = status["sync"].get("status", "Unknown")
                if status.get("health"):
                    health_status = status["health"].get("status", "Unknown")

                # Check if auto-sync is enabled
                auto_sync = bool(spec.get("syncPolicy", {}).get("automated"))

                # Get last sync time
                last_sync = None
                if status.get("operationState", {}).get("finishedAt"):
                    try:
                        last_sync = datetime.fromisoformat(
                            status["operationState"]["finishedAt"].replace("Z", "+00:00")
                        )
                    except Exception:
                        pass

                app_list.append(ArgoCDApp(
                    name=app["metadata"]["name"],
                    namespace=app["metadata"].get("namespace", "argocd"),
                    project=spec.get("project", "default"),
                    sync_status=sync_status,
                    health_status=health_status,
                    repo_url=source.get("repoURL"),
                    path=source.get("path"),
                    target_revision=source.get("targetRevision", "main"),
                    auto_sync=auto_sync,
                    last_sync=last_sync
                ))

            return app_list

        except Exception as e:
            logger.error(f"Error getting ArgoCD apps: {e}")
            raise KubernetesError(message="Failed to get ArgoCD applications", original_error=str(e))

    async def sync_argocd_app(self, app_name: str, prune: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Trigger sync for an ArgoCD application."""
        # Use ArgoCD API for sync operations
        if not settings.ARGOCD_TOKEN:
            raise ServiceUnavailableError("ArgoCD")

        try:
            async with httpx.AsyncClient(verify=False) as client:
                headers = {"Authorization": f"Bearer {settings.ARGOCD_TOKEN}"}
                url = f"{settings.ARGOCD_URL}/api/v1/applications/{app_name}/sync"

                body = {
                    "prune": prune,
                    "dryRun": dry_run
                }

                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()

                logger.info(f"Triggered sync for ArgoCD app {app_name}")
                return {
                    "application": app_name,
                    "status": "Syncing" if not dry_run else "DryRun",
                    "message": f"Sync {'(dry-run) ' if dry_run else ''}triggered for {app_name}"
                }

        except Exception as e:
            logger.error(f"Error syncing ArgoCD app {app_name}: {e}")
            raise KubernetesError(
                message=f"Failed to sync ArgoCD application {app_name}",
                original_error=str(e)
            )

    # =========================================================================
    # RESOURCES
    # =========================================================================

    async def get_cluster_resources(self) -> ClusterResources:
        """Get aggregated cluster resource usage."""
        await self._init_client()

        try:
            nodes = await self.get_nodes()
            pods = await self.get_pods()

            total_nodes = len(nodes)
            ready_nodes = len([n for n in nodes if n.status == "Ready"])
            total_pods = len(pods)
            running_pods = len([p for p in pods if p.status == "Running"])

            # Aggregate resources
            cpu_total = sum(n.cpu_cores or 0 for n in nodes)
            memory_total = sum(n.memory_gb or 0 for n in nodes)

            # Estimate usage (would need metrics-server for accurate values)
            # For now, calculate based on pod count vs capacity
            cpu_used = cpu_total * (running_pods / max(sum(n.pods_capacity or 110 for n in nodes), 1)) * 0.8
            memory_used = memory_total * (running_pods / max(sum(n.pods_capacity or 110 for n in nodes), 1)) * 0.85

            return ClusterResources(
                total_nodes=total_nodes,
                ready_nodes=ready_nodes,
                total_pods=total_pods,
                running_pods=running_pods,
                cpu_total_cores=cpu_total,
                cpu_used_cores=round(cpu_used, 1),
                cpu_percent=round((cpu_used / max(cpu_total, 1)) * 100, 1),
                memory_total_gb=round(memory_total, 1),
                memory_used_gb=round(memory_used, 1),
                memory_percent=round((memory_used / max(memory_total, 1)) * 100, 1)
            )

        except Exception as e:
            logger.error(f"Error getting cluster resources: {e}")
            raise KubernetesError(message="Failed to get cluster resources", original_error=str(e))

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _parse_memory(self, memory_str: str) -> float:
        """Parse Kubernetes memory string to bytes."""
        if not memory_str:
            return 0

        units = {
            "Ki": 1024,
            "Mi": 1024 ** 2,
            "Gi": 1024 ** 3,
            "Ti": 1024 ** 4,
            "K": 1000,
            "M": 1000 ** 2,
            "G": 1000 ** 3,
            "T": 1000 ** 4
        }

        for suffix, multiplier in units.items():
            if memory_str.endswith(suffix):
                return float(memory_str[:-len(suffix)]) * multiplier

        try:
            return float(memory_str)
        except ValueError:
            return 0

    async def health_check(self) -> Dict[str, Any]:
        """Check Kubernetes connectivity."""
        try:
            await self._init_client()
            nodes = await self.get_nodes()
            return {
                "status": "healthy",
                "service": "kubernetes",
                "nodes": len(nodes),
                "ready_nodes": len([n for n in nodes if n.status == "Ready"])
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "kubernetes",
                "error": str(e)
            }


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_k8s_service: Optional[K8sClusterService] = None


def get_k8s_service() -> K8sClusterService:
    """Get or create K8s cluster service singleton."""
    global _k8s_service
    if _k8s_service is None:
        _k8s_service = K8sClusterService()
    return _k8s_service
