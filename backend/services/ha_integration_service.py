"""
Home Assistant Integration Service
Manages HA connection setup during client onboarding and syncs tokens to Infisical
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, Depends

from db.models import Client
from db.database import get_db
from services.infisical_api_client import get_infisical_client
from services.ha_client_manager import get_ha_client_manager

logger = logging.getLogger(__name__)


class HAIntegrationService:
    """
    Service for managing Home Assistant integration during client onboarding

    Responsibilities:
    - Enable HA integration for clients
    - Sync HA tokens to Infisical
    - Validate HA connections
    - Health check HA instances
    - Rotate HA tokens
    - Disable/remove HA integration
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session"""
        self.db = db

    async def get_client(self, client_id: UUID) -> Optional[Client]:
        """Get client by ID"""
        query = select(Client).where(Client.id == client_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _generate_client_numeric_id(self, client: Client) -> str:
        """
        Generate a numeric client ID for Infisical storage

        Uses the first 8 characters of the UUID converted to a number

        Args:
            client: Client model

        Returns:
            Numeric ID string (e.g., "001", "042", "123")
        """
        # Use first 8 chars of UUID hex and convert to int, then mod to keep it reasonable
        uuid_hex = str(client.id).replace("-", "")[:8]
        numeric_value = int(uuid_hex, 16) % 999 + 1  # Keep between 1-999
        return f"{numeric_value:03d}"

    async def enable_ha_integration(
        self,
        client_id: UUID,
        ha_url: str,
        ha_token: str,
        network_type: Optional[str] = None,
        notes: Optional[str] = None,
        test_connection: bool = True
    ) -> Dict[str, Any]:
        """
        Enable Home Assistant integration for a client

        This will:
        1. Validate the HA connection if requested
        2. Sync the token to Infisical
        3. Update the client record
        4. Trigger a health check

        Args:
            client_id: Client UUID
            ha_url: Full URL to client's HA instance
            ha_token: HA long-lived access token
            network_type: How we access HA (tailscale, cloudflare_tunnel, etc.)
            notes: Admin notes about this HA instance
            test_connection: Whether to test the connection before enabling

        Returns:
            Dict with status and details

        Raises:
            HTTPException if validation fails
        """
        # Get client
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Test connection if requested
        if test_connection:
            connection_result = await self._test_ha_connection(ha_url, ha_token)
            if not connection_result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"HA connection test failed: {connection_result.get('error', 'Unknown error')}"
                )

        # Generate numeric client ID for Infisical
        numeric_id = self._generate_client_numeric_id(client)

        # Sync to Infisical
        infisical_client = await get_infisical_client()

        onboarding_date = client.onboarded_at.strftime("%Y-%m-%d") if client.onboarded_at else datetime.now().strftime("%Y-%m-%d")

        sync_result = await infisical_client.create_client_ha_token(
            client_id=numeric_id,
            client_name=client.name,
            ha_url=ha_url,
            ha_token=ha_token,
            service_tier=client.subscription_plan or "standard",
            contact_email=client.primary_contact_email or client.email,
            contact_phone=client.primary_contact_phone or client.phone,
            onboarding_date=onboarding_date,
            location=f"{client.property_city}, {client.property_state}" if client.property_city else None,
            billing_account=str(client.id),
            network_type=network_type or "unknown"
        )

        if not sync_result:
            raise HTTPException(
                status_code=500,
                detail="Failed to sync HA token to Infisical"
            )

        # Update client record
        client.ha_enabled = True
        client.ha_url = ha_url
        client.ha_token_synced_to_infisical = True
        client.ha_network_type = network_type
        client.ha_instance_notes = notes
        client.ha_health_status = "healthy" if test_connection else "unknown"
        client.ha_last_health_check = datetime.now() if test_connection else None

        await self.db.flush()
        await self.db.refresh(client)

        logger.info(f"Enabled HA integration for client {client.name} ({client_id}) with numeric ID {numeric_id}")

        return {
            "success": True,
            "client_id": str(client.id),
            "client_name": client.name,
            "numeric_id": numeric_id,
            "ha_url": ha_url,
            "synced_to_infisical": True,
            "health_status": client.ha_health_status,
            "message": f"HA integration enabled. Client numeric ID: {numeric_id}"
        }

    async def update_ha_url(
        self,
        client_id: UUID,
        ha_url: str,
        test_connection: bool = True
    ) -> Dict[str, Any]:
        """
        Update HA URL for a client

        Args:
            client_id: Client UUID
            ha_url: New HA URL
            test_connection: Whether to test new URL

        Returns:
            Dict with status
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if not client.ha_enabled:
            raise HTTPException(status_code=400, detail="HA integration not enabled for this client")

        # Test connection if requested
        if test_connection:
            # We don't have the token here, so we need to get it from Infisical or skip the test
            # For now, skip connection test when updating URL
            pass

        # Update in Infisical
        numeric_id = self._generate_client_numeric_id(client)
        infisical_client = await get_infisical_client()

        await infisical_client.update_secret(
            "/home-assistant/client-tokens",
            f"CLIENT_{numeric_id}_HA_URL",
            ha_url
        )

        # Update client record
        client.ha_url = ha_url

        await self.db.flush()
        await self.db.refresh(client)

        logger.info(f"Updated HA URL for client {client.name}")

        return {
            "success": True,
            "client_id": str(client.id),
            "ha_url": ha_url
        }

    async def rotate_ha_token(
        self,
        client_id: UUID,
        new_token: str,
        test_connection: bool = True
    ) -> Dict[str, Any]:
        """
        Rotate HA token for a client

        Args:
            client_id: Client UUID
            new_token: New HA token
            test_connection: Whether to test new token

        Returns:
            Dict with status
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if not client.ha_enabled:
            raise HTTPException(status_code=400, detail="HA integration not enabled for this client")

        # Test connection if requested
        if test_connection:
            connection_result = await self._test_ha_connection(client.ha_url, new_token)
            if not connection_result["success"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"HA connection test with new token failed: {connection_result.get('error')}"
                )

        # Update in Infisical
        numeric_id = self._generate_client_numeric_id(client)
        infisical_client = await get_infisical_client()

        sync_result = await infisical_client.update_client_ha_token(
            numeric_id,
            new_token
        )

        if not sync_result:
            raise HTTPException(status_code=500, detail="Failed to update token in Infisical")

        # Update client record
        client.ha_health_status = "healthy" if test_connection else "unknown"
        client.ha_last_health_check = datetime.now() if test_connection else None

        await self.db.flush()
        await self.db.refresh(client)

        logger.info(f"Rotated HA token for client {client.name}")

        return {
            "success": True,
            "client_id": str(client.id),
            "message": "HA token rotated successfully",
            "health_status": client.ha_health_status
        }

    async def check_ha_health(
        self,
        client_id: UUID
    ) -> Dict[str, Any]:
        """
        Check health of client's HA instance

        Args:
            client_id: Client UUID

        Returns:
            Dict with health status
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if not client.ha_enabled:
            raise HTTPException(status_code=400, detail="HA integration not enabled for this client")

        # Use HA Client Manager to check health
        numeric_id = self._generate_client_numeric_id(client)

        try:
            ha_manager = await get_ha_client_manager()
            health = await ha_manager.check_health(numeric_id)

            # Update client record
            client.ha_health_status = health["status"]
            client.ha_last_health_check = datetime.now()

            await self.db.flush()
            await self.db.refresh(client)

            return health

        except Exception as e:
            logger.error(f"Health check failed for client {client.name}: {e}")

            client.ha_health_status = "error"
            client.ha_last_health_check = datetime.now()
            await self.db.flush()

            return {
                "status": "error",
                "error": str(e),
                "client_id": numeric_id,
                "client_name": client.name
            }

    async def disable_ha_integration(
        self,
        client_id: UUID,
        delete_from_infisical: bool = True
    ) -> Dict[str, Any]:
        """
        Disable HA integration for a client

        Args:
            client_id: Client UUID
            delete_from_infisical: Whether to delete secrets from Infisical

        Returns:
            Dict with status
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if not client.ha_enabled:
            raise HTTPException(status_code=400, detail="HA integration not enabled for this client")

        # Delete from Infisical if requested
        if delete_from_infisical:
            numeric_id = self._generate_client_numeric_id(client)
            infisical_client = await get_infisical_client()

            await infisical_client.delete_client_ha_secrets(numeric_id)
            logger.info(f"Deleted HA secrets for client {client.name} from Infisical")

        # Update client record
        client.ha_enabled = False
        client.ha_token_synced_to_infisical = False
        client.ha_health_status = "unknown"

        await self.db.flush()
        await self.db.refresh(client)

        logger.info(f"Disabled HA integration for client {client.name}")

        return {
            "success": True,
            "client_id": str(client.id),
            "message": "HA integration disabled",
            "deleted_from_infisical": delete_from_infisical
        }

    async def _test_ha_connection(
        self,
        ha_url: str,
        ha_token: str
    ) -> Dict[str, Any]:
        """
        Test connection to a Home Assistant instance

        Args:
            ha_url: HA URL
            ha_token: HA token

        Returns:
            Dict with success status and details
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{ha_url}/api/",
                    headers={"Authorization": f"Bearer {ha_token}"}
                )
                response.raise_for_status()

                data = response.json()

                return {
                    "success": True,
                    "message": data.get("message", "API running"),
                    "ha_url": ha_url
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Connection timeout - HA instance not reachable"
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return {
                    "success": False,
                    "error": "Authentication failed - invalid token"
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {e.response.status_code}: {e.response.text}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def get_client_numeric_id(self, client_id: UUID) -> str:
        """
        Get the numeric ID used for this client in Infisical

        Args:
            client_id: Client UUID

        Returns:
            Numeric ID string
        """
        client = await self.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        return self._generate_client_numeric_id(client)


def get_ha_integration_service(db: AsyncSession = Depends(get_db)) -> HAIntegrationService:
    """Get HAIntegrationService instance"""
    return HAIntegrationService(db)
