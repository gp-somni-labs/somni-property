"""
Fleet Deployment Service
Deploys Kubernetes service packages to Tier 2/3 hubs via GitOps
"""

import logging
import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import PropertyEdgeNode, ServicePackage, FleetDeployment
from db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class FleetDeploymentService:
    """
    Deploy Kubernetes service packages to Tier 2/3 hubs

    This service orchestrates deployments from Tier 1 (Master Hub) to
    downstream Tier 2 (Property Hubs) and Tier 3 (Residential Hubs).

    Deployment Flow:
    1. Fetch service package manifest definition from database
    2. Get hub connection info (Tailscale IP, API token)
    3. Fetch manifests from Git repository
    4. Push manifests to hub's GitOps controller (ArgoCD/Flux)
    5. Monitor deployment status
    6. Record deployment results in FleetDeployment table

    Supports:
    - Single hub deployments
    - Bulk deployments to multiple hubs
    - Tier-based filtering (all tier_2, all tier_3)
    - Deployment status tracking
    - Rollback capabilities
    """

    def __init__(self):
        self.http_timeout = 30.0  # HTTP request timeout in seconds
        self.deployment_check_interval = 10  # Check deployment status every 10s
        self.max_deployment_wait = 600  # Max 10 minutes wait for deployment

    async def deploy_to_hub(
        self,
        hub_id: str,
        service_package_id: str,
        manifest_version: str,
        initiated_by: str
    ) -> Dict:
        """
        Deploy a service package to a specific hub

        Args:
            hub_id: UUID of the PropertyEdgeNode (Tier 2/3 hub)
            service_package_id: UUID of the ServicePackage to deploy
            manifest_version: Git commit SHA or version tag
            initiated_by: Username who triggered the deployment

        Returns:
            Dict with deployment results: {
                "deployment_id": "uuid",
                "status": "success|failed",
                "message": "Deployment completed successfully",
                "duration_seconds": 45.2
            }
        """
        logger.info(f"Starting deployment of package {service_package_id} to hub {hub_id}")

        start_time = datetime.now()

        async with AsyncSessionLocal() as session:
            # Validate hub exists
            stmt = select(PropertyEdgeNode).where(PropertyEdgeNode.id == hub_id)
            result = await session.execute(stmt)
            hub = result.scalar_one_or_none()

            if not hub:
                raise ValueError(f"Hub {hub_id} not found")

            # Validate service package exists
            stmt = select(ServicePackage).where(ServicePackage.id == service_package_id)
            result = await session.execute(stmt)
            service_package = result.scalar_one_or_none()

            if not service_package:
                raise ValueError(f"Service package {service_package_id} not found")

            # Validate tier compatibility
            if service_package.target_tier not in [hub.hub_type.replace('tier_', 'tier_'), 'both']:
                raise ValueError(
                    f"Service package targets {service_package.target_tier} "
                    f"but hub is {hub.hub_type}"
                )

            # Create deployment record
            deployment = FleetDeployment(
                target_hub_id=hub_id,
                target_hub_type=hub.hub_type,
                service_package_id=service_package_id,
                manifest_version=manifest_version,
                deployment_status='pending',
                initiated_by=initiated_by
            )
            session.add(deployment)
            await session.commit()
            await session.refresh(deployment)

            deployment_id = str(deployment.id)

            try:
                # Update status to deploying
                deployment.deployment_status = 'deploying'
                await session.commit()

                # Execute deployment
                deployment_log = await self._execute_deployment(
                    hub=hub,
                    service_package=service_package,
                    manifest_version=manifest_version
                )

                # Monitor deployment status
                success = await self._monitor_deployment(hub, service_package)

                # Update deployment record
                deployment.deployment_status = 'success' if success else 'failed'
                deployment.completed_at = datetime.now()
                deployment.deployment_log = deployment_log

                if not success:
                    deployment.error_message = "Deployment failed - check logs for details"

                # Update hub manifest version if successful
                if success:
                    hub.deployed_stack = service_package.name
                    hub.manifest_version = manifest_version

                await session.commit()

                duration = (datetime.now() - start_time).total_seconds()

                logger.info(
                    f"Deployment {deployment_id} {'succeeded' if success else 'failed'} "
                    f"in {duration:.1f} seconds"
                )

                return {
                    "deployment_id": deployment_id,
                    "status": "success" if success else "failed",
                    "message": "Deployment completed successfully" if success else "Deployment failed",
                    "duration_seconds": duration
                }

            except Exception as e:
                logger.error(f"Error during deployment {deployment_id}: {e}", exc_info=True)

                # Update deployment record with error
                deployment.deployment_status = 'failed'
                deployment.completed_at = datetime.now()
                deployment.error_message = str(e)

                await session.commit()

                raise

    async def bulk_deploy(
        self,
        hub_filter: str,
        service_package_id: str,
        manifest_version: str,
        initiated_by: str,
        hub_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        Deploy to multiple hubs in parallel

        Args:
            hub_filter: 'all_tier_2' | 'all_tier_3' | 'all' | 'custom'
            service_package_id: UUID of the ServicePackage to deploy
            manifest_version: Git commit SHA or version tag
            initiated_by: Username who triggered the deployment
            hub_ids: List of hub UUIDs (required if hub_filter='custom')

        Returns:
            Dict with bulk deployment results: {
                "total_hubs": 10,
                "successful": 8,
                "failed": 2,
                "deployments": [...]
            }
        """
        logger.info(f"Starting bulk deployment with filter '{hub_filter}'")

        async with AsyncSessionLocal() as session:
            # Get target hubs based on filter
            if hub_filter == 'all_tier_2':
                stmt = select(PropertyEdgeNode).where(
                    PropertyEdgeNode.hub_type == 'tier_2_property'
                )
            elif hub_filter == 'all_tier_3':
                stmt = select(PropertyEdgeNode).where(
                    PropertyEdgeNode.hub_type == 'tier_3_residential'
                )
            elif hub_filter == 'all':
                stmt = select(PropertyEdgeNode).where(
                    PropertyEdgeNode.managed_by_tier1 == True
                )
            elif hub_filter == 'custom':
                if not hub_ids:
                    raise ValueError("hub_ids required when hub_filter='custom'")
                stmt = select(PropertyEdgeNode).where(
                    PropertyEdgeNode.id.in_(hub_ids)
                )
            else:
                raise ValueError(f"Invalid hub_filter: {hub_filter}")

            result = await session.execute(stmt)
            target_hubs = result.scalars().all()

        if not target_hubs:
            return {
                "total_hubs": 0,
                "successful": 0,
                "failed": 0,
                "deployments": []
            }

        # Deploy to all hubs in parallel
        deployment_tasks = [
            self.deploy_to_hub(
                hub_id=str(hub.id),
                service_package_id=service_package_id,
                manifest_version=manifest_version,
                initiated_by=initiated_by
            )
            for hub in target_hubs
        ]

        results = await asyncio.gather(*deployment_tasks, return_exceptions=True)

        # Analyze results
        successful = 0
        failed = 0
        deployments = []

        for i, result in enumerate(results):
            hub = target_hubs[i]

            if isinstance(result, Exception):
                failed += 1
                deployments.append({
                    "hub_id": str(hub.id),
                    "hub_name": hub.hostname,
                    "status": "failed",
                    "error": str(result)
                })
            else:
                if result['status'] == 'success':
                    successful += 1
                else:
                    failed += 1
                deployments.append({
                    "hub_id": str(hub.id),
                    "hub_name": hub.hostname,
                    "status": result['status'],
                    "deployment_id": result['deployment_id']
                })

        logger.info(
            f"Bulk deployment complete: {successful} successful, "
            f"{failed} failed out of {len(target_hubs)} total"
        )

        return {
            "total_hubs": len(target_hubs),
            "successful": successful,
            "failed": failed,
            "deployments": deployments
        }

    async def get_deployment_status(self, deployment_id: str) -> Dict:
        """
        Get status of a specific deployment

        Args:
            deployment_id: UUID of the FleetDeployment

        Returns:
            Dict with deployment details
        """
        async with AsyncSessionLocal() as session:
            stmt = select(FleetDeployment).where(FleetDeployment.id == deployment_id)
            result = await session.execute(stmt)
            deployment = result.scalar_one_or_none()

            if not deployment:
                raise ValueError(f"Deployment {deployment_id} not found")

            duration = None
            if deployment.completed_at:
                duration = (deployment.completed_at - deployment.initiated_at).total_seconds()

            return {
                "deployment_id": str(deployment.id),
                "hub_id": str(deployment.target_hub_id),
                "service_package_id": str(deployment.service_package_id),
                "manifest_version": deployment.manifest_version,
                "status": deployment.deployment_status,
                "initiated_at": deployment.initiated_at.isoformat(),
                "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None,
                "duration_seconds": duration,
                "error_message": deployment.error_message,
                "initiated_by": deployment.initiated_by
            }

    async def _execute_deployment(
        self,
        hub: PropertyEdgeNode,
        service_package: ServicePackage,
        manifest_version: str
    ) -> str:
        """
        Execute the actual deployment to the hub

        This is a placeholder for the actual implementation.
        In production, this would:
        1. Fetch manifests from Git repo (service_package.manifest_repo_url)
        2. Apply manifests to hub's GitOps controller via API
        3. Return deployment logs

        Args:
            hub: Target PropertyEdgeNode
            service_package: ServicePackage to deploy
            manifest_version: Git commit SHA

        Returns:
            Deployment log as string
        """
        # TODO: Implement actual deployment logic
        # This would involve:
        # 1. Clone/fetch from service_package.manifest_repo_url
        # 2. Checkout manifest_version
        # 3. Read manifests from service_package.manifest_path
        # 4. POST to hub's GitOps API (ArgoCD/Flux)
        #    URL: f"http://{hub.tailscale_ip}/api/argocd/applications"
        #    Headers: {"Authorization": f"Bearer {hub_api_token}"}
        # 5. Return API response logs

        logger.info(
            f"[PLACEHOLDER] Deploying {service_package.name} v{manifest_version} "
            f"to hub {hub.hostname} at {hub.tailscale_ip}"
        )

        deployment_log = f"""
Deployment initiated at {datetime.now().isoformat()}
Target Hub: {hub.hostname} ({hub.tailscale_ip})
Service Package: {service_package.name}
Manifest Version: {manifest_version}
Manifest Repo: {service_package.manifest_repo_url or 'N/A'}
Manifest Path: {service_package.manifest_path or 'N/A'}

[PLACEHOLDER] In production, this would:
1. Fetch manifests from Git repository
2. Apply to hub's GitOps controller
3. Monitor rollout status

Deployment completed at {datetime.now().isoformat()}
"""

        return deployment_log

    async def _monitor_deployment(
        self,
        hub: PropertyEdgeNode,
        service_package: ServicePackage
    ) -> bool:
        """
        Monitor deployment status on the hub

        This is a placeholder for the actual implementation.
        In production, this would:
        1. Poll hub's GitOps API for deployment status
        2. Wait for all pods to be ready
        3. Return True if successful, False if failed

        Args:
            hub: Target PropertyEdgeNode
            service_package: ServicePackage being deployed

        Returns:
            True if deployment successful, False otherwise
        """
        # TODO: Implement actual monitoring logic
        # This would involve:
        # 1. Poll ArgoCD/Flux API for application sync status
        #    GET http://{hub.tailscale_ip}/api/argocd/applications/{app_name}
        # 2. Check if sync_status == 'Synced' and health_status == 'Healthy'
        # 3. Wait up to self.max_deployment_wait seconds
        # 4. Return True if healthy, False if timeout/failed

        logger.info(
            f"[PLACEHOLDER] Monitoring deployment of {service_package.name} "
            f"on hub {hub.hostname}"
        )

        # Simulate monitoring delay
        await asyncio.sleep(2)

        # Placeholder: always return success
        # In production, this would actually check deployment health
        return True

    async def rollback_deployment(
        self,
        hub_id: str,
        previous_manifest_version: str,
        initiated_by: str
    ) -> Dict:
        """
        Rollback a hub to a previous manifest version

        Args:
            hub_id: UUID of the PropertyEdgeNode
            previous_manifest_version: Git commit SHA to rollback to
            initiated_by: Username who triggered the rollback

        Returns:
            Dict with rollback results
        """
        logger.info(f"Rolling back hub {hub_id} to version {previous_manifest_version}")

        async with AsyncSessionLocal() as session:
            # Get hub
            stmt = select(PropertyEdgeNode).where(PropertyEdgeNode.id == hub_id)
            result = await session.execute(stmt)
            hub = result.scalar_one_or_none()

            if not hub:
                raise ValueError(f"Hub {hub_id} not found")

            # Get the service package currently deployed
            stmt = select(ServicePackage).where(
                ServicePackage.name == hub.deployed_stack
            )
            result = await session.execute(stmt)
            service_package = result.scalar_one_or_none()

            if not service_package:
                raise ValueError(f"No service package found for deployed stack: {hub.deployed_stack}")

            # Trigger deployment with previous version
            return await self.deploy_to_hub(
                hub_id=hub_id,
                service_package_id=str(service_package.id),
                manifest_version=previous_manifest_version,
                initiated_by=f"{initiated_by} (rollback)"
            )


# Global fleet deployment service instance
fleet_deployment_service = FleetDeploymentService()


async def get_fleet_deployment_service() -> FleetDeploymentService:
    """Dependency to get fleet deployment service instance"""
    return fleet_deployment_service
