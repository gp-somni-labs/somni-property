"""
Somni Property Manager - Home Assistant API Client

Client for Home Assistant Supervisor and REST APIs to install components
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class HAClientResult:
    """Result of an HA API operation"""
    success: bool
    logs: str
    error: Optional[str] = None


class HomeAssistantAPIClient:
    """
    Client for Home Assistant Supervisor and REST APIs

    Used to:
    - Install SomniProperty custom component
    - Restart Home Assistant
    - Verify integration is loaded
    """

    async def test_connectivity(
        self,
        base_url: str,
        token: str
    ) -> HAClientResult:
        """
        Test connectivity to Home Assistant instance

        Args:
            base_url: HA instance URL (e.g., http://192.168.1.50:8123)
            token: Long-lived access token

        Returns:
            HAClientResult
        """
        logger.info(f"Testing connectivity to {base_url}")

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }

                async with session.get(
                    f"{base_url}/api/",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return HAClientResult(
                            success=True,
                            logs=f"[INFO] Connected to Home Assistant {data.get('version', 'unknown')}\n"
                        )
                    else:
                        return HAClientResult(
                            success=False,
                            logs=f"[ERROR] HTTP {response.status}\n",
                            error=f"HTTP {response.status}"
                        )

        except Exception as e:
            logger.exception(f"Failed to connect to {base_url}: {e}")
            return HAClientResult(
                success=False,
                logs=f"[ERROR] {str(e)}\n",
                error=str(e)
            )

    async def install_custom_component(
        self,
        base_url: str,
        token: str,
        component_name: str,
        hub_id: str,
        backend_url: str
    ) -> HAClientResult:
        """
        Install SomniProperty custom component to Home Assistant

        This is complex because we need to:
        1. Upload component files to /config/custom_components/somniproperty/
        2. Create a configuration entry for the integration

        For now, this is a placeholder that returns instructions for manual installation.

        Args:
            base_url: HA instance URL
            token: Long-lived access token
            component_name: Component name (somniproperty)
            hub_id: Hub UUID
            backend_url: SomniProperty backend URL

        Returns:
            HAClientResult
        """
        logger.info(f"Installing {component_name} component to {base_url}")

        # TODO: Implement file upload via HA file API
        # For now, return instructions for manual installation

        instructions = f"""
[INFO] SomniProperty custom component installation

To complete installation manually:

1. SSH into your Home Assistant host
2. Navigate to /config/custom_components/
3. Create directory: mkdir -p somniproperty
4. Copy integration files from apps/ha-integrations/somniproperty/ to /config/custom_components/somniproperty/
5. Restart Home Assistant
6. Add integration via UI with these details:
   - Backend URL: {backend_url}
   - Hub ID: {hub_id}

Automatic installation via API will be implemented in future update.
"""

        return HAClientResult(
            success=True,
            logs=instructions,
            error=None
        )

    async def restart_ha(
        self,
        base_url: str,
        token: str
    ) -> HAClientResult:
        """
        Restart Home Assistant via API

        Args:
            base_url: HA instance URL
            token: Long-lived access token

        Returns:
            HAClientResult
        """
        logger.info(f"Restarting Home Assistant at {base_url}")

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }

                async with session.post(
                    f"{base_url}/api/services/homeassistant/restart",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status in [200, 201]:
                        return HAClientResult(
                            success=True,
                            logs="[INFO] Home Assistant restart initiated\n"
                        )
                    else:
                        return HAClientResult(
                            success=False,
                            logs=f"[ERROR] HTTP {response.status}\n",
                            error=f"HTTP {response.status}"
                        )

        except Exception as e:
            logger.exception(f"Failed to restart HA at {base_url}: {e}")
            return HAClientResult(
                success=False,
                logs=f"[ERROR] {str(e)}\n",
                error=str(e)
            )

    async def verify_integration(
        self,
        base_url: str,
        token: str,
        integration_domain: str
    ) -> HAClientResult:
        """
        Verify integration is loaded in Home Assistant

        Args:
            base_url: HA instance URL
            token: Long-lived access token
            integration_domain: Integration domain (somniproperty)

        Returns:
            HAClientResult
        """
        logger.info(f"Verifying {integration_domain} integration is loaded")

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }

                async with session.get(
                    f"{base_url}/api/config/config_entries",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Check if our integration is in the list
                        for entry in data:
                            if entry.get("domain") == integration_domain:
                                return HAClientResult(
                                    success=True,
                                    logs=f"[INFO] {integration_domain} integration is loaded and configured\n"
                                )

                        return HAClientResult(
                            success=False,
                            logs=f"[WARN] {integration_domain} integration not found in config entries\n",
                            error=f"{integration_domain} not loaded"
                        )
                    else:
                        return HAClientResult(
                            success=False,
                            logs=f"[ERROR] HTTP {response.status}\n",
                            error=f"HTTP {response.status}"
                        )

        except Exception as e:
            logger.exception(f"Failed to verify integration: {e}")
            return HAClientResult(
                success=False,
                logs=f"[ERROR] {str(e)}\n",
                error=str(e)
            )
