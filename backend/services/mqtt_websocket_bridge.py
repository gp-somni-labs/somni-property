"""
MQTT to WebSocket Bridge Service
Bridges MQTT messages to WebSocket clients for real-time frontend updates
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class MQTTWebSocketBridge:
    """
    Bridges MQTT messages to WebSocket clients.

    When IoT devices publish messages to MQTT, this bridge forwards
    relevant events to connected WebSocket clients for real-time UI updates.

    Message Types Forwarded:
    - sensor_reading: Temperature, humidity, power readings
    - lock_event: Smart lock access events
    - hvac_update: HVAC/thermostat status changes
    - device_alert: Critical alerts (water leak, smoke, etc.)
    - device_state: Device online/offline status
    """

    def __init__(self):
        self.running = False
        self._ws_manager = None
        self._mqtt_client = None
        logger.info("MQTTWebSocketBridge initialized")

    def _get_ws_manager(self):
        """Lazy load WebSocket manager to avoid circular imports."""
        if self._ws_manager is None:
            from services.websocket_manager import manager
            self._ws_manager = manager
        return self._ws_manager

    def _get_mqtt_client(self):
        """Lazy load MQTT client to avoid circular imports."""
        if self._mqtt_client is None:
            from services.mqtt_client import mqtt_service
            self._mqtt_client = mqtt_service
        return self._mqtt_client

    async def start(self):
        """Start the bridge by registering MQTT handlers."""
        if self.running:
            logger.warning("MQTTWebSocketBridge already running")
            return

        mqtt_client = self._get_mqtt_client()

        if not mqtt_client.is_connected():
            logger.warning("MQTT client not connected, bridge will not forward messages")
            return

        # Register handlers for each message type
        mqtt_client.register_handler("somniproperty/sensor", self._handle_sensor_for_ws)
        mqtt_client.register_handler("somniproperty/lock", self._handle_lock_for_ws)
        mqtt_client.register_handler("somniproperty/hvac", self._handle_hvac_for_ws)
        mqtt_client.register_handler("somniproperty/alert", self._handle_alert_for_ws)
        mqtt_client.register_handler("somniproperty/state", self._handle_state_for_ws)

        self.running = True
        logger.info("✅ MQTT-WebSocket bridge started - forwarding IoT events to frontend")

    async def stop(self):
        """Stop the bridge."""
        self.running = False
        logger.info("MQTT-WebSocket bridge stopped")

    async def _handle_sensor_for_ws(self, topic: str, data: dict):
        """Forward sensor readings to WebSocket clients."""
        try:
            ws_manager = self._get_ws_manager()

            # Parse topic to get unit/device info
            # Example: somniproperty/sensor/unit-101/temperature
            parts = topic.split('/')
            unit_id = parts[2] if len(parts) >= 3 else "unknown"
            metric = parts[3] if len(parts) >= 4 else "unknown"

            message = {
                "type": "sensor_reading",
                "topic": topic,
                "unit_id": unit_id,
                "metric": metric,
                "value": data.get('value'),
                "unit": data.get('unit'),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Broadcast to room for this unit
            room = f"unit:{unit_id}"
            await ws_manager.broadcast_to_room(message, room)

            # Also broadcast to general IoT room
            await ws_manager.broadcast_to_room(message, "iot:all")

            logger.debug(f"WS Bridge: Forwarded sensor reading from {topic}")

        except Exception as e:
            logger.error(f"WS Bridge error handling sensor: {e}")

    async def _handle_lock_for_ws(self, topic: str, data: dict):
        """Forward lock events to WebSocket clients."""
        try:
            ws_manager = self._get_ws_manager()

            # Parse topic
            parts = topic.split('/')
            lock_id = parts[2] if len(parts) >= 3 else "unknown"

            event_type = data.get('event_type', 'unknown')
            success = data.get('success', False)
            user_name = data.get('user') or data.get('user_name', 'unknown')

            message = {
                "type": "lock_event",
                "topic": topic,
                "lock_id": lock_id,
                "event_type": event_type,
                "success": success,
                "user": user_name,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Security events go to security room
            await ws_manager.broadcast_to_room(message, "security:access")

            # Also to general IoT room
            await ws_manager.broadcast_to_room(message, "iot:all")

            # Failed access attempts get broadcasted to all admins
            if not success:
                message["severity"] = "warning"
                await ws_manager.broadcast_to_room(message, "alerts:security")

            logger.info(f"WS Bridge: Forwarded lock event from {topic} ({event_type})")

        except Exception as e:
            logger.error(f"WS Bridge error handling lock event: {e}")

    async def _handle_hvac_for_ws(self, topic: str, data: dict):
        """Forward HVAC updates to WebSocket clients."""
        try:
            ws_manager = self._get_ws_manager()

            parts = topic.split('/')
            hvac_id = parts[2] if len(parts) >= 3 else "unknown"

            message = {
                "type": "hvac_update",
                "topic": topic,
                "hvac_id": hvac_id,
                "current_temperature": data.get('current_temperature'),
                "target_temperature": data.get('target_temperature'),
                "mode": data.get('mode'),
                "humidity": data.get('humidity'),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Broadcast to unit room
            room = f"unit:{hvac_id}"
            await ws_manager.broadcast_to_room(message, room)
            await ws_manager.broadcast_to_room(message, "iot:all")

            logger.debug(f"WS Bridge: Forwarded HVAC update from {topic}")

        except Exception as e:
            logger.error(f"WS Bridge error handling HVAC: {e}")

    async def _handle_alert_for_ws(self, topic: str, data: dict):
        """Forward critical alerts to WebSocket clients."""
        try:
            ws_manager = self._get_ws_manager()

            parts = topic.split('/')
            source = parts[2] if len(parts) >= 3 else "unknown"

            alert_type = data.get('alert_type', 'unknown')
            severity = data.get('severity', 'info')
            alert_message = data.get('message', 'Alert received')

            message = {
                "type": "device_alert",
                "topic": topic,
                "alert_type": alert_type,
                "severity": severity,
                "message": alert_message,
                "source": source,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Use the existing send_iot_alert method for critical alerts
            if severity in ('critical', 'emergency', 'high'):
                await ws_manager.send_iot_alert(
                    alert_type=alert_type,
                    device_id=source,
                    message_text=alert_message,
                    severity=severity,
                    room="alerts:critical"
                )

                # Also broadcast to all connected clients for critical alerts
                await ws_manager.broadcast(message)
            else:
                # Lower severity just goes to alert room
                await ws_manager.broadcast_to_room(message, "alerts:all")

            await ws_manager.broadcast_to_room(message, "iot:all")

            logger.warning(f"WS Bridge: Forwarded alert from {topic} ({alert_type}, severity={severity})")

        except Exception as e:
            logger.error(f"WS Bridge error handling alert: {e}")

    async def _handle_state_for_ws(self, topic: str, data: dict):
        """Forward device state changes to WebSocket clients."""
        try:
            ws_manager = self._get_ws_manager()

            parts = topic.split('/')
            device_id = data.get('device_id') or (parts[2] if len(parts) >= 3 else "unknown")

            state = data.get('state', 'unknown')
            battery = data.get('battery_level')

            message = {
                "type": "device_state",
                "topic": topic,
                "device_id": device_id,
                "state": state,
                "battery_level": battery,
                "online": state.lower() in ('online', 'active', 'connected'),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Broadcast to IoT monitoring room
            await ws_manager.broadcast_to_room(message, "iot:all")
            await ws_manager.broadcast_to_room(message, "devices:status")

            # Low battery alerts
            if battery is not None and battery < 20:
                message["type"] = "low_battery_alert"
                message["severity"] = "warning"
                await ws_manager.broadcast_to_room(message, "alerts:all")

            logger.debug(f"WS Bridge: Forwarded device state from {topic} ({state})")

        except Exception as e:
            logger.error(f"WS Bridge error handling state: {e}")

    async def send_custom_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        room: Optional[str] = None,
        broadcast_all: bool = False
    ):
        """
        Send a custom event to WebSocket clients.

        Useful for other services to push real-time updates.

        Args:
            event_type: Type of event (e.g., 'work_order_created', 'payment_received')
            data: Event data to send
            room: Optional room to target
            broadcast_all: If True, broadcast to all connected clients
        """
        try:
            ws_manager = self._get_ws_manager()

            message = {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }

            if broadcast_all:
                await ws_manager.broadcast(message)
            elif room:
                await ws_manager.broadcast_to_room(message, room)
            else:
                await ws_manager.broadcast_to_room(message, "iot:all")

            logger.info(f"WS Bridge: Sent custom event {event_type}")

        except Exception as e:
            logger.error(f"WS Bridge error sending custom event: {e}")


# Global singleton instance
mqtt_ws_bridge = MQTTWebSocketBridge()


async def get_mqtt_ws_bridge() -> MQTTWebSocketBridge:
    """Dependency to get MQTT-WebSocket bridge instance."""
    return mqtt_ws_bridge
