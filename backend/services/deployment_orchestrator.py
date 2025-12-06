"""
Somni Property Manager - Deployment Orchestrator Service

Orchestrates automatic deployment of infrastructure stacks based on hub tier type:
- Tier 2/3: Deploy full k3s cluster with Home Assistant, EMQX, monitoring
- Tier 0: Deploy SomniProperty HA integration to existing Home Assistant instance
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import PropertyEdgeNode
from services.ssh_deployer import SSHDeployer
from services.ha_api_client import HomeAssistantAPIClient
from core.encryption import EncryptionService

logger = logging.getLogger(__name__)


class DeploymentResult:
    """Result of a deployment operation"""

    def __init__(
        self,
        success: bool,
        message: str,
        deployed_components: Optional[List[str]] = None,
        logs: Optional[str] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.message = message
        self.deployed_components = deployed_components or []
        self.logs = logs or ""
        self.error = error


class DeploymentOrchestrator:
    """
    Orchestrates hub deployments based on tier type

    Workflow:
    1. User registers hub via EdgeNodeModal (Frontend)
    2. Backend creates PropertyEdgeNode record with deployment_status='pending'
    3. User provides deployment credentials (SSH keys for Tier 2/3, HA token for Tier 0)
    4. Frontend calls POST /api/v1/edge-nodes/{id}/deploy
    5. DeploymentOrchestrator triggers appropriate deployment workflow
    6. Deployment progress is tracked in database
    7. Frontend polls GET /api/v1/edge-nodes/{id}/deployment-status for updates
    8. On completion, deployment_status is updated to 'deployed' or 'failed'
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ssh_deployer = SSHDeployer()
        self.ha_client = HomeAssistantAPIClient()
        self.encryption = EncryptionService()

    async def deploy_hub(
        self,
        edge_node: PropertyEdgeNode,
        deployment_config: Dict[str, Any]
    ) -> DeploymentResult:
        """
        Main entry point for hub deployment

        Args:
            edge_node: PropertyEdgeNode instance to deploy
            deployment_config: Deployment configuration (SSH or HA credentials)

        Returns:
            DeploymentResult with success status, logs, and deployed components
        """
        logger.info(f"Starting deployment for hub {edge_node.id} ({edge_node.hostname})")

        # Update deployment status to 'in_progress'
        edge_node.deployment_status = 'in_progress'
        edge_node.deployment_started_at = datetime.utcnow()
        edge_node.deployment_progress_percent = 0
        edge_node.deployment_current_step = 'Initializing deployment...'
        edge_node.deployment_logs = f"[{datetime.utcnow().isoformat()}] Deployment started\n"
        await self.db.flush()

        try:
            # Route to appropriate deployment method based on hub type
            if edge_node.hub_type in ['tier_2_property', 'tier_3_residential']:
                result = await self._deploy_k3s_cluster(edge_node, deployment_config)
            elif edge_node.hub_type == 'tier_0_standalone':
                result = await self._deploy_somni_components(edge_node, deployment_config)
            else:
                raise ValueError(f"Unknown hub type: {edge_node.hub_type}")

            # Update deployment status based on result
            if result.success:
                edge_node.deployment_status = 'deployed'
                edge_node.deployment_completed_at = datetime.utcnow()
                edge_node.deployment_progress_percent = 100
                edge_node.deployment_current_step = 'Deployment completed successfully'
                edge_node.deployed_components = result.deployed_components
            else:
                edge_node.deployment_status = 'failed'
                edge_node.deployment_error_message = result.error
                edge_node.deployment_current_step = f'Deployment failed: {result.error}'

            edge_node.deployment_logs += result.logs
            await self.db.flush()

            logger.info(
                f"Deployment {'succeeded' if result.success else 'failed'} for hub {edge_node.id}"
            )
            return result

        except Exception as e:
            logger.exception(f"Deployment failed for hub {edge_node.id}: {e}")
            edge_node.deployment_status = 'failed'
            edge_node.deployment_error_message = str(e)
            edge_node.deployment_current_step = f'Deployment failed with exception: {str(e)}'
            edge_node.deployment_logs += f"\n[{datetime.utcnow().isoformat()}] ERROR: {str(e)}\n"
            await self.db.flush()

            return DeploymentResult(
                success=False,
                message="Deployment failed with exception",
                error=str(e),
                logs=edge_node.deployment_logs
            )

    async def _deploy_k3s_cluster(
        self,
        edge_node: PropertyEdgeNode,
        deployment_config: Dict[str, Any]
    ) -> DeploymentResult:
        """
        Deploy managed k3s cluster with full stack

        Steps:
        1. Validate SSH configuration
        2. Test SSH connectivity
        3. Install k3s on remote host
        4. Retrieve kubeconfig
        5. Apply deployment manifests (core services, HA, monitoring)
        6. Configure Tailscale mesh networking
        7. Verify all pods are running
        8. Configure SomniProperty HA integration with Hub ID

        Args:
            edge_node: PropertyEdgeNode instance
            deployment_config: {
                "ssh_host": "192.168.1.100",
                "ssh_port": 22,
                "ssh_user": "admin",
                "ssh_key": "-----BEGIN PRIVATE KEY-----..."
            }

        Returns:
            DeploymentResult
        """
        logs = ""
        deployed_components = []

        try:
            # Extract and encrypt SSH configuration
            ssh_host = deployment_config.get('ssh_host', edge_node.ip_address)
            ssh_port = deployment_config.get('ssh_port', 22)
            ssh_user = deployment_config.get('ssh_user', 'admin')
            ssh_key = deployment_config.get('ssh_key')

            if not ssh_key:
                return DeploymentResult(
                    success=False,
                    message="SSH private key is required for Tier 2/3 deployment",
                    error="Missing SSH key",
                    logs=logs
                )

            # Store encrypted SSH credentials
            edge_node.deployment_ssh_host = ssh_host
            edge_node.deployment_ssh_port = ssh_port
            edge_node.deployment_ssh_user = ssh_user
            edge_node.deployment_ssh_key_encrypted = self.encryption.encrypt(ssh_key)
            await self.db.flush()

            logs += f"[{datetime.utcnow().isoformat()}] SSH configuration stored\n"
            edge_node.deployment_logs += logs
            await self.db.flush()

            # Step 1: Test SSH connectivity
            edge_node.deployment_progress_percent = 10
            edge_node.deployment_current_step = f'Testing SSH connectivity to {ssh_host}:{ssh_port}...'
            await self.db.flush()

            connectivity_test = await self.ssh_deployer.test_connectivity(
                host=ssh_host,
                port=ssh_port,
                user=ssh_user,
                ssh_key=ssh_key
            )

            if not connectivity_test:
                return DeploymentResult(
                    success=False,
                    message=f"Failed to connect to {ssh_host}:{ssh_port}",
                    error="SSH connectivity test failed",
                    logs=logs
                )

            logs += f"[{datetime.utcnow().isoformat()}] SSH connectivity test passed\n"
            edge_node.deployment_logs += logs
            await self.db.flush()

            # Step 2: Install k3s
            edge_node.deployment_progress_percent = 20
            edge_node.deployment_current_step = 'Installing k3s cluster...'
            await self.db.flush()

            k3s_install_result = await self.ssh_deployer.install_k3s(
                host=ssh_host,
                port=ssh_port,
                user=ssh_user,
                ssh_key=ssh_key
            )

            if not k3s_install_result.success:
                return DeploymentResult(
                    success=False,
                    message="Failed to install k3s",
                    error=k3s_install_result.error,
                    logs=logs + k3s_install_result.logs
                )

            logs += k3s_install_result.logs
            edge_node.deployment_logs += k3s_install_result.logs
            deployed_components.append('k3s')
            await self.db.flush()

            # Step 3: Apply deployment manifests
            edge_node.deployment_progress_percent = 40
            edge_node.deployment_current_step = 'Applying deployment manifests...'
            await self.db.flush()

            # Determine which manifest template to use
            manifest_template = 'tier2-property-hub' if edge_node.hub_type == 'tier_2_property' else 'tier3-residential-hub'

            manifest_result = await self.ssh_deployer.apply_manifests(
                host=ssh_host,
                port=ssh_port,
                user=ssh_user,
                ssh_key=ssh_key,
                manifest_template=manifest_template,
                hub_id=str(edge_node.id),
                backend_url="http://somniproperty-backend.somniproperty.svc.cluster.local:8000"
            )

            if not manifest_result.success:
                return DeploymentResult(
                    success=False,
                    message="Failed to apply deployment manifests",
                    error=manifest_result.error,
                    logs=logs + manifest_result.logs
                )

            logs += manifest_result.logs
            edge_node.deployment_logs += manifest_result.logs
            deployed_components.extend(['postgresql', 'emqx', 'home_assistant', 'monitoring'])
            await self.db.flush()

            # Step 4: Configure Tailscale (optional)
            if edge_node.tailscale_ip:
                edge_node.deployment_progress_percent = 70
                edge_node.deployment_current_step = 'Configuring Tailscale mesh...'
                await self.db.flush()

                tailscale_result = await self.ssh_deployer.configure_tailscale(
                    host=ssh_host,
                    port=ssh_port,
                    user=ssh_user,
                    ssh_key=ssh_key
                )

                if tailscale_result.success:
                    logs += tailscale_result.logs
                    edge_node.deployment_logs += tailscale_result.logs
                    deployed_components.append('tailscale')
                    await self.db.flush()

            # Step 5: Verify deployment
            edge_node.deployment_progress_percent = 90
            edge_node.deployment_current_step = 'Verifying deployment...'
            await self.db.flush()

            verify_result = await self.ssh_deployer.verify_deployment(
                host=ssh_host,
                port=ssh_port,
                user=ssh_user,
                ssh_key=ssh_key
            )

            if not verify_result.success:
                return DeploymentResult(
                    success=False,
                    message="Deployment verification failed - some pods are not running",
                    error=verify_result.error,
                    logs=logs + verify_result.logs
                )

            logs += verify_result.logs
            edge_node.deployment_logs += verify_result.logs
            await self.db.flush()

            # Success!
            return DeploymentResult(
                success=True,
                message=f"Successfully deployed {edge_node.hub_type} cluster",
                deployed_components=deployed_components,
                logs=logs
            )

        except Exception as e:
            logger.exception(f"k3s deployment failed for hub {edge_node.id}: {e}")
            return DeploymentResult(
                success=False,
                message="k3s deployment failed with exception",
                error=str(e),
                logs=logs
            )

    async def _deploy_somni_components(
        self,
        edge_node: PropertyEdgeNode,
        deployment_config: Dict[str, Any]
    ) -> DeploymentResult:
        """
        Deploy SomniProperty integration to existing Home Assistant instance

        Steps:
        1. Validate HA configuration
        2. Test HA connectivity
        3. Upload SomniProperty integration files to /config/custom_components/
        4. Restart Home Assistant
        5. Configure integration via Config Flow API
        6. Verify device sync is working

        Args:
            edge_node: PropertyEdgeNode instance
            deployment_config: {
                "ha_url": "http://192.168.1.50:8123",
                "ha_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
            }

        Returns:
            DeploymentResult
        """
        logs = ""
        deployed_components = []

        try:
            # Extract and hash HA configuration
            ha_url = deployment_config.get('ha_url', edge_node.api_url)
            ha_token = deployment_config.get('ha_token')

            if not ha_token:
                return DeploymentResult(
                    success=False,
                    message="Home Assistant long-lived access token is required for Tier 0 deployment",
                    error="Missing HA token",
                    logs=logs
                )

            # Store HA configuration (hash the token for security)
            edge_node.deployment_ha_url = ha_url
            edge_node.deployment_ha_token_hash = self.encryption.hash_token(ha_token)
            await self.db.flush()

            logs += f"[{datetime.utcnow().isoformat()}] Home Assistant configuration stored\n"
            edge_node.deployment_logs += logs
            await self.db.flush()

            # Step 1: Test HA connectivity
            edge_node.deployment_progress_percent = 10
            edge_node.deployment_current_step = f'Testing connectivity to {ha_url}...'
            await self.db.flush()

            connectivity_test = await self.ha_client.test_connectivity(ha_url, ha_token)

            if not connectivity_test.success:
                return DeploymentResult(
                    success=False,
                    message=f"Failed to connect to Home Assistant at {ha_url}",
                    error=connectivity_test.error,
                    logs=logs + connectivity_test.logs
                )

            logs += connectivity_test.logs
            edge_node.deployment_logs += connectivity_test.logs
            await self.db.flush()

            # Step 2: Install SomniProperty custom component
            edge_node.deployment_progress_percent = 30
            edge_node.deployment_current_step = 'Installing SomniProperty integration...'
            await self.db.flush()

            install_result = await self.ha_client.install_custom_component(
                base_url=ha_url,
                token=ha_token,
                component_name='somniproperty',
                hub_id=str(edge_node.id),
                backend_url="http://somniproperty-backend.somniproperty.svc.cluster.local:8000"
            )

            if not install_result.success:
                return DeploymentResult(
                    success=False,
                    message="Failed to install SomniProperty integration",
                    error=install_result.error,
                    logs=logs + install_result.logs
                )

            logs += install_result.logs
            edge_node.deployment_logs += install_result.logs
            deployed_components.append('somniproperty_integration')
            await self.db.flush()

            # Step 3: Restart Home Assistant
            edge_node.deployment_progress_percent = 60
            edge_node.deployment_current_step = 'Restarting Home Assistant...'
            await self.db.flush()

            restart_result = await self.ha_client.restart_ha(ha_url, ha_token)

            if not restart_result.success:
                return DeploymentResult(
                    success=False,
                    message="Failed to restart Home Assistant",
                    error=restart_result.error,
                    logs=logs + restart_result.logs
                )

            logs += restart_result.logs
            edge_node.deployment_logs += restart_result.logs
            await self.db.flush()

            # Step 4: Wait for HA to come back online
            edge_node.deployment_progress_percent = 70
            edge_node.deployment_current_step = 'Waiting for Home Assistant to restart...'
            await self.db.flush()

            # Wait up to 120 seconds for HA to restart
            for i in range(24):
                await asyncio.sleep(5)
                online_check = await self.ha_client.test_connectivity(ha_url, ha_token)
                if online_check.success:
                    logs += f"[{datetime.utcnow().isoformat()}] Home Assistant is back online\n"
                    edge_node.deployment_logs += f"[{datetime.utcnow().isoformat()}] Home Assistant is back online\n"
                    await self.db.flush()
                    break
            else:
                return DeploymentResult(
                    success=False,
                    message="Home Assistant did not come back online after restart",
                    error="Restart timeout",
                    logs=logs
                )

            # Step 5: Verify integration is loaded
            edge_node.deployment_progress_percent = 90
            edge_node.deployment_current_step = 'Verifying integration is loaded...'
            await self.db.flush()

            verify_result = await self.ha_client.verify_integration(ha_url, ha_token, 'somniproperty')

            if not verify_result.success:
                return DeploymentResult(
                    success=False,
                    message="SomniProperty integration is not loaded in Home Assistant",
                    error=verify_result.error,
                    logs=logs + verify_result.logs
                )

            logs += verify_result.logs
            edge_node.deployment_logs += verify_result.logs
            await self.db.flush()

            # Success!
            return DeploymentResult(
                success=True,
                message=f"Successfully deployed SomniProperty integration to {ha_url}",
                deployed_components=deployed_components,
                logs=logs
            )

        except Exception as e:
            logger.exception(f"Somni Components deployment failed for hub {edge_node.id}: {e}")
            return DeploymentResult(
                success=False,
                message="Somni Components deployment failed with exception",
                error=str(e),
                logs=logs
            )

    async def get_deployment_status(self, edge_node_id: UUID) -> Dict[str, Any]:
        """
        Get current deployment status for a hub

        Returns:
            Dictionary with deployment progress, current step, logs, etc.
        """
        query = select(PropertyEdgeNode).where(PropertyEdgeNode.id == edge_node_id)
        result = await self.db.execute(query)
        edge_node = result.scalar_one_or_none()

        if not edge_node:
            raise ValueError(f"Edge node {edge_node_id} not found")

        return {
            "status": edge_node.deployment_status,
            "progress_percent": edge_node.deployment_progress_percent or 0,
            "current_step": edge_node.deployment_current_step or "Waiting to start",
            "started_at": edge_node.deployment_started_at.isoformat() if edge_node.deployment_started_at else None,
            "completed_at": edge_node.deployment_completed_at.isoformat() if edge_node.deployment_completed_at else None,
            "deployed_components": edge_node.deployed_components or [],
            "logs": edge_node.deployment_logs or "",
            "error": edge_node.deployment_error_message
        }
