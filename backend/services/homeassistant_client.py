"""
Home Assistant API Client
Monitors IoT devices and triggers maintenance work orders based on sensor states
"""

import httpx
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from core.config import settings

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """
    Home Assistant API client for IoT integration

    Connects to multiple Home Assistant instances (one per property)
    and monitors device states for maintenance triggers
    """

    def __init__(self):
        """Initialize HA client with configured instances"""
        self.instances = settings.HA_INSTANCES
        self.clients = {}

        # Create HTTP clients for each HA instance
        for instance in self.instances:
            self.clients[instance['id']] = httpx.AsyncClient(
                base_url=instance['url'],
                headers={
                    'Authorization': f"Bearer {instance['token']}",
                    'Content-Type': 'application/json'
                },
                timeout=10.0
            )

        logger.info(f"Initialized Home Assistant client with {len(self.instances)} instances")

    async def close(self):
        """Close all HTTP clients"""
        for client in self.clients.values():
            await client.aclose()

    async def get_states(self, instance_id: str) -> List[Dict[str, Any]]:
        """
        Get all entity states from a Home Assistant instance

        Args:
            instance_id: Home Assistant instance ID (e.g., 'oak-street')

        Returns:
            List of entity state objects
        """
        if instance_id not in self.clients:
            logger.error(f"Unknown Home Assistant instance: {instance_id}")
            return []

        try:
            client = self.clients[instance_id]
            response = await client.get('/api/states')
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get states from {instance_id}: {e}")
            return []

    async def get_state(self, instance_id: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get state of a specific entity

        Args:
            instance_id: Home Assistant instance ID
            entity_id: Entity ID (e.g., 'sensor.water_leak_detector')

        Returns:
            Entity state object or None
        """
        if instance_id not in self.clients:
            logger.error(f"Unknown Home Assistant instance: {instance_id}")
            return None

        try:
            client = self.clients[instance_id]
            response = await client.get(f'/api/states/{entity_id}')
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get state for {entity_id} from {instance_id}: {e}")
            return None

    async def call_service(
        self,
        instance_id: str,
        domain: str,
        service: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Call a Home Assistant service

        Args:
            instance_id: Home Assistant instance ID
            domain: Service domain (e.g., 'light', 'switch', 'notify')
            service: Service name (e.g., 'turn_on', 'turn_off')
            data: Service data/parameters

        Returns:
            True if service call succeeded
        """
        if instance_id not in self.clients:
            logger.error(f"Unknown Home Assistant instance: {instance_id}")
            return False

        try:
            client = self.clients[instance_id]
            response = await client.post(
                f'/api/services/{domain}/{service}',
                json=data or {}
            )
            response.raise_for_status()
            logger.info(f"Called service {domain}.{service} on {instance_id}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to call service {domain}.{service} on {instance_id}: {e}")
            return False

    async def send_notification(self, instance_id: str, message: str, title: Optional[str] = None):
        """
        Send a notification through Home Assistant

        Args:
            instance_id: Home Assistant instance ID
            message: Notification message
            title: Optional notification title
        """
        data = {
            'message': message
        }
        if title:
            data['title'] = title

        await self.call_service(instance_id, 'notify', 'persistent_notification', data)

    async def get_history(
        self,
        instance_id: str,
        entity_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical data for an entity

        Args:
            instance_id: Home Assistant instance ID
            entity_id: Entity ID
            start_time: Start time (default: 24 hours ago)
            end_time: End time (default: now)

        Returns:
            List of historical state records
        """
        if instance_id not in self.clients:
            logger.error(f"Unknown Home Assistant instance: {instance_id}")
            return []

        try:
            client = self.clients[instance_id]

            # Build URL with optional timestamp params
            url = f'/api/history/period'
            params = {}

            if start_time:
                url += f"/{start_time.isoformat()}"
            if entity_id:
                params['filter_entity_id'] = entity_id
            if end_time:
                params['end_time'] = end_time.isoformat()

            response = await client.get(url, params=params)
            response.raise_for_status()

            # History API returns list of lists
            history = response.json()
            return history[0] if history else []

        except httpx.HTTPError as e:
            logger.error(f"Failed to get history for {entity_id} from {instance_id}: {e}")
            return []

    async def check_maintenance_triggers(self, instance_id: str) -> List[Dict[str, Any]]:
        """
        Check for entities that should trigger maintenance work orders

        Monitors for:
        - Water leak detectors (state: 'on' or 'wet')
        - Temperature sensors (extreme values)
        - HVAC filters (needs replacement)
        - Door/window sensors (stuck open)
        - Battery levels (low battery)

        Args:
            instance_id: Home Assistant instance ID

        Returns:
            List of trigger events with entity info and reason
        """
        triggers = []
        states = await self.get_states(instance_id)

        for state in states:
            entity_id = state['entity_id']
            current_state = state['state']
            attributes = state.get('attributes', {})

            # Water leak detection
            if 'water_leak' in entity_id or 'leak_sensor' in entity_id:
                if current_state in ['on', 'wet', 'detected']:
                    triggers.append({
                        'instance_id': instance_id,
                        'entity_id': entity_id,
                        'trigger_type': 'water_leak',
                        'priority': 'emergency',
                        'category': 'plumbing',
                        'title': f"Water Leak Detected: {attributes.get('friendly_name', entity_id)}",
                        'description': f"Water leak sensor triggered at {attributes.get('friendly_name', entity_id)}",
                        'state': current_state
                    })

            # Temperature extremes
            if entity_id.startswith('sensor.') and 'temperature' in entity_id:
                try:
                    temp = float(current_state)
                    unit = attributes.get('unit_of_measurement', '°F')

                    # Extreme temperature thresholds
                    if unit == '°F':
                        if temp < 40 or temp > 95:
                            triggers.append({
                                'instance_id': instance_id,
                                'entity_id': entity_id,
                                'trigger_type': 'extreme_temperature',
                                'priority': 'high',
                                'category': 'hvac',
                                'title': f"Extreme Temperature: {temp}{unit}",
                                'description': f"Temperature sensor reading {temp}{unit} at {attributes.get('friendly_name', entity_id)}",
                                'state': current_state
                            })
                except (ValueError, TypeError):
                    pass

            # Low battery detection
            if entity_id.startswith('sensor.') and 'battery' in entity_id:
                try:
                    battery = float(current_state)
                    if battery < 15:
                        triggers.append({
                            'instance_id': instance_id,
                            'entity_id': entity_id,
                            'trigger_type': 'low_battery',
                            'priority': 'normal',
                            'category': 'electrical',
                            'title': f"Low Battery: {attributes.get('friendly_name', entity_id)}",
                            'description': f"Device battery at {battery}% - replacement needed",
                            'state': current_state
                        })
                except (ValueError, TypeError):
                    pass

            # HVAC filter replacement
            if 'filter' in entity_id and 'hvac' in entity_id:
                if current_state in ['replace', 'dirty', 'needs_replacement']:
                    triggers.append({
                        'instance_id': instance_id,
                        'entity_id': entity_id,
                        'trigger_type': 'filter_replacement',
                        'priority': 'normal',
                        'category': 'hvac',
                        'title': f"HVAC Filter Replacement Needed",
                        'description': f"HVAC filter needs replacement at {attributes.get('friendly_name', entity_id)}",
                        'state': current_state
                    })

            # Door/window stuck open
            if entity_id.startswith('binary_sensor.') and ('door' in entity_id or 'window' in entity_id):
                if current_state == 'on':  # Open state
                    # Check if it's been open for extended time (would need history check)
                    # For now, we can flag it as potential issue
                    pass

        logger.info(f"Found {len(triggers)} maintenance triggers for {instance_id}")
        return triggers

    async def get_device_info(self, instance_id: str, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device information

        Args:
            instance_id: Home Assistant instance ID
            device_id: Device ID

        Returns:
            Device information or None
        """
        if instance_id not in self.clients:
            logger.error(f"Unknown Home Assistant instance: {instance_id}")
            return None

        try:
            client = self.clients[instance_id]
            response = await client.get(f'/api/config/device_registry/get?device_id={device_id}')
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get device info for {device_id} from {instance_id}: {e}")
            return None

    async def get_areas(self, instance_id: str) -> List[Dict[str, Any]]:
        """
        Get all areas (rooms) from Home Assistant

        Args:
            instance_id: Home Assistant instance ID

        Returns:
            List of area objects
        """
        if instance_id not in self.clients:
            logger.error(f"Unknown Home Assistant instance: {instance_id}")
            return []

        try:
            client = self.clients[instance_id]
            response = await client.get('/api/config/area_registry/list')
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get areas from {instance_id}: {e}")
            return []


# Global Home Assistant client instance
ha_client = HomeAssistantClient()


async def get_ha_client() -> HomeAssistantClient:
    """Dependency to get Home Assistant client instance"""
    return ha_client
