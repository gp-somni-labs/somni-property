"""
MQTT Message Persistence Service
Handles storing MQTT messages in the database
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from db.models import IoTDevice, SensorReading, AccessLog, Alert
from db.database import async_session_maker
from services.notification_service import send_critical_alert_notification

logger = logging.getLogger(__name__)


class MQTTPersistenceService:
    """
    Service for persisting MQTT messages to the database.

    Provides async methods to store sensor readings, lock events,
    alerts, and device state updates.
    """

    async def get_or_create_device(
        self,
        db: AsyncSession,
        entity_id: str,
        device_name: Optional[str] = None,
        device_type: str = "sensor",
        mqtt_topic: Optional[str] = None
    ) -> IoTDevice:
        """
        Get existing device by entity_id or create new one.

        Args:
            db: Database session
            entity_id: Unique device identifier (from topic)
            device_name: Human-readable device name
            device_type: Type of device (sensor, lock, hvac, etc.)
            mqtt_topic: MQTT topic for this device

        Returns:
            IoTDevice instance
        """
        # Try to find existing device
        result = await db.execute(
            select(IoTDevice).where(IoTDevice.entity_id == entity_id)
        )
        device = result.scalar_one_or_none()

        if device:
            # Update last_seen
            device.last_seen = datetime.utcnow()
            return device

        # Create new device
        device = IoTDevice(
            entity_id=entity_id,
            device_name=device_name or entity_id,
            device_type=device_type,
            mqtt_topic=mqtt_topic,
            is_active=True,
            last_seen=datetime.utcnow()
        )
        db.add(device)
        await db.flush()  # Get the ID without committing

        logger.info(f"Created new IoT device: {entity_id} ({device_type})")
        return device

    async def store_sensor_reading(
        self,
        entity_id: str,
        metric: str,
        value: float,
        unit: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        mqtt_topic: Optional[str] = None
    ) -> bool:
        """
        Store a sensor reading in the database.

        Args:
            entity_id: Device entity ID
            metric: Metric name (temperature, humidity, power, etc.)
            value: Reading value
            unit: Unit of measurement
            timestamp: Reading timestamp (defaults to now)
            mqtt_topic: MQTT topic the reading came from

        Returns:
            True if stored successfully
        """
        try:
            async with async_session_maker() as db:
                # Get or create device
                device = await self.get_or_create_device(
                    db,
                    entity_id=entity_id,
                    device_type="sensor",
                    mqtt_topic=mqtt_topic
                )

                # Create sensor reading
                reading = SensorReading(
                    device_id=device.id,
                    metric=metric,
                    value=Decimal(str(value)),
                    unit=unit,
                    timestamp=timestamp or datetime.utcnow()
                )
                db.add(reading)
                await db.commit()

                logger.debug(f"Stored sensor reading: {entity_id}/{metric}={value}{unit or ''}")
                return True

        except Exception as e:
            logger.error(f"Failed to store sensor reading: {e}", exc_info=True)
            return False

    async def store_lock_event(
        self,
        entity_id: str,
        event_type: str,
        success: bool,
        user_name: Optional[str] = None,
        code_used: Optional[str] = None,
        unit_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Store a smart lock access event.

        Args:
            entity_id: Lock device entity ID
            event_type: Type of event (lock, unlock, code_entry, etc.)
            success: Whether the event was successful
            user_name: Name/identifier of user if known
            code_used: Code or credential used
            unit_id: Associated unit ID
            timestamp: Event timestamp

        Returns:
            True if stored successfully
        """
        try:
            async with async_session_maker() as db:
                # Create access log entry
                access_log = AccessLog(
                    entity_id=entity_id,
                    access_type="smart_lock",
                    event_type=event_type,
                    success=success,
                    user_name=user_name,
                    code_used=code_used,
                    timestamp=timestamp or datetime.utcnow()
                )

                # Set unit_id if provided (need to handle UUID conversion)
                if unit_id:
                    try:
                        import uuid
                        access_log.unit_id = uuid.UUID(unit_id)
                    except ValueError:
                        logger.warning(f"Invalid unit_id format: {unit_id}")

                db.add(access_log)
                await db.commit()

                logger.info(f"Stored lock event: {entity_id} - {event_type} (success={success})")

                # Log warning for failed access attempts
                if not success:
                    logger.warning(f"Failed access attempt on {entity_id} by {user_name or 'unknown'}")

                return True

        except Exception as e:
            logger.error(f"Failed to store lock event: {e}", exc_info=True)
            return False

    async def store_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        source: str,
        category: Optional[str] = None,
        hub_id: Optional[str] = None,
        unit_id: Optional[str] = None,
        send_notification: bool = True
    ) -> bool:
        """
        Store an alert and optionally send notifications.

        Args:
            alert_type: Type of alert (water_leak, smoke, etc.)
            severity: Severity level (info, warning, critical)
            message: Alert message
            source: Source device/sensor
            category: Alert category
            hub_id: Associated hub ID
            unit_id: Associated unit ID
            send_notification: Whether to send push notification

        Returns:
            True if stored successfully
        """
        try:
            async with async_session_maker() as db:
                alert = Alert(
                    category=category or alert_type,
                    severity=severity,
                    message=message,
                    status="open",
                    occurred_at=datetime.utcnow()
                )

                if hub_id:
                    alert.hub_id = hub_id

                db.add(alert)
                await db.commit()

                logger.warning(f"Stored alert: {alert_type} ({severity}) - {message[:100]}")

                # Send notification for critical alerts
                if send_notification and severity in ('critical', 'emergency'):
                    try:
                        await send_critical_alert_notification(
                            alert_type=alert_type,
                            message=message,
                            source=source
                        )
                    except Exception as e:
                        logger.error(f"Failed to send alert notification: {e}")

                return True

        except Exception as e:
            logger.error(f"Failed to store alert: {e}", exc_info=True)
            return False

    async def update_device_state(
        self,
        entity_id: str,
        state: str,
        battery_level: Optional[int] = None,
        signal_strength: Optional[int] = None,
        device_type: str = "sensor"
    ) -> bool:
        """
        Update device state information.

        Args:
            entity_id: Device entity ID
            state: Device state (online, offline, etc.)
            battery_level: Battery percentage
            signal_strength: Signal strength in dBm
            device_type: Type of device

        Returns:
            True if updated successfully
        """
        try:
            async with async_session_maker() as db:
                device = await self.get_or_create_device(
                    db,
                    entity_id=entity_id,
                    device_type=device_type
                )

                device.is_active = state.lower() in ('online', 'active', 'connected')
                device.last_seen = datetime.utcnow()

                if battery_level is not None:
                    device.battery_level = battery_level

                await db.commit()

                logger.debug(f"Updated device state: {entity_id} -> {state}")
                return True

        except Exception as e:
            logger.error(f"Failed to update device state: {e}", exc_info=True)
            return False


# Global singleton instance
mqtt_persistence = MQTTPersistenceService()
