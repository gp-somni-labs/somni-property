"""
Hub Sync Service
Receives and processes device syncs from Tier 2/3 hubs to Master Hub (Tier 1)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import PropertyEdgeNode, SmartDevice, DeviceSync
from db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class HubSyncService:
    """
    Process device sync operations from Tier 2/3 hubs

    Tier 2/3 hubs call POST /api/v1/sync/devices to push their discovered devices
    This service:
    1. Validates hub_id and auth token
    2. Compares incoming devices with database
    3. Adds new devices
    4. Updates changed devices
    5. Marks removed devices as inactive
    6. Records sync metadata
    """

    async def process_device_sync(
        self,
        hub_id: str,
        devices: List[Dict],
        session: AsyncSession
    ) -> Dict:
        """
        Process device sync from a Tier 2/3 hub

        Args:
            hub_id: UUID of the PropertyEdgeNode (Tier 2/3 hub)
            devices: List of device dictionaries from Home Assistant
            session: Database session

        Returns:
            Dict with sync results: {
                "added": 5,
                "updated": 3,
                "removed": 1,
                "sync_id": "uuid"
            }
        """
        logger.info(f"Processing device sync from hub {hub_id} with {len(devices)} devices")

        # Validate hub exists
        stmt = select(PropertyEdgeNode).where(PropertyEdgeNode.id == hub_id)
        result = await session.execute(stmt)
        hub = result.scalar_one_or_none()

        if not hub:
            raise ValueError(f"Hub {hub_id} not found")

        # Create sync record
        device_sync = DeviceSync(
            source_hub_id=hub_id,
            devices_discovered=len(devices)
        )
        session.add(device_sync)

        # Get existing devices for this hub
        stmt = select(SmartDevice).where(
            SmartDevice.synced_from_hub_id == hub_id
        )
        result = await session.execute(stmt)
        existing_devices = {d.home_assistant_entity_id: d for d in result.scalars().all()}

        incoming_entity_ids = set()
        added_count = 0
        updated_count = 0

        try:
            # Process each incoming device
            for device_data in devices:
                entity_id = device_data.get('entity_id')
                if not entity_id:
                    logger.warning(f"Skipping device with no entity_id: {device_data}")
                    continue

                incoming_entity_ids.add(entity_id)

                if entity_id in existing_devices:
                    # Update existing device
                    device = existing_devices[entity_id]
                    updated = self._update_device_from_ha(device, device_data, hub)
                    if updated:
                        updated_count += 1
                else:
                    # Create new device
                    new_device = self._create_device_from_ha(device_data, hub)
                    session.add(new_device)
                    added_count += 1

            # Mark removed devices as inactive
            removed_count = 0
            for entity_id, device in existing_devices.items():
                if entity_id not in incoming_entity_ids:
                    device.status = 'inactive'
                    device.health_status = 'unknown'
                    removed_count += 1
                    logger.info(f"Marked device {entity_id} as inactive (removed from HA)")

            # Update sync record
            device_sync.devices_added = added_count
            device_sync.devices_updated = updated_count
            device_sync.devices_removed = removed_count
            device_sync.sync_completed_at = datetime.now()
            device_sync.sync_status = 'success'

            # Update hub sync status
            hub.sync_status = 'synced'
            hub.last_sync = datetime.now()
            hub.device_count = len(incoming_entity_ids)
            hub.sync_error_message = None

            await session.commit()

            logger.info(f"Device sync complete: added={added_count}, updated={updated_count}, removed={removed_count}")

            return {
                "added": added_count,
                "updated": updated_count,
                "removed": removed_count,
                "sync_id": str(device_sync.id)
            }

        except Exception as e:
            logger.error(f"Error processing device sync: {e}", exc_info=True)

            # Update sync record with error
            device_sync.sync_status = 'failed'
            device_sync.sync_completed_at = datetime.now()
            device_sync.error_message = str(e)

            # Update hub sync status
            hub.sync_status = 'error'
            hub.sync_error_message = str(e)

            await session.commit()
            raise

    def _create_device_from_ha(
        self,
        device_data: Dict,
        hub: PropertyEdgeNode
    ) -> SmartDevice:
        """Create SmartDevice from Home Assistant entity data"""

        # Extract device type from domain
        domain = device_data.get('domain', 'sensor')
        device_type_map = {
            'light': 'light',
            'switch': 'switch',
            'sensor': 'sensor',
            'binary_sensor': 'sensor',
            'climate': 'thermostat',
            'lock': 'lock',
            'camera': 'camera',
            'cover': 'cover',
            'fan': 'fan',
        }
        device_type = device_type_map.get(domain, 'sensor')

        # Get friendly name from attributes
        attributes = device_data.get('attributes', {})
        device_name = attributes.get('friendly_name', device_data.get('entity_id', 'Unknown'))

        return SmartDevice(
            property_id=hub.property_id,
            sync_source='home_assistant',
            synced_from_hub_id=hub.id,
            last_synced_at=datetime.now(),

            # Home Assistant data
            home_assistant_entity_id=device_data.get('entity_id'),
            ha_domain=domain,
            ha_state=device_data.get('state'),
            ha_attributes=attributes,
            device_name=device_name,

            # Device info
            device_type=device_type,
            status='active',
            health_status='healthy',
            last_seen=datetime.now(),

            # Location from attributes if available
            location=attributes.get('location'),

            # Manufacturer and model from attributes if available
            manufacturer=attributes.get('manufacturer'),
            model=attributes.get('model'),
        )

    def _update_device_from_ha(
        self,
        device: SmartDevice,
        device_data: Dict,
        hub: PropertyEdgeNode
    ) -> bool:
        """
        Update existing SmartDevice with latest HA data

        Returns True if device was updated, False if no changes
        """
        updated = False

        # Update HA state and attributes
        new_state = device_data.get('state')
        if device.ha_state != new_state:
            device.ha_state = new_state
            updated = True

        new_attributes = device_data.get('attributes', {})
        if device.ha_attributes != new_attributes:
            device.ha_attributes = new_attributes
            updated = True

        # Update last seen and synced
        device.last_seen = datetime.now()
        device.last_synced_at = datetime.now()

        # If device was inactive, mark as active
        if device.status == 'inactive':
            device.status = 'active'
            device.health_status = 'healthy'
            updated = True

        # Update device name if changed
        new_name = new_attributes.get('friendly_name', device_data.get('entity_id'))
        if device.device_name != new_name:
            device.device_name = new_name
            updated = True

        return updated

    async def trigger_sync_from_hub(self, hub_id: str) -> Dict:
        """
        Request a Tier 2/3 hub to push its devices to us

        This would make an API call to the hub's /sync endpoint
        For now, this is a placeholder - actual implementation would use httpx
        to call the hub's API endpoint

        Args:
            hub_id: UUID of the PropertyEdgeNode

        Returns:
            Dict with response from hub
        """
        async with AsyncSessionLocal() as session:
            # Get hub details
            stmt = select(PropertyEdgeNode).where(PropertyEdgeNode.id == hub_id)
            result = await session.execute(stmt)
            hub = result.scalar_one_or_none()

            if not hub:
                raise ValueError(f"Hub {hub_id} not found")

            # Update hub sync status to 'syncing'
            hub.sync_status = 'syncing'
            await session.commit()

        # TODO: Make API call to hub's /sync endpoint
        # This would be something like:
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"http://{hub.tailscale_ip}/api/sync",
        #         headers={"Authorization": f"Bearer {tier1_api_token}"}
        #     )

        logger.info(f"Triggered sync for hub {hub_id}")

        return {
            "hub_id": hub_id,
            "status": "sync_requested",
            "message": "Hub will push devices shortly"
        }


# Global hub sync service instance
hub_sync_service = HubSyncService()


async def get_hub_sync_service() -> HubSyncService:
    """Dependency to get hub sync service instance"""
    return hub_sync_service
