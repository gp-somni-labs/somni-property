"""
Service Catalog Service - One-click service deployment to Tier 1/2 K3s clusters
Manages the catalog of available services and handles GitOps-based deployment
"""

import os
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import git
from sqlalchemy.orm import Session
from sqlalchemy import and_

from db.models import ServiceDeployment, PropertyEdgeNode

logger = logging.getLogger(__name__)


class ServiceCatalogService:
    """Service Catalog for one-click K8s service deployment"""

    def __init__(self, db: Session):
        self.db = db

        # Paths
        self.base_dir = Path(__file__).parent
        self.catalog_path = self.base_dir / "service_catalog.yaml"
        self.templates_dir = self.base_dir.parent / "templates" / "k8s"

        # Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Load catalog
        self._catalog = self._load_catalog()

    def _load_catalog(self) -> Dict[str, Any]:
        """Load service catalog from YAML"""
        try:
            with open(self.catalog_path, 'r') as f:
                catalog = yaml.safe_load(f)
            logger.info(f"Loaded service catalog with {len(catalog.get('services', []))} services")
            return catalog
        except Exception as e:
            logger.error(f"Failed to load service catalog: {e}")
            return {"services": [], "categories": []}

    def load_service_catalog(self) -> Dict[str, Any]:
        """Get the full service catalog"""
        return self._catalog

    def get_available_services(self, tier: str) -> List[Dict[str, Any]]:
        """
        Get available services filtered by tier

        Args:
            tier: Client tier (tier_0, tier_1, tier_2)

        Returns:
            List of service definitions available for the tier
        """
        services = self._catalog.get('services', [])

        # Filter by tier
        filtered_services = [
            service for service in services
            if tier in service.get('tiers', [])
        ]

        logger.info(f"Found {len(filtered_services)} services available for {tier}")
        return filtered_services

    def get_service_by_id(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get service definition by ID"""
        services = self._catalog.get('services', [])
        for service in services:
            if service.get('id') == service_id:
                return service
        return None

    def get_installed_services(self, client_id: str) -> List[ServiceDeployment]:
        """
        Get list of services installed for a client

        Args:
            client_id: Client/PropertyEdgeNode UUID

        Returns:
            List of ServiceDeployment records
        """
        deployments = self.db.query(ServiceDeployment).filter(
            and_(
                ServiceDeployment.client_id == client_id,
                ServiceDeployment.deployment_status.in_(['deployed', 'deploying', 'pending'])
            )
        ).all()

        logger.info(f"Client {client_id} has {len(deployments)} services installed")
        return deployments

    def is_service_installed(self, client_id: str, service_id: str) -> bool:
        """Check if a service is already installed for a client"""
        deployment = self.db.query(ServiceDeployment).filter(
            and_(
                ServiceDeployment.client_id == client_id,
                ServiceDeployment.service_id == service_id,
                ServiceDeployment.deployment_status != 'uninstalled'
            )
        ).first()
        return deployment is not None

    def generate_manifest(
        self,
        service_id: str,
        params: Dict[str, Any]
    ) -> str:
        """
        Generate Kubernetes manifest from template

        Args:
            service_id: Service identifier (e.g., "portainer")
            params: Template parameters (namespace, hostname, resources, etc.)

        Returns:
            Generated YAML manifest as string
        """
        # Get service definition
        service = self.get_service_by_id(service_id)
        if not service:
            raise ValueError(f"Service {service_id} not found in catalog")

        # Get template
        template_name = service.get('manifest_template')
        if not template_name:
            raise ValueError(f"No manifest template defined for service {service_id}")

        try:
            template = self.jinja_env.get_template(template_name)
        except TemplateNotFound:
            raise FileNotFoundError(f"Template {template_name} not found in {self.templates_dir}")

        # Merge default params with provided params
        default_params = {
            'namespace': service.get('default_namespace', 'default'),
            'cpu_request': service.get('resource_requirements', {}).get('cpu_request', '100m'),
            'cpu_limit': service.get('resource_requirements', {}).get('cpu_limit', '500m'),
            'memory_request': service.get('resource_requirements', {}).get('memory_request', '256Mi'),
            'memory_limit': service.get('resource_requirements', {}).get('memory_limit', '512Mi'),
            'ingress_enabled': service.get('ingress_required', True),
            'ingress_annotations': params.get('ingress_annotations', {}),
            'storage_class': 'local-path',
        }

        # Merge with user-provided params (user params take precedence)
        template_params = {**default_params, **params}

        # Render template
        manifest = template.render(**template_params)

        logger.info(f"Generated manifest for {service_id} with params: {list(template_params.keys())}")
        return manifest

    def deploy_service(
        self,
        client_id: str,
        service_id: str,
        params: Dict[str, Any]
    ) -> ServiceDeployment:
        """
        Deploy a service to client's GitOps repo

        Args:
            client_id: Client/PropertyEdgeNode UUID
            service_id: Service identifier
            params: Deployment parameters

        Returns:
            ServiceDeployment record
        """
        # Validate client exists
        client = self.db.query(PropertyEdgeNode).filter(PropertyEdgeNode.id == client_id).first()
        if not client:
            raise ValueError(f"Client {client_id} not found")

        # Check if service already installed
        if self.is_service_installed(client_id, service_id):
            raise ValueError(f"Service {service_id} is already installed for client {client_id}")

        # Get service definition
        service = self.get_service_by_id(service_id)
        if not service:
            raise ValueError(f"Service {service_id} not found in catalog")

        # Generate manifest
        try:
            manifest = self.generate_manifest(service_id, params)
        except Exception as e:
            logger.error(f"Failed to generate manifest for {service_id}: {e}")
            raise

        # Create deployment record
        deployment = ServiceDeployment(
            client_id=client_id,
            service_id=service_id,
            service_name=service.get('name'),
            deployment_status='pending',
            configuration=params
        )

        self.db.add(deployment)
        self.db.flush()  # Get ID without committing

        # Commit manifest to GitOps repo
        try:
            git_result = self._commit_to_gitops(
                client=client,
                service_id=service_id,
                manifest=manifest,
                deployment=deployment
            )

            # Update deployment with GitOps info
            deployment.deployment_status = 'deploying'
            deployment.git_commit_sha = git_result.get('commit_sha')
            deployment.gitops_repo_url = git_result.get('repo_url')
            deployment.gitops_repo_path = git_result.get('manifest_path')
            deployment.deployed_at = datetime.utcnow()

            self.db.commit()
            logger.info(f"Successfully deployed {service_id} to client {client_id}")

        except Exception as e:
            deployment.deployment_status = 'failed'
            deployment.error_message = str(e)
            self.db.commit()
            logger.error(f"Failed to deploy {service_id} to GitOps: {e}")
            raise

        return deployment

    def _commit_to_gitops(
        self,
        client: PropertyEdgeNode,
        service_id: str,
        manifest: str,
        deployment: ServiceDeployment
    ) -> Dict[str, str]:
        """
        Commit service manifest to client's GitOps repository

        Args:
            client: PropertyEdgeNode record
            service_id: Service identifier
            manifest: Generated manifest YAML
            deployment: ServiceDeployment record

        Returns:
            Dict with commit_sha, repo_url, manifest_path
        """
        # Get client's GitOps repo configuration
        # This would come from client configuration
        gitops_repo_url = os.getenv('GITOPS_REPO_URL')  # Or from client.gitops_repo_url
        gitops_repo_path = os.getenv('GITOPS_REPO_PATH', '/tmp/gitops-repos')

        if not gitops_repo_url:
            raise ValueError("GitOps repository URL not configured for client")

        # Clone or update repo
        repo_dir = Path(gitops_repo_path) / str(client.id)

        if repo_dir.exists():
            repo = git.Repo(repo_dir)
            repo.remotes.origin.pull()
        else:
            repo_dir.mkdir(parents=True, exist_ok=True)
            repo = git.Repo.clone_from(gitops_repo_url, repo_dir)

        # Write manifest to repo
        service_dir = repo_dir / 'services' / service_id
        service_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = service_dir / f'{service_id}.yaml'
        with open(manifest_path, 'w') as f:
            f.write(manifest)

        # Commit and push
        repo.index.add([str(manifest_path.relative_to(repo_dir))])

        commit_message = f"Deploy {service_id} for client {client.property.name if client.property else client.id}\n\n" \
                        f"Service: {deployment.service_name}\n" \
                        f"Deployment ID: {deployment.id}\n" \
                        f"Managed by: SomniProperty Service Catalog"

        commit = repo.index.commit(commit_message)
        repo.remotes.origin.push()

        logger.info(f"Committed {service_id} manifest to GitOps repo: {commit.hexsha}")

        return {
            'commit_sha': commit.hexsha,
            'repo_url': gitops_repo_url,
            'manifest_path': f'services/{service_id}/{service_id}.yaml'
        }

    def remove_service(
        self,
        client_id: str,
        service_id: str
    ) -> ServiceDeployment:
        """
        Remove a service from client's GitOps repo

        Args:
            client_id: Client/PropertyEdgeNode UUID
            service_id: Service identifier

        Returns:
            Updated ServiceDeployment record
        """
        # Get deployment record
        deployment = self.db.query(ServiceDeployment).filter(
            and_(
                ServiceDeployment.client_id == client_id,
                ServiceDeployment.service_id == service_id,
                ServiceDeployment.deployment_status == 'deployed'
            )
        ).first()

        if not deployment:
            raise ValueError(f"Service {service_id} not found or not deployed for client {client_id}")

        # Get client
        client = self.db.query(PropertyEdgeNode).filter(PropertyEdgeNode.id == client_id).first()
        if not client:
            raise ValueError(f"Client {client_id} not found")

        # Remove from GitOps repo
        try:
            self._remove_from_gitops(client, service_id, deployment)

            # Update deployment status
            deployment.deployment_status = 'uninstalled'
            deployment.uninstalled_at = datetime.utcnow()

            self.db.commit()
            logger.info(f"Successfully removed {service_id} from client {client_id}")

        except Exception as e:
            deployment.error_message = f"Failed to remove: {str(e)}"
            self.db.commit()
            logger.error(f"Failed to remove {service_id} from GitOps: {e}")
            raise

        return deployment

    def _remove_from_gitops(
        self,
        client: PropertyEdgeNode,
        service_id: str,
        deployment: ServiceDeployment
    ):
        """Remove service manifest from GitOps repository"""
        gitops_repo_path = os.getenv('GITOPS_REPO_PATH', '/tmp/gitops-repos')
        repo_dir = Path(gitops_repo_path) / str(client.id)

        if not repo_dir.exists():
            raise ValueError("GitOps repository not found")

        repo = git.Repo(repo_dir)
        repo.remotes.origin.pull()

        # Remove manifest file
        manifest_path = repo_dir / deployment.gitops_repo_path
        if manifest_path.exists():
            manifest_path.unlink()

            # Commit and push
            repo.index.remove([str(manifest_path.relative_to(repo_dir))])

            commit_message = f"Remove {service_id} for client {client.property.name if client.property else client.id}\n\n" \
                            f"Service: {deployment.service_name}\n" \
                            f"Deployment ID: {deployment.id}"

            repo.index.commit(commit_message)
            repo.remotes.origin.push()

            logger.info(f"Removed {service_id} manifest from GitOps repo")

    def get_deployment_status(
        self,
        client_id: str,
        service_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get deployment status for a service

        Args:
            client_id: Client/PropertyEdgeNode UUID
            service_id: Service identifier

        Returns:
            Deployment status dict or None
        """
        deployment = self.db.query(ServiceDeployment).filter(
            and_(
                ServiceDeployment.client_id == client_id,
                ServiceDeployment.service_id == service_id
            )
        ).first()

        if not deployment:
            return None

        return {
            'deployment_id': str(deployment.id),
            'service_id': deployment.service_id,
            'service_name': deployment.service_name,
            'status': deployment.deployment_status,
            'deployed_at': deployment.deployed_at.isoformat() if deployment.deployed_at else None,
            'configuration': deployment.configuration,
            'git_commit_sha': deployment.git_commit_sha,
            'error_message': deployment.error_message
        }
