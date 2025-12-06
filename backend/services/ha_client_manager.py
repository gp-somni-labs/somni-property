"""
Home Assistant Client Manager for MSP Multi-Client Management
Manages Home Assistant API connections for multiple paying customer instances
Uses Kubernetes secrets synced from Infisical for client token storage
"""

import os
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class HAClientConfig:
    """Configuration for a single Home Assistant client instance"""
    client_id: str
    name: str
    ha_url: str
    token: str
    service_tier: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    onboarding_date: Optional[str] = None
    location: Optional[str] = None
    billing_account: Optional[str] = None
    sla_level: Optional[str] = None
    notes: Optional[str] = None
    hardware: Optional[str] = None
    network_type: Optional[str] = None
    backup_enabled: Optional[str] = None
    monitoring: Optional[str] = None
    auto_update: Optional[str] = None


class HAClientManager:
    """
    Multi-client Home Assistant API Manager for MSP Operations

    Reads client configurations from Kubernetes secrets (mounted from Infisical)
    and manages API connections to multiple customer Home Assistant instances.

    Usage:
        manager = HAClientManager()
        await manager.initialize()

        # Get all clients
        clients = manager.get_all_clients()

        # Call a specific client's HA API
        states = await manager.get_states("001")

        # Turn on a light for a client
        await manager.call_service("001", "light", "turn_on", {"entity_id": "light.kitchen"})
    """

    def __init__(self, secrets_path: str = "/etc/secrets/ha-clients"):
        """
        Initialize the HA Client Manager

        Args:
            secrets_path: Path where Kubernetes secret is mounted
                         Default: /etc/secrets/ha-clients
                         This is where the ha-client-tokens secret should be mounted
        """
        self.secrets_path = Path(secrets_path)
        self.clients: Dict[str, HAClientConfig] = {}
        self.http_clients: Dict[str, httpx.AsyncClient] = {}
        self._initialized = False

    async def initialize(self):
        """
        Initialize the client manager by loading all client configurations
        from mounted Kubernetes secrets and creating HTTP clients
        """
        if self._initialized:
            logger.warning("HAClientManager already initialized")
            return

        logger.info(f"Initializing HAClientManager from {self.secrets_path}")

        # Load client configurations from secrets
        self._load_client_configs()

        # Create HTTP clients for each client
        for client_id, config in self.clients.items():
            self.http_clients[client_id] = httpx.AsyncClient(
                base_url=config.ha_url,
                headers={
                    "Authorization": f"Bearer {config.token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
                follow_redirects=True,
            )

        self._initialized = True
        logger.info(f"Initialized HAClientManager with {len(self.clients)} client instances")

    def _load_client_configs(self):
        """
        Load client configurations from mounted Kubernetes secret files

        Expected file structure in secrets_path:
        - CLIENT_001_TOKEN
        - CLIENT_001_NAME
        - CLIENT_001_HA_URL
        - CLIENT_001_SERVICE_TIER
        - ... (additional metadata)
        """
        if not self.secrets_path.exists():
            logger.error(f"Secrets path does not exist: {self.secrets_path}")
            return

        # Find all client IDs by looking for TOKEN files
        client_ids = set()
        for file_path in self.secrets_path.iterdir():
            if file_path.is_file() and "_TOKEN" in file_path.name:
                # Extract client ID from CLIENT_001_TOKEN -> 001
                parts = file_path.name.split("_")
                if len(parts) >= 2 and parts[0] == "CLIENT":
                    client_ids.add(parts[1])

        logger.info(f"Found {len(client_ids)} client IDs: {sorted(client_ids)}")

        # Load configuration for each client
        for client_id in sorted(client_ids):
            config = self._load_single_client_config(client_id)
            if config:
                self.clients[client_id] = config
                logger.info(f"Loaded config for client {client_id}: {config.name}")
            else:
                logger.warning(f"Failed to load config for client {client_id}")

    def _load_single_client_config(self, client_id: str) -> Optional[HAClientConfig]:
        """
        Load configuration for a single client from secret files

        Args:
            client_id: Client ID (e.g., "001")

        Returns:
            HAClientConfig object or None if required fields are missing
        """
        def read_secret(field_name: str) -> Optional[str]:
            """Read a secret file and return its contents"""
            file_path = self.secrets_path / f"CLIENT_{client_id}_{field_name}"
            if file_path.exists():
                try:
                    return file_path.read_text().strip()
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
            return None

        # Required fields
        token = read_secret("TOKEN")
        name = read_secret("NAME")
        ha_url = read_secret("HA_URL")

        if not token or not name or not ha_url:
            logger.error(f"Missing required fields for client {client_id}")
            logger.error(f"  TOKEN: {'✓' if token else '✗'}")
            logger.error(f"  NAME: {'✓' if name else '✗'}")
            logger.error(f"  HA_URL: {'✓' if ha_url else '✗'}")
            return None

        # Optional metadata fields
        return HAClientConfig(
            client_id=client_id,
            name=name,
            ha_url=ha_url,
            token=token,
            service_tier=read_secret("SERVICE_TIER"),
            contact_email=read_secret("CONTACT_EMAIL"),
            contact_phone=read_secret("CONTACT_PHONE"),
            onboarding_date=read_secret("ONBOARDING_DATE"),
            location=read_secret("LOCATION"),
            billing_account=read_secret("BILLING_ACCOUNT"),
            sla_level=read_secret("SLA_LEVEL"),
            notes=read_secret("NOTES"),
            hardware=read_secret("HARDWARE"),
            network_type=read_secret("NETWORK_TYPE"),
            backup_enabled=read_secret("BACKUP_ENABLED"),
            monitoring=read_secret("MONITORING"),
            auto_update=read_secret("AUTO_UPDATE"),
        )

    async def close(self):
        """Close all HTTP client connections"""
        for client in self.http_clients.values():
            await client.aclose()
        logger.info("Closed all HA client connections")

    # ============================================================================
    # Client Information Methods
    # ============================================================================

    def get_all_clients(self) -> List[HAClientConfig]:
        """
        Get list of all configured client instances

        Returns:
            List of HAClientConfig objects
        """
        return list(self.clients.values())

    def get_client_config(self, client_id: str) -> Optional[HAClientConfig]:
        """
        Get configuration for a specific client

        Args:
            client_id: Client ID (e.g., "001")

        Returns:
            HAClientConfig object or None if client not found
        """
        return self.clients.get(client_id)

    def get_client_ids(self) -> List[str]:
        """Get list of all client IDs"""
        return sorted(self.clients.keys())

    # ============================================================================
    # Home Assistant API Methods
    # ============================================================================

    async def get_states(self, client_id: str) -> List[Dict[str, Any]]:
        """
        Get all entity states from a client's Home Assistant instance

        Args:
            client_id: Client ID (e.g., "001")

        Returns:
            List of entity state objects, empty list on error
        """
        if client_id not in self.http_clients:
            logger.error(f"Unknown client ID: {client_id}")
            return []

        try:
            client = self.http_clients[client_id]
            response = await client.get("/api/states")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get states for client {client_id}: {e}")
            return []

    async def get_state(self, client_id: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get state of a specific entity

        Args:
            client_id: Client ID
            entity_id: Entity ID (e.g., "light.kitchen")

        Returns:
            Entity state object or None on error
        """
        if client_id not in self.http_clients:
            logger.error(f"Unknown client ID: {client_id}")
            return None

        try:
            client = self.http_clients[client_id]
            response = await client.get(f"/api/states/{entity_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get state for {entity_id} from client {client_id}: {e}")
            return None

    async def call_service(
        self,
        client_id: str,
        domain: str,
        service: str,
        service_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Call a Home Assistant service

        Args:
            client_id: Client ID
            domain: Service domain (e.g., "light", "switch", "climate")
            service: Service name (e.g., "turn_on", "turn_off", "set_temperature")
            service_data: Optional service data/parameters

        Returns:
            True if service call succeeded, False otherwise

        Example:
            # Turn on kitchen light
            await manager.call_service("001", "light", "turn_on",
                                      {"entity_id": "light.kitchen"})

            # Set thermostat
            await manager.call_service("002", "climate", "set_temperature",
                                      {"entity_id": "climate.main", "temperature": 72})
        """
        if client_id not in self.http_clients:
            logger.error(f"Unknown client ID: {client_id}")
            return False

        try:
            client = self.http_clients[client_id]
            response = await client.post(
                f"/api/services/{domain}/{service}",
                json=service_data or {}
            )
            response.raise_for_status()
            logger.info(f"Called service {domain}.{service} for client {client_id}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to call service {domain}.{service} for client {client_id}: {e}")
            return False

    async def send_notification(
        self,
        client_id: str,
        message: str,
        title: Optional[str] = None,
        target: Optional[str] = None
    ):
        """
        Send a notification through Home Assistant

        Args:
            client_id: Client ID
            message: Notification message
            title: Optional notification title
            target: Optional notification target (specific notify service)
        """
        data = {"message": message}
        if title:
            data["title"] = title

        service = target or "persistent_notification"
        await self.call_service(client_id, "notify", service, data)

    async def get_history(
        self,
        client_id: str,
        entity_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical data for an entity

        Args:
            client_id: Client ID
            entity_id: Entity ID
            start_time: Start time (default: 24 hours ago)
            end_time: End time (default: now)

        Returns:
            List of historical state records
        """
        if client_id not in self.http_clients:
            logger.error(f"Unknown client ID: {client_id}")
            return []

        try:
            client = self.http_clients[client_id]

            url = "/api/history/period"
            params = {}

            if start_time:
                url += f"/{start_time.isoformat()}"
            if entity_id:
                params["filter_entity_id"] = entity_id
            if end_time:
                params["end_time"] = end_time.isoformat()

            response = await client.get(url, params=params)
            response.raise_for_status()

            history = response.json()
            return history[0] if history else []
        except httpx.HTTPError as e:
            logger.error(f"Failed to get history for {entity_id} from client {client_id}: {e}")
            return []

    async def get_config(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get Home Assistant configuration

        Args:
            client_id: Client ID

        Returns:
            Configuration dictionary or None on error
        """
        if client_id not in self.http_clients:
            logger.error(f"Unknown client ID: {client_id}")
            return None

        try:
            client = self.http_clients[client_id]
            response = await client.get("/api/config")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get config for client {client_id}: {e}")
            return None

    async def get_services(self, client_id: str) -> Optional[Dict[str, Any]]:
        """
        Get available services in Home Assistant

        Args:
            client_id: Client ID

        Returns:
            Services dictionary or None on error
        """
        if client_id not in self.http_clients:
            logger.error(f"Unknown client ID: {client_id}")
            return None

        try:
            client = self.http_clients[client_id]
            response = await client.get("/api/services")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to get services for client {client_id}: {e}")
            return None

    # ============================================================================
    # Health & Monitoring
    # ============================================================================

    async def check_health(self, client_id: str) -> Dict[str, Any]:
        """
        Check health of a client's Home Assistant instance

        Args:
            client_id: Client ID

        Returns:
            Dictionary with health status and metadata
        """
        config = self.clients.get(client_id)
        if not config:
            return {
                "client_id": client_id,
                "status": "unknown",
                "error": "Client not found"
            }

        try:
            client = self.http_clients[client_id]
            start_time = datetime.now()
            response = await client.get("/api/")
            elapsed = (datetime.now() - start_time).total_seconds()

            response.raise_for_status()
            data = response.json()

            return {
                "client_id": client_id,
                "client_name": config.name,
                "status": "healthy",
                "message": data.get("message", "API running"),
                "response_time_seconds": elapsed,
                "timestamp": datetime.now().isoformat(),
                "ha_url": config.ha_url,
                "service_tier": config.service_tier,
            }
        except httpx.TimeoutException:
            return {
                "client_id": client_id,
                "client_name": config.name,
                "status": "timeout",
                "error": "Request timed out",
                "timestamp": datetime.now().isoformat(),
            }
        except httpx.HTTPError as e:
            return {
                "client_id": client_id,
                "client_name": config.name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def check_all_clients_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Check health of all client Home Assistant instances

        Returns:
            Dictionary mapping client IDs to health status
        """
        results = {}
        for client_id in self.clients.keys():
            results[client_id] = await self.check_health(client_id)
        return results

    # ============================================================================
    # Convenience Methods for Common Operations
    # ============================================================================

    async def get_all_clients_states(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get states from all client instances

        Returns:
            Dictionary mapping client IDs to their state lists
        """
        results = {}
        for client_id in self.clients.keys():
            results[client_id] = await self.get_states(client_id)
        return results

    async def turn_on_light(self, client_id: str, entity_id: str) -> bool:
        """Convenience method to turn on a light"""
        return await self.call_service(client_id, "light", "turn_on", {"entity_id": entity_id})

    async def turn_off_light(self, client_id: str, entity_id: str) -> bool:
        """Convenience method to turn off a light"""
        return await self.call_service(client_id, "light", "turn_off", {"entity_id": entity_id})

    async def set_temperature(self, client_id: str, entity_id: str, temperature: float) -> bool:
        """Convenience method to set thermostat temperature"""
        return await self.call_service(
            client_id,
            "climate",
            "set_temperature",
            {"entity_id": entity_id, "temperature": temperature}
        )


# Global instance (singleton pattern)
_ha_client_manager: Optional[HAClientManager] = None


async def get_ha_client_manager() -> HAClientManager:
    """
    Get or create the global HAClientManager instance

    Usage in FastAPI endpoints:
        @router.get("/clients")
        async def get_clients(manager: HAClientManager = Depends(get_ha_client_manager)):
            return manager.get_all_clients()
    """
    global _ha_client_manager

    if _ha_client_manager is None:
        _ha_client_manager = HAClientManager()
        await _ha_client_manager.initialize()

    return _ha_client_manager


async def initialize_ha_client_manager():
    """Initialize the global HA client manager (call at app startup)"""
    await get_ha_client_manager()


async def shutdown_ha_client_manager():
    """Shutdown the global HA client manager (call at app shutdown)"""
    global _ha_client_manager
    if _ha_client_manager:
        await _ha_client_manager.close()
        _ha_client_manager = None
