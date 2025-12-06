"""
Infisical API Client for Programmatic Secret Management
Allows SomniProperty to automatically create/update/delete client HA tokens in Infisical
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class InfisicalAPIClient:
    """
    Client for Infisical API to programmatically manage secrets

    Used to automatically sync Home Assistant client tokens to Infisical
    when clients are onboarded in SomniProperty.

    Environment Variables Required:
    - INFISICAL_API_URL: Infisical API endpoint (http://infisical.secrets.svc.cluster.local:8080/api)
    - INFISICAL_CLIENT_ID: Service account client ID
    - INFISICAL_CLIENT_SECRET: Service account client secret
    - INFISICAL_PROJECT_ID: Project/Workspace ID (UUID)
    - INFISICAL_ENV_SLUG: Environment slug (prod)
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        project_id: Optional[str] = None,
        env_slug: Optional[str] = None
    ):
        """
        Initialize Infisical API client

        If parameters not provided, reads from environment variables
        """
        self.api_url = api_url or os.getenv("INFISICAL_API_URL", "http://infisical.secrets.svc.cluster.local:8080/api")
        self.client_id = client_id or os.getenv("INFISICAL_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("INFISICAL_CLIENT_SECRET")
        self.project_id = project_id or os.getenv("INFISICAL_PROJECT_ID", "1ea85e90-22db-4313-b6c4-d6fa34f8d801")
        self.env_slug = env_slug or os.getenv("INFISICAL_ENV_SLUG", "prod")

        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        self.http_client = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=30.0
        )

    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()

    async def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return  # Token still valid

        # Authenticate to get new token
        await self._authenticate()

    async def _authenticate(self):
        """
        Authenticate with Infisical using service account credentials

        Uses Universal Auth method
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Infisical client_id and client_secret are required")

        try:
            response = await self.http_client.post(
                "/v1/auth/universal-auth/login",
                json={
                    "clientId": self.client_id,
                    "clientSecret": self.client_secret
                }
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data["accessToken"]
            # Token typically expires in 1 hour, refresh 5 minutes before
            # For now, we'll just re-auth on each request if needed

            logger.info("Successfully authenticated with Infisical")

        except httpx.HTTPError as e:
            logger.error(f"Failed to authenticate with Infisical: {e}")
            raise

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authorization token"""
        if not self.access_token:
            raise ValueError("Not authenticated. Call _ensure_authenticated() first")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def create_secret(
        self,
        secret_path: str,
        key: str,
        value: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a secret in Infisical

        Args:
            secret_path: Path in Infisical (e.g., "/home-assistant/client-tokens")
            key: Secret key (e.g., "CLIENT_001_TOKEN")
            value: Secret value
            comment: Optional comment/description

        Returns:
            Created secret data
        """
        await self._ensure_authenticated()

        try:
            response = await self.http_client.post(
                "/v3/secrets/raw",
                headers=self._get_headers(),
                json={
                    "workspaceId": self.project_id,
                    "environment": self.env_slug,
                    "secretPath": secret_path,
                    "secretKey": key,
                    "secretValue": value,
                    "secretComment": comment or ""
                }
            )
            response.raise_for_status()

            logger.info(f"Created secret {key} at {secret_path}")
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                # Secret already exists, update instead
                logger.warning(f"Secret {key} already exists, updating instead")
                return await self.update_secret(secret_path, key, value, comment)
            else:
                logger.error(f"Failed to create secret {key}: {e}")
                raise

    async def update_secret(
        self,
        secret_path: str,
        key: str,
        value: str,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing secret in Infisical

        Args:
            secret_path: Path in Infisical
            key: Secret key
            value: New secret value
            comment: Optional comment

        Returns:
            Updated secret data
        """
        await self._ensure_authenticated()

        try:
            response = await self.http_client.patch(
                "/v3/secrets/raw",
                headers=self._get_headers(),
                json={
                    "workspaceId": self.project_id,
                    "environment": self.env_slug,
                    "secretPath": secret_path,
                    "secretKey": key,
                    "secretValue": value,
                    "secretComment": comment or ""
                }
            )
            response.raise_for_status()

            logger.info(f"Updated secret {key} at {secret_path}")
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to update secret {key}: {e}")
            raise

    async def delete_secret(
        self,
        secret_path: str,
        key: str
    ) -> bool:
        """
        Delete a secret from Infisical

        Args:
            secret_path: Path in Infisical
            key: Secret key to delete

        Returns:
            True if successful
        """
        await self._ensure_authenticated()

        try:
            response = await self.http_client.delete(
                "/v3/secrets/raw",
                headers=self._get_headers(),
                params={
                    "workspaceId": self.project_id,
                    "environment": self.env_slug,
                    "secretPath": secret_path,
                    "secretKey": key
                }
            )
            response.raise_for_status()

            logger.info(f"Deleted secret {key} from {secret_path}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to delete secret {key}: {e}")
            return False

    async def get_secret(
        self,
        secret_path: str,
        key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a secret from Infisical

        Args:
            secret_path: Path in Infisical
            key: Secret key

        Returns:
            Secret data or None if not found
        """
        await self._ensure_authenticated()

        try:
            response = await self.http_client.get(
                "/v3/secrets/raw",
                headers=self._get_headers(),
                params={
                    "workspaceId": self.project_id,
                    "environment": self.env_slug,
                    "secretPath": secret_path,
                    "secretKey": key
                }
            )
            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get secret {key}: {e}")
            raise

    async def list_secrets(
        self,
        secret_path: str
    ) -> List[Dict[str, Any]]:
        """
        List all secrets at a path

        Args:
            secret_path: Path in Infisical

        Returns:
            List of secrets (without values for security)
        """
        await self._ensure_authenticated()

        try:
            response = await self.http_client.get(
                "/v3/secrets",
                headers=self._get_headers(),
                params={
                    "workspaceId": self.project_id,
                    "environment": self.env_slug,
                    "secretPath": secret_path
                }
            )
            response.raise_for_status()

            return response.json().get("secrets", [])

        except httpx.HTTPError as e:
            logger.error(f"Failed to list secrets at {secret_path}: {e}")
            return []

    async def create_client_ha_token(
        self,
        client_id: str,
        client_name: str,
        ha_url: str,
        ha_token: str,
        service_tier: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        onboarding_date: Optional[str] = None,
        **additional_metadata
    ) -> bool:
        """
        Create all secrets for a Home Assistant client

        This is a convenience method that creates all the standard secrets
        for a client in one call.

        Args:
            client_id: Client ID (e.g., "001", "002")
            client_name: Client name
            ha_url: Home Assistant URL
            ha_token: Home Assistant long-lived access token
            service_tier: Service tier (premium, standard, basic)
            contact_email: Contact email
            contact_phone: Contact phone
            onboarding_date: Onboarding date (YYYY-MM-DD)
            **additional_metadata: Any additional metadata fields

        Returns:
            True if successful
        """
        secret_path = "/home-assistant/client-tokens"

        # Format client_id to ensure 3-digit format
        if client_id.isdigit():
            formatted_id = f"{int(client_id):03d}"
        else:
            formatted_id = client_id

        try:
            # Create required secrets
            await self.create_secret(
                secret_path,
                f"CLIENT_{formatted_id}_TOKEN",
                ha_token,
                comment=f"HA token for {client_name}"
            )

            await self.create_secret(
                secret_path,
                f"CLIENT_{formatted_id}_NAME",
                client_name,
                comment=f"Client name"
            )

            await self.create_secret(
                secret_path,
                f"CLIENT_{formatted_id}_HA_URL",
                ha_url,
                comment=f"HA instance URL"
            )

            # Create optional metadata secrets
            if service_tier:
                await self.create_secret(
                    secret_path,
                    f"CLIENT_{formatted_id}_SERVICE_TIER",
                    service_tier
                )

            if contact_email:
                await self.create_secret(
                    secret_path,
                    f"CLIENT_{formatted_id}_CONTACT_EMAIL",
                    contact_email
                )

            if contact_phone:
                await self.create_secret(
                    secret_path,
                    f"CLIENT_{formatted_id}_CONTACT_PHONE",
                    contact_phone
                )

            if onboarding_date:
                await self.create_secret(
                    secret_path,
                    f"CLIENT_{formatted_id}_ONBOARDING_DATE",
                    onboarding_date
                )

            # Create any additional metadata
            for key, value in additional_metadata.items():
                await self.create_secret(
                    secret_path,
                    f"CLIENT_{formatted_id}_{key.upper()}",
                    str(value)
                )

            logger.info(f"Successfully created all HA secrets for client {formatted_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create HA secrets for client {formatted_id}: {e}")
            return False

    async def update_client_ha_token(
        self,
        client_id: str,
        ha_token: str
    ) -> bool:
        """
        Update just the HA token for a client (for token rotation)

        Args:
            client_id: Client ID
            ha_token: New HA token

        Returns:
            True if successful
        """
        secret_path = "/home-assistant/client-tokens"

        if client_id.isdigit():
            formatted_id = f"{int(client_id):03d}"
        else:
            formatted_id = client_id

        try:
            await self.update_secret(
                secret_path,
                f"CLIENT_{formatted_id}_TOKEN",
                ha_token,
                comment="Token rotated"
            )

            logger.info(f"Updated HA token for client {formatted_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update HA token for client {formatted_id}: {e}")
            return False

    async def delete_client_ha_secrets(
        self,
        client_id: str
    ) -> bool:
        """
        Delete all secrets for a client (for offboarding)

        Args:
            client_id: Client ID

        Returns:
            True if successful
        """
        secret_path = "/home-assistant/client-tokens"

        if client_id.isdigit():
            formatted_id = f"{int(client_id):03d}"
        else:
            formatted_id = client_id

        try:
            # List all secrets to find ones for this client
            all_secrets = await self.list_secrets(secret_path)

            # Find secrets for this client
            client_secrets = [
                s for s in all_secrets
                if s.get("secretKey", "").startswith(f"CLIENT_{formatted_id}_")
            ]

            # Delete each secret
            for secret in client_secrets:
                await self.delete_secret(secret_path, secret["secretKey"])

            logger.info(f"Deleted {len(client_secrets)} secrets for client {formatted_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete HA secrets for client {formatted_id}: {e}")
            return False


# Global instance
_infisical_client: Optional[InfisicalAPIClient] = None


async def get_infisical_client() -> InfisicalAPIClient:
    """Get or create global Infisical API client"""
    global _infisical_client

    if _infisical_client is None:
        _infisical_client = InfisicalAPIClient()

    return _infisical_client


async def close_infisical_client():
    """Close global Infisical API client"""
    global _infisical_client

    if _infisical_client:
        await _infisical_client.close()
        _infisical_client = None
