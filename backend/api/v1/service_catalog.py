"""
Service Catalog API - One-click service deployment endpoints
Manages service catalog browsing and deployment to Tier 1/2 K3s clusters
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from db.database import get_db
from services.service_catalog_service import ServiceCatalogService
from db.models import PropertyEdgeNode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["service-catalog"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ServiceDefinition(BaseModel):
    """Service definition from catalog"""
    id: str
    name: str
    category: str
    description: str
    tiers: List[str]
    default_namespace: str
    ingress_required: bool
    default_port: int
    icon_url: Optional[str] = None
    documentation_url: Optional[str] = None
    resource_requirements: Dict[str, str]
    requires_storage: Optional[bool] = False
    storage_size: Optional[str] = None
    requires_gpu: Optional[bool] = False
    requires_usb_device: Optional[bool] = False


class ServiceDeploymentRequest(BaseModel):
    """Request to deploy a service"""
    service_id: str = Field(..., description="Service ID from catalog")
    namespace: Optional[str] = Field(None, description="Override default namespace")
    ingress_hostname: Optional[str] = Field(None, description="Custom ingress hostname")
    client_domain: str = Field(..., description="Client's domain for ingress")
    storage_class: Optional[str] = Field("local-path", description="Storage class for PVCs")

    # Service-specific configuration
    configuration: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional service configuration")


class ServiceDeploymentResponse(BaseModel):
    """Response from service deployment"""
    deployment_id: str
    service_id: str
    service_name: str
    status: str
    deployed_at: Optional[datetime] = None
    git_commit_sha: Optional[str] = None
    configuration: Dict[str, Any]
    error_message: Optional[str] = None


class InstalledServiceResponse(BaseModel):
    """Installed service information"""
    deployment_id: str
    service_id: str
    service_name: str
    status: str
    deployed_at: Optional[datetime] = None
    configuration: Dict[str, Any]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/clients/{client_id}/services/available", response_model=List[ServiceDefinition])
async def get_available_services(
    client_id: str,
    db: Session = Depends(get_db)
):
    """
    Get available services for a client based on their tier

    Returns list of services from the catalog that are available for the client's tier.
    """
    try:
        # Get client to determine tier
        client = db.query(PropertyEdgeNode).filter(PropertyEdgeNode.id == client_id).first()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {client_id} not found"
            )

        # Determine tier from hub_type
        tier_mapping = {
            'tier_0_standalone': 'tier_0',
            'tier_2_property': 'tier_2',
            'tier_3_residential': 'tier_2'  # Tier 3 gets tier_2 services
        }
        tier = tier_mapping.get(client.hub_type, 'tier_2')

        # Get available services
        service_catalog = ServiceCatalogService(db)
        services = service_catalog.get_available_services(tier)

        logger.info(f"Client {client_id} ({tier}) has {len(services)} available services")
        return services

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get available services for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve available services: {str(e)}"
        )


@router.get("/clients/{client_id}/services/installed", response_model=List[InstalledServiceResponse])
async def get_installed_services(
    client_id: str,
    db: Session = Depends(get_db)
):
    """
    Get list of services installed for a client

    Returns all deployed services and their current status.
    """
    try:
        service_catalog = ServiceCatalogService(db)
        deployments = service_catalog.get_installed_services(client_id)

        installed_services = [
            InstalledServiceResponse(
                deployment_id=str(deployment.id),
                service_id=deployment.service_id,
                service_name=deployment.service_name,
                status=deployment.deployment_status,
                deployed_at=deployment.deployed_at,
                configuration=deployment.configuration or {}
            )
            for deployment in deployments
        ]

        logger.info(f"Client {client_id} has {len(installed_services)} installed services")
        return installed_services

    except Exception as e:
        logger.error(f"Failed to get installed services for client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve installed services: {str(e)}"
        )


@router.post("/clients/{client_id}/services/{service_id}/deploy", response_model=ServiceDeploymentResponse)
async def deploy_service(
    client_id: str,
    service_id: str,
    request: ServiceDeploymentRequest,
    db: Session = Depends(get_db)
):
    """
    Deploy a service to client's K3s cluster via GitOps

    Generates K8s manifest from template and commits to client's GitOps repository.
    FluxCD will automatically deploy the service to the cluster.
    """
    try:
        # Validate service_id matches path parameter
        if request.service_id != service_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service_id in body must match service_id in path"
            )

        service_catalog = ServiceCatalogService(db)

        # Check if service exists in catalog
        service = service_catalog.get_service_by_id(service_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service {service_id} not found in catalog"
            )

        # Check if already installed
        if service_catalog.is_service_installed(client_id, service_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Service {service_id} is already installed for this client"
            )

        # Prepare deployment parameters
        params = {
            'client_id': client_id,
            'client_domain': request.client_domain,
            'storage_class': request.storage_class,
            **request.configuration
        }

        # Add optional overrides
        if request.namespace:
            params['namespace'] = request.namespace
        if request.ingress_hostname:
            params['ingress_hostname'] = request.ingress_hostname

        # Deploy service
        deployment = service_catalog.deploy_service(
            client_id=client_id,
            service_id=service_id,
            params=params
        )

        logger.info(f"Successfully deployed {service_id} to client {client_id}")

        return ServiceDeploymentResponse(
            deployment_id=str(deployment.id),
            service_id=deployment.service_id,
            service_name=deployment.service_name,
            status=deployment.deployment_status,
            deployed_at=deployment.deployed_at,
            git_commit_sha=deployment.git_commit_sha,
            configuration=deployment.configuration or {},
            error_message=deployment.error_message
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error deploying {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to deploy {service_id} to client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy service: {str(e)}"
        )


@router.delete("/clients/{client_id}/services/{service_id}", response_model=ServiceDeploymentResponse)
async def remove_service(
    client_id: str,
    service_id: str,
    db: Session = Depends(get_db)
):
    """
    Remove a service from client's K3s cluster

    Removes the manifest from GitOps repository. FluxCD will automatically
    remove the service from the cluster.
    """
    try:
        service_catalog = ServiceCatalogService(db)

        # Remove service
        deployment = service_catalog.remove_service(
            client_id=client_id,
            service_id=service_id
        )

        logger.info(f"Successfully removed {service_id} from client {client_id}")

        return ServiceDeploymentResponse(
            deployment_id=str(deployment.id),
            service_id=deployment.service_id,
            service_name=deployment.service_name,
            status=deployment.deployment_status,
            deployed_at=deployment.deployed_at,
            git_commit_sha=deployment.git_commit_sha,
            configuration=deployment.configuration or {},
            error_message=deployment.error_message
        )

    except ValueError as e:
        logger.warning(f"Validation error removing {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to remove {service_id} from client {client_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove service: {str(e)}"
        )


@router.get("/clients/{client_id}/services/{service_id}/status", response_model=ServiceDeploymentResponse)
async def get_service_status(
    client_id: str,
    service_id: str,
    db: Session = Depends(get_db)
):
    """
    Get deployment status for a specific service

    Returns current deployment status, configuration, and any errors.
    For real-time Kubernetes status, this could be enhanced to query
    the cluster directly via kubectl or K8s API.
    """
    try:
        service_catalog = ServiceCatalogService(db)
        status_info = service_catalog.get_deployment_status(client_id, service_id)

        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service {service_id} not found for client {client_id}"
            )

        return ServiceDeploymentResponse(**status_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for {service_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve service status: {str(e)}"
        )


@router.get("/services/catalog", response_model=Dict[str, Any])
async def get_service_catalog(db: Session = Depends(get_db)):
    """
    Get the complete service catalog

    Returns all available services and categories.
    Useful for building UI catalog views.
    """
    try:
        service_catalog = ServiceCatalogService(db)
        catalog = service_catalog.load_service_catalog()

        logger.info("Retrieved full service catalog")
        return catalog

    except Exception as e:
        logger.error(f"Failed to get service catalog: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve service catalog: {str(e)}"
        )
