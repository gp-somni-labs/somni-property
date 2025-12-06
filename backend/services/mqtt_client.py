"""
MQTT Client Service
Handles MQTT connection and message routing for IoT devices
"""

import asyncio
import logging
import json
from typing import Optional, Callable, Dict
from paho.mqtt import client as mqtt_client
from datetime import datetime

from core.config import settings

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
_persistence_service = None


def get_persistence_service():
    """Lazy load persistence service to avoid circular imports."""
    global _persistence_service
    if _persistence_service is None:
        from services.mqtt_persistence import mqtt_persistence
        _persistence_service = mqtt_persistence
    return _persistence_service


class MQTTClient:
    """
    MQTT Client for IoT device communication

    Connects to EMQX broker and handles:
    - Device state updates
    - Sensor readings
    - Smart lock events
    - HVAC status changes
    - Work order triggers
    """

    def __init__(self):
        self.client: Optional[mqtt_client.Client] = None
        self.connected = False
        self.message_handlers: Dict[str, Callable] = {}

        # MQTT connection settings
        self.broker = settings.MQTT_BROKER
        self.port = int(settings.MQTT_PORT)

        # Use pod hostname for unique client_id (avoids client_id collision with multiple replicas)
        import socket
        hostname = socket.gethostname()
        self.client_id = f"somniproperty-backend-{hostname}"

        # Topic prefixes
        self.base_topic = "somniproperty"
        self.state_topic = f"{self.base_topic}/state"
        self.sensor_topic = f"{self.base_topic}/sensor"
        self.lock_topic = f"{self.base_topic}/lock"
        self.hvac_topic = f"{self.base_topic}/hvac"
        self.alert_topic = f"{self.base_topic}/alert"

    async def connect(self):
        """Initialize MQTT connection"""
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")

            # Create MQTT client
            self.client = mqtt_client.Client(client_id=self.client_id)

            # Set authentication credentials if available
            mqtt_username = settings.MQTT_USERNAME
            mqtt_password = settings.MQTT_PASSWORD

            if mqtt_username and mqtt_password:
                logger.info(f"Configuring MQTT authentication for user: {mqtt_username}")
                self.client.username_pw_set(username=mqtt_username, password=mqtt_password)
            else:
                logger.warning("MQTT credentials not configured - attempting anonymous connection")

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message

            # Connect to broker
            self.client.connect(self.broker, self.port, keepalive=60)

            # Start network loop in background
            self.client.loop_start()

            logger.info("MQTT client started successfully")
            self.connected = True

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.connected = False
            raise

    async def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client:
            logger.info("Disconnecting from MQTT broker")
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            logger.info("Successfully connected to MQTT broker")
            self.connected = True

            # Subscribe to all relevant topics
            topics = [
                (f"{self.state_topic}/#", 0),
                (f"{self.sensor_topic}/#", 0),
                (f"{self.lock_topic}/#", 0),
                (f"{self.hvac_topic}/#", 0),
                (f"{self.alert_topic}/#", 0),
            ]

            for topic, qos in topics:
                client.subscribe(topic, qos)
                logger.info(f"Subscribed to topic: {topic}")

        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc}")
            self.connected = False

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection. Return code: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")

    def _on_message(self, client, userdata, message):
        """Callback when MQTT message is received"""
        try:
            topic = message.topic
            payload = message.payload.decode('utf-8')

            logger.debug(f"Received MQTT message - Topic: {topic}, Payload: {payload}")

            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON payload from topic {topic}: {payload}")
                return

            # Route message to appropriate handler
            asyncio.create_task(self._handle_message(topic, data))

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)

    async def _handle_message(self, topic: str, data: dict):
        """Route MQTT messages to appropriate handlers"""
        try:
            # Determine message type from topic
            if topic.startswith(self.sensor_topic):
                await self._handle_sensor_message(topic, data)
            elif topic.startswith(self.lock_topic):
                await self._handle_lock_message(topic, data)
            elif topic.startswith(self.hvac_topic):
                await self._handle_hvac_message(topic, data)
            elif topic.startswith(self.alert_topic):
                await self._handle_alert_message(topic, data)
            elif topic.startswith(self.state_topic):
                await self._handle_state_message(topic, data)

            # Call custom handlers
            for pattern, handler in self.message_handlers.items():
                if topic.startswith(pattern):
                    await handler(topic, data)

        except Exception as e:
            logger.error(f"Error handling MQTT message from {topic}: {e}", exc_info=True)

    async def _handle_sensor_message(self, topic: str, data: dict):
        """Handle sensor reading messages"""
        logger.debug(f"Sensor data received: {topic} -> {data}")

        # Extract entity_id from topic
        # Example topic: somniproperty/sensor/unit-101/temperature
        parts = topic.split('/')
        if len(parts) >= 4:
            unit_identifier = parts[2]
            metric = parts[3]
            entity_id = f"{unit_identifier}/{metric}"

            # Store sensor reading in database
            persistence = get_persistence_service()
            value = data.get('value')
            unit = data.get('unit')

            if value is not None:
                try:
                    await persistence.store_sensor_reading(
                        entity_id=entity_id,
                        metric=metric,
                        value=float(value),
                        unit=unit,
                        mqtt_topic=topic
                    )
                except Exception as e:
                    logger.error(f"Failed to persist sensor reading: {e}")

            logger.info(f"Sensor reading: {unit_identifier}/{metric} = {value}")

    async def _handle_lock_message(self, topic: str, data: dict):
        """Handle smart lock events"""
        logger.debug(f"Lock event received: {topic} -> {data}")

        # Extract lock_id from topic
        # Example topic: somniproperty/lock/front-door-101
        parts = topic.split('/')
        entity_id = parts[2] if len(parts) >= 3 else topic

        event_type = data.get('event_type', 'unknown')
        success = data.get('success', False)
        user_name = data.get('user') or data.get('user_name')
        code_used = data.get('code_used') or data.get('code_type')

        # Store lock event in database
        persistence = get_persistence_service()
        try:
            await persistence.store_lock_event(
                entity_id=entity_id,
                event_type=event_type,
                success=success,
                user_name=user_name,
                code_used=code_used
            )
        except Exception as e:
            logger.error(f"Failed to persist lock event: {e}")

        logger.info(f"Lock event: {topic} - {event_type} (success={success})")

    async def _handle_hvac_message(self, topic: str, data: dict):
        """Handle HVAC/thermostat messages"""
        logger.debug(f"HVAC data received: {topic} -> {data}")

        # Extract hvac_id from topic
        # Example topic: somniproperty/hvac/unit-101
        parts = topic.split('/')
        entity_id = parts[2] if len(parts) >= 3 else topic

        persistence = get_persistence_service()

        # Store temperature readings as sensor data
        try:
            if 'current_temperature' in data:
                await persistence.store_sensor_reading(
                    entity_id=f"{entity_id}/temperature",
                    metric="temperature",
                    value=float(data['current_temperature']),
                    unit="fahrenheit",
                    mqtt_topic=topic
                )

            if 'humidity' in data:
                await persistence.store_sensor_reading(
                    entity_id=f"{entity_id}/humidity",
                    metric="humidity",
                    value=float(data['humidity']),
                    unit="percent",
                    mqtt_topic=topic
                )
        except Exception as e:
            logger.error(f"Failed to persist HVAC readings: {e}")

        logger.info(f"HVAC update: {topic} -> {data}")

    async def _handle_alert_message(self, topic: str, data: dict):
        """Handle alert/alarm messages"""
        logger.warning(f"Alert received: {topic} -> {data}")

        # Extract alert info from topic and data
        parts = topic.split('/')
        source = parts[2] if len(parts) >= 3 else "unknown"

        alert_type = data.get('alert_type', 'unknown')
        severity = data.get('severity', 'info')
        message = data.get('message', f"Alert from {source}")

        # Store alert and send notifications for critical alerts
        persistence = get_persistence_service()
        try:
            await persistence.store_alert(
                alert_type=alert_type,
                severity=severity,
                message=message,
                source=source,
                category=alert_type,
                send_notification=(severity in ('critical', 'emergency', 'high'))
            )
        except Exception as e:
            logger.error(f"Failed to persist alert: {e}")

        logger.warning(f"ALERT: {alert_type} (severity={severity}) from {topic}")

    async def _handle_state_message(self, topic: str, data: dict):
        """Handle general state update messages"""
        logger.debug(f"State update received: {topic} -> {data}")

        # Extract device_id from topic or data
        parts = topic.split('/')
        entity_id = data.get('device_id') or (parts[2] if len(parts) >= 3 else topic)

        state = data.get('state', 'unknown')
        battery_level = data.get('battery_level')
        signal_strength = data.get('signal_strength')

        # Update device state in database
        persistence = get_persistence_service()
        try:
            await persistence.update_device_state(
                entity_id=entity_id,
                state=state,
                battery_level=battery_level,
                signal_strength=signal_strength
            )
        except Exception as e:
            logger.error(f"Failed to update device state: {e}")

    def register_handler(self, topic_pattern: str, handler: Callable):
        """
        Register a custom message handler for a topic pattern

        Args:
            topic_pattern: MQTT topic pattern (can include wildcards)
            handler: Async function to call when message matches pattern
        """
        self.message_handlers[topic_pattern] = handler
        logger.info(f"Registered custom handler for topic: {topic_pattern}")

    def publish(self, topic: str, payload: dict, qos: int = 0, retain: bool = False):
        """
        Publish message to MQTT broker

        Args:
            topic: MQTT topic
            payload: Message payload (will be JSON encoded)
            qos: Quality of Service (0, 1, or 2)
            retain: Whether to retain the message
        """
        if not self.connected or not self.client:
            logger.warning(f"Cannot publish to {topic}: MQTT client not connected")
            return

        try:
            payload_str = json.dumps(payload)
            result = self.client.publish(topic, payload_str, qos=qos, retain=retain)

            if result.rc == mqtt_client.MQTT_ERR_SUCCESS:
                logger.debug(f"Published to {topic}: {payload_str}")
            else:
                logger.error(f"Failed to publish to {topic}: {result.rc}")

        except Exception as e:
            logger.error(f"Error publishing to {topic}: {e}", exc_info=True)

    def is_connected(self) -> bool:
        """Check if MQTT client is connected"""
        return self.connected


# Global MQTT client instance
mqtt_service = MQTTClient()


async def get_mqtt_client() -> MQTTClient:
    """Dependency to get MQTT client instance"""
    return mqtt_service
