"""
Device Monitoring Service
Monitors IoT device heartbeats, health, and automatically creates work orders for failures
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import SmartDevice, WorkOrder, PropertyEdgeNode
from services.mqtt_client import mqtt_service
from db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class DeviceMonitorService:
    """
    Monitor IoT devices for health, connectivity, and failures

    Features:
    - Track device heartbeats via MQTT
    - Update last_seen timestamps
    - Monitor battery levels and signal strength
    - Detect offline devices
    - Auto-create work orders for critical failures
    """

    def __init__(self):
        self.running = False
        self.heartbeat_timeout = 300  # 5 minutes
        self.check_interval = 60  # Check every minute
        self.device_cache: Dict[str, datetime] = {}

    async def start(self):
        """Start the device monitoring service"""
        if self.running:
            logger.warning("Device monitor service is already running")
            return

        logger.info("Starting device monitoring service")
        self.running = True

        # Register MQTT handlers for device heartbeats
        mqtt_service.register_handler("somniproperty/heartbeat", self._handle_heartbeat)
        mqtt_service.register_handler("somniproperty/state", self._handle_state_update)
        mqtt_service.register_handler("somniproperty/sensor", self._handle_sensor_reading)

        # Start background monitoring task
        asyncio.create_task(self._monitor_devices_loop())

        logger.info("Device monitoring service started successfully")

    async def stop(self):
        """Stop the device monitoring service"""
        logger.info("Stopping device monitoring service")
        self.running = False

    async def _handle_heartbeat(self, topic: str, data: dict):
        """
        Handle device heartbeat messages

        Expected message format:
        {
            "device_id": "uuid",
            "timestamp": "2024-01-15T10:30:00Z",
            "battery_level": 85,
            "signal_strength": 92
        }
        """
        try:
            device_id = data.get('device_id')
            if not device_id:
                logger.warning(f"Heartbeat message missing device_id: {data}")
                return

            # Update cache
            self.device_cache[device_id] = datetime.now()

            # Update database
            async with AsyncSessionLocal() as session:
                await self._update_device_heartbeat(
                    session,
                    device_id,
                    battery_level=data.get('battery_level'),
                    signal_strength=data.get('signal_strength')
                )
                await session.commit()

            logger.debug(f"Heartbeat received from device {device_id}")

        except Exception as e:
            logger.error(f"Error handling heartbeat: {e}", exc_info=True)

    async def _handle_state_update(self, topic: str, data: dict):
        """
        Handle device state update messages

        Expected message format:
        {
            "device_id": "uuid",
            "status": "active|inactive|failed",
            "health_status": "healthy|warning|critical",
            "firmware_version": "1.2.3"
        }
        """
        try:
            device_id = data.get('device_id')
            if not device_id:
                return

            async with AsyncSessionLocal() as session:
                # Get device from database
                stmt = select(SmartDevice).where(SmartDevice.id == device_id)
                result = await session.execute(stmt)
                device = result.scalar_one_or_none()

                if not device:
                    logger.warning(f"Received state update for unknown device: {device_id}")
                    return

                # Update device state
                if 'status' in data:
                    device.status = data['status']
                if 'health_status' in data:
                    device.health_status = data['health_status']
                if 'firmware_version' in data:
                    device.firmware_version = data['firmware_version']

                device.last_seen = datetime.now()

                await session.commit()

                # Check if device needs attention
                if data.get('status') == 'failed' or data.get('health_status') == 'critical':
                    await self._create_device_failure_work_order(session, device, data)

        except Exception as e:
            logger.error(f"Error handling state update: {e}", exc_info=True)

    async def _handle_sensor_reading(self, topic: str, data: dict):
        """
        Handle sensor reading messages

        Expected message format:
        {
            "device_id": "uuid",
            "sensor_type": "temperature|humidity|battery|etc",
            "value": 72.5,
            "unit": "°F",
            "timestamp": "2024-01-15T10:30:00Z"
        }
        """
        try:
            device_id = data.get('device_id')
            if not device_id:
                return

            # Update last seen timestamp for any sensor reading
            self.device_cache[device_id] = datetime.now()

            async with AsyncSessionLocal() as session:
                await self._update_device_heartbeat(session, device_id)

                # Handle specific sensor types
                sensor_type = data.get('sensor_type')
                value = data.get('value')

                if sensor_type == 'battery' and value is not None:
                    stmt = select(SmartDevice).where(SmartDevice.id == device_id)
                    result = await session.execute(stmt)
                    device = result.scalar_one_or_none()

                    if device:
                        device.battery_level = int(value)

                        # Create work order if battery is critically low
                        if value < 10:
                            await self._create_low_battery_work_order(session, device)

                await session.commit()

        except Exception as e:
            logger.error(f"Error handling sensor reading: {e}", exc_info=True)

    async def _update_device_heartbeat(
        self,
        session: AsyncSession,
        device_id: str,
        battery_level: Optional[int] = None,
        signal_strength: Optional[int] = None
    ):
        """Update device last_seen timestamp and optionally battery/signal"""
        stmt = select(SmartDevice).where(SmartDevice.id == device_id)
        result = await session.execute(stmt)
        device = result.scalar_one_or_none()

        if device:
            device.last_seen = datetime.now()

            if battery_level is not None:
                device.battery_level = battery_level
            if signal_strength is not None:
                device.signal_strength = signal_strength

            # Update health status based on metrics
            if device.battery_level is not None and device.battery_level < 20:
                device.health_status = 'warning'
            elif device.battery_level is not None and device.battery_level < 10:
                device.health_status = 'critical'
            elif device.signal_strength is not None and device.signal_strength < 30:
                device.health_status = 'warning'

    async def _monitor_devices_loop(self):
        """Background task to monitor devices for offline status"""
        while self.running:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_offline_devices()

            except Exception as e:
                logger.error(f"Error in device monitoring loop: {e}", exc_info=True)

    async def _check_offline_devices(self):
        """
        Check for devices that haven't sent heartbeat in timeout period

        NOTE: Only monitors devices synced from Home Assistant (sync_source='home_assistant').
        Manual devices (sync_source='manual') are legacy and not monitored.
        """
        try:
            async with AsyncSessionLocal() as session:
                # Find devices that should be active but haven't been seen recently
                # ONLY monitor synced devices (3-tier architecture)
                timeout_threshold = datetime.now() - timedelta(seconds=self.heartbeat_timeout)

                stmt = select(SmartDevice).where(
                    and_(
                        SmartDevice.sync_source == 'home_assistant',  # Only monitor synced devices
                        SmartDevice.status == 'active',
                        SmartDevice.last_seen < timeout_threshold
                    )
                )
                result = await session.execute(stmt)
                offline_devices = result.scalars().all()

                for device in offline_devices:
                    logger.warning(
                        f"Synced device {device.device_name} ({device.id}) from hub "
                        f"{device.synced_from_hub_id} appears offline - last seen {device.last_seen}"
                    )

                    # Update device status to inactive
                    device.status = 'inactive'
                    device.health_status = 'critical'

                    # Create work order for offline device
                    await self._create_offline_device_work_order(session, device)

                if offline_devices:
                    await session.commit()

        except Exception as e:
            logger.error(f"Error checking offline devices: {e}", exc_info=True)

    async def _create_device_failure_work_order(
        self,
        session: AsyncSession,
        device: SmartDevice,
        failure_data: dict
    ):
        """Create work order for device failure"""
        try:
            # Check if work order already exists for this device
            stmt = select(WorkOrder).where(
                and_(
                    WorkOrder.property_id == device.property_id,
                    WorkOrder.status.in_(['open', 'assigned', 'in_progress']),
                    WorkOrder.title.contains(device.device_name)
                )
            )
            result = await session.execute(stmt)
            existing_wo = result.scalar_one_or_none()

            if existing_wo:
                logger.info(f"Work order already exists for device {device.device_name}")
                return

            # Create new work order
            work_order = WorkOrder(
                property_id=device.property_id,
                title=f"Smart Device Failure: {device.device_name}",
                description=f"Device {device.device_name} ({device.device_type}) has failed.\n\n"
                           f"Status: {device.status}\n"
                           f"Health: {device.health_status}\n"
                           f"Location: {device.location or 'Unknown'}\n"
                           f"Manufacturer: {device.manufacturer or 'Unknown'}\n"
                           f"Model: {device.model or 'Unknown'}\n\n"
                           f"Failure details: {failure_data}",
                category='other',
                priority='high',
                status='open'
            )

            session.add(work_order)
            await session.commit()

            logger.info(f"Created work order for device failure: {device.device_name}")

        except Exception as e:
            logger.error(f"Error creating device failure work order: {e}", exc_info=True)

    async def _create_offline_device_work_order(
        self,
        session: AsyncSession,
        device: SmartDevice
    ):
        """Create work order for offline device"""
        try:
            # Check if work order already exists
            stmt = select(WorkOrder).where(
                and_(
                    WorkOrder.property_id == device.property_id,
                    WorkOrder.status.in_(['open', 'assigned']),
                    WorkOrder.title.contains(device.device_name)
                )
            )
            result = await session.execute(stmt)
            existing_wo = result.scalar_one_or_none()

            if existing_wo:
                return

            work_order = WorkOrder(
                property_id=device.property_id,
                title=f"Smart Device Offline: {device.device_name}",
                description=f"Device {device.device_name} ({device.device_type}) has not responded to heartbeat checks.\n\n"
                           f"Last seen: {device.last_seen}\n"
                           f"Location: {device.location or 'Unknown'}\n"
                           f"IP Address: {device.ip_address or 'Unknown'}\n"
                           f"MAC Address: {device.mac_address or 'Unknown'}\n\n"
                           f"Please check device connectivity and power status.",
                category='other',
                priority='normal',
                status='open'
            )

            session.add(work_order)
            await session.commit()

            logger.info(f"Created work order for offline device: {device.device_name}")

        except Exception as e:
            logger.error(f"Error creating offline device work order: {e}", exc_info=True)

    async def _create_low_battery_work_order(
        self,
        session: AsyncSession,
        device: SmartDevice
    ):
        """Create work order for low battery device"""
        try:
            # Check if work order already exists
            stmt = select(WorkOrder).where(
                and_(
                    WorkOrder.property_id == device.property_id,
                    WorkOrder.status.in_(['open', 'assigned']),
                    WorkOrder.title.contains(f"Low Battery: {device.device_name}")
                )
            )
            result = await session.execute(stmt)
            existing_wo = result.scalar_one_or_none()

            if existing_wo:
                return

            work_order = WorkOrder(
                property_id=device.property_id,
                title=f"Low Battery: {device.device_name}",
                description=f"Device {device.device_name} ({device.device_type}) has critically low battery.\n\n"
                           f"Battery Level: {device.battery_level}%\n"
                           f"Location: {device.location or 'Unknown'}\n"
                           f"Manufacturer: {device.manufacturer or 'Unknown'}\n"
                           f"Model: {device.model or 'Unknown'}\n\n"
                           f"Please replace or recharge the battery.",
                category='other',
                priority='normal',
                status='open'
            )

            session.add(work_order)
            await session.commit()

            logger.info(f"Created work order for low battery: {device.device_name}")

        except Exception as e:
            logger.error(f"Error creating low battery work order: {e}", exc_info=True)


# Global device monitor instance
device_monitor = DeviceMonitorService()


async def get_device_monitor() -> DeviceMonitorService:
    """Dependency to get device monitor instance"""
    return device_monitor
