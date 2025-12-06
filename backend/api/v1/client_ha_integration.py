"""
Client Home Assistant Integration API
Manage HA connections for SomniProperty clients during onboarding
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from services.ha_integration_service import get_ha_integration_service, HAIntegrationService

router = APIRouter(prefix="/clients/{client_id}/ha-integration", tags=["Client HA Integration"])


# ============================================================================
# Pydantic Models
# ============================================================================

class EnableHAIntegrationRequest(BaseModel):
    """Request to enable HA integration"""
    ha_url: str = Field(..., description="Full URL to client's HA instance (https://ha.client.com or http://192.168.1.100:8123)")
    ha_token: str = Field(..., description="Home Assistant long-lived access token")
    network_type: Optional[str] = Field(None, description="Network access type: tailscale, cloudflare_tunnel, vpn, public_ip, local_network")
    notes: Optional[str] = Field(None, description="Admin notes about this HA instance")
    test_connection: bool = Field(True, description="Test connection before enabling")


class UpdateHAURLRequest(BaseModel):
    """Request to update HA URL"""
    ha_url: str = Field(..., description="New HA URL")
    test_connection: bool = Field(True, description="Test new URL before updating")


class RotateHATokenRequest(BaseModel):
    """Request to rotate HA token"""
    new_token: str = Field(..., description="New HA long-lived access token")
    test_connection: bool = Field(True, description="Test new token before rotating")


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/enable")
async def enable_ha_integration(
    client_id: UUID,
    request: EnableHAIntegrationRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Enable Home Assistant integration for a client

    This will:
    1. Test the HA connection (if requested)
    2. Sync the HA token to Infisical with client metadata
    3. Update the client record in the database
    4. Make the client's HA instance accessible via HAClientManager

    Use this during client onboarding when reaching the deployment stage.

    Example:
        ```
        POST /api/v1/clients/{client_id}/ha-integration/enable
        {
            "ha_url": "https://ha.smithfamily.com",
            "ha_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "network_type": "tailscale",
            "notes": "Accessing via Tailscale VPN",
            "test_connection": true
        }
        ```
    """
    service = HAIntegrationService(db)
    result = await service.enable_ha_integration(
        client_id=client_id,
        ha_url=request.ha_url,
        ha_token=request.ha_token,
        network_type=request.network_type,
        notes=request.notes,
        test_connection=request.test_connection
    )

    return result


@router.put("/url")
async def update_ha_url(
    client_id: UUID,
    request: UpdateHAURLRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Update HA URL for a client

    Use this when:
    - Client changes ISP and gets new IP
    - Migrating from local IP to domain name
    - Switching from Tailscale to Cloudflare Tunnel
    """
    service = HAIntegrationService(db)
    result = await service.update_ha_url(
        client_id=client_id,
        ha_url=request.ha_url,
        test_connection=request.test_connection
    )

    return result


@router.post("/rotate-token")
async def rotate_ha_token(
    client_id: UUID,
    request: RotateHATokenRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Rotate HA token for a client

    Use this for:
    - Annual token rotation (security best practice)
    - Token compromised
    - Client personnel changes

    Process:
    1. Create new token in client's HA
    2. Call this endpoint with new token
    3. Service updates token in Infisical
    4. Revoke old token in client's HA
    """
    service = HAIntegrationService(db)
    result = await service.rotate_ha_token(
        client_id=client_id,
        new_token=request.new_token,
        test_connection=request.test_connection
    )

    return result


@router.get("/health")
async def check_ha_health(
    client_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Check health of client's Home Assistant instance

    Tests connectivity and updates health status in database
    """
    service = HAIntegrationService(db)
    result = await service.check_ha_health(client_id)
    return result


@router.get("/numeric-id")
async def get_numeric_id(
    client_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get the numeric client ID used in Infisical for this client

    Useful for debugging or manual Infisical operations
    """
    service = HAIntegrationService(db)
    numeric_id = await service.get_client_numeric_id(client_id)

    return {
        "client_id": str(client_id),
        "numeric_id": numeric_id,
        "infisical_prefix": f"CLIENT_{numeric_id}_"
    }


@router.delete("/disable")
async def disable_ha_integration(
    client_id: UUID,
    delete_from_infisical: bool = True,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Disable HA integration for a client

    Use this when:
    - Client offboarding
    - Temporarily disabling HA management
    - Client switches to different platform

    Args:
        delete_from_infisical: If True, deletes secrets from Infisical (default)
                              If False, marks as disabled but keeps secrets for potential re-enablement
    """
    service = HAIntegrationService(db)
    result = await service.disable_ha_integration(
        client_id=client_id,
        delete_from_infisical=delete_from_infisical
    )

    return result
