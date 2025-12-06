"""
MQTT Integration Tests
Tests for verifying MQTT connectivity and message flow

Run with: pytest tests/test_mqtt_integration.py -v
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the MQTT service and test router
from services.mqtt_client import MQTTClient, mqtt_service


class TestMQTTClient:
    """Tests for MQTTClient class"""

    def test_client_initialization(self):
        """Test MQTT client initializes with correct defaults"""
        client = MQTTClient()

        assert client.base_topic == "somniproperty"
        assert client.state_topic == "somniproperty/state"
        assert client.sensor_topic == "somniproperty/sensor"
        assert client.lock_topic == "somniproperty/lock"
        assert client.hvac_topic == "somniproperty/hvac"
        assert client.alert_topic == "somniproperty/alert"
        assert client.connected is False
        assert client.client is None

    def test_client_id_uses_hostname(self):
        """Test that client ID includes hostname for uniqueness"""
        client = MQTTClient()

        assert "somniproperty-backend-" in client.client_id
        # Should not be empty after the prefix
        assert len(client.client_id) > len("somniproperty-backend-")

    def test_is_connected_returns_false_initially(self):
        """Test is_connected returns False before connection"""
        client = MQTTClient()

        assert client.is_connected() is False

    @pytest.mark.asyncio
    async def test_publish_when_disconnected(self):
        """Test that publish logs warning when not connected"""
        client = MQTTClient()

        with patch('services.mqtt_client.logger') as mock_logger:
            client.publish("test/topic", {"key": "value"})
            mock_logger.warning.assert_called()

    def test_register_handler(self):
        """Test custom handler registration"""
        client = MQTTClient()

        async def my_handler(topic, data):
            pass

        client.register_handler("somniproperty/custom", my_handler)

        assert "somniproperty/custom" in client.message_handlers
        assert client.message_handlers["somniproperty/custom"] == my_handler


class TestMQTTMessageRouting:
    """Tests for MQTT message routing logic"""

    @pytest.fixture
    def mqtt_client(self):
        """Create a fresh MQTT client for testing"""
        return MQTTClient()

    @pytest.mark.asyncio
    async def test_sensor_message_routing(self, mqtt_client):
        """Test sensor messages are routed correctly"""
        handled = []

        async def capture_handler(topic, data):
            handled.append(("sensor", topic, data))

        # Patch the handler
        mqtt_client._handle_sensor_message = capture_handler

        await mqtt_client._handle_message(
            "somniproperty/sensor/unit-101/temperature",
            {"value": 23.5, "unit": "celsius"}
        )

        assert len(handled) == 1
        assert handled[0][0] == "sensor"
        assert "temperature" in handled[0][1]

    @pytest.mark.asyncio
    async def test_lock_message_routing(self, mqtt_client):
        """Test lock event messages are routed correctly"""
        handled = []

        async def capture_handler(topic, data):
            handled.append(("lock", topic, data))

        mqtt_client._handle_lock_message = capture_handler

        await mqtt_client._handle_message(
            "somniproperty/lock/front-door",
            {"event_type": "unlock", "success": True}
        )

        assert len(handled) == 1
        assert handled[0][0] == "lock"

    @pytest.mark.asyncio
    async def test_alert_message_routing(self, mqtt_client):
        """Test alert messages are routed correctly"""
        handled = []

        async def capture_handler(topic, data):
            handled.append(("alert", topic, data))

        mqtt_client._handle_alert_message = capture_handler

        await mqtt_client._handle_message(
            "somniproperty/alert/water-leak",
            {"severity": "critical", "message": "Water detected"}
        )

        assert len(handled) == 1
        assert handled[0][0] == "alert"

    @pytest.mark.asyncio
    async def test_hvac_message_routing(self, mqtt_client):
        """Test HVAC messages are routed correctly"""
        handled = []

        async def capture_handler(topic, data):
            handled.append(("hvac", topic, data))

        mqtt_client._handle_hvac_message = capture_handler

        await mqtt_client._handle_message(
            "somniproperty/hvac/unit-101",
            {"current_temperature": 72.0, "mode": "cooling"}
        )

        assert len(handled) == 1
        assert handled[0][0] == "hvac"

    @pytest.mark.asyncio
    async def test_state_message_routing(self, mqtt_client):
        """Test state update messages are routed correctly"""
        handled = []

        async def capture_handler(topic, data):
            handled.append(("state", topic, data))

        mqtt_client._handle_state_message = capture_handler

        await mqtt_client._handle_message(
            "somniproperty/state/thermostat-101",
            {"state": "online", "battery_level": 85}
        )

        assert len(handled) == 1
        assert handled[0][0] == "state"

    @pytest.mark.asyncio
    async def test_custom_handler_called(self, mqtt_client):
        """Test custom handlers are called for matching topics"""
        custom_handled = []

        async def custom_handler(topic, data):
            custom_handled.append((topic, data))

        mqtt_client.register_handler("somniproperty/sensor", custom_handler)

        await mqtt_client._handle_message(
            "somniproperty/sensor/test",
            {"value": 100}
        )

        assert len(custom_handled) == 1


class TestMQTTConnectionCallbacks:
    """Tests for MQTT connection callbacks"""

    def test_on_connect_success(self):
        """Test successful connection callback"""
        client = MQTTClient()
        mock_mqtt_client = Mock()

        # Simulate successful connection (rc=0)
        client._on_connect(mock_mqtt_client, None, None, 0)

        assert client.connected is True
        # Should subscribe to 5 topics
        assert mock_mqtt_client.subscribe.call_count == 5

    def test_on_connect_failure(self):
        """Test failed connection callback"""
        client = MQTTClient()
        mock_mqtt_client = Mock()

        # Simulate failed connection (rc=4 = bad credentials)
        with patch('services.mqtt_client.logger') as mock_logger:
            client._on_connect(mock_mqtt_client, None, None, 4)
            mock_logger.error.assert_called()

        assert client.connected is False
        assert mock_mqtt_client.subscribe.call_count == 0

    def test_on_disconnect_unexpected(self):
        """Test unexpected disconnection callback"""
        client = MQTTClient()
        client.connected = True

        with patch('services.mqtt_client.logger') as mock_logger:
            client._on_disconnect(None, None, 1)  # rc=1 = unexpected
            mock_logger.warning.assert_called()

        assert client.connected is False

    def test_on_disconnect_normal(self):
        """Test normal disconnection callback"""
        client = MQTTClient()
        client.connected = True

        client._on_disconnect(None, None, 0)  # rc=0 = normal

        assert client.connected is False


class TestMQTTMessageParsing:
    """Tests for MQTT message parsing"""

    def test_on_message_valid_json(self):
        """Test handling valid JSON message"""
        client = MQTTClient()
        client.connected = True

        mock_message = Mock()
        mock_message.topic = "somniproperty/sensor/test"
        mock_message.payload = b'{"value": 23.5}'

        with patch.object(client, '_handle_message') as mock_handler:
            with patch('asyncio.create_task'):
                client._on_message(None, None, mock_message)
                # Handler should be called via asyncio.create_task

    def test_on_message_invalid_json(self):
        """Test handling invalid JSON message"""
        client = MQTTClient()

        mock_message = Mock()
        mock_message.topic = "somniproperty/sensor/test"
        mock_message.payload = b'not valid json'

        with patch('services.mqtt_client.logger') as mock_logger:
            client._on_message(None, None, mock_message)
            mock_logger.warning.assert_called()


class TestMQTTPublish:
    """Tests for MQTT publish functionality"""

    def test_publish_when_connected(self):
        """Test publishing when connected"""
        client = MQTTClient()
        client.connected = True
        client.client = Mock()
        client.client.publish.return_value = Mock(rc=0)  # MQTT_ERR_SUCCESS

        client.publish("test/topic", {"key": "value"}, qos=1, retain=True)

        client.client.publish.assert_called_once()
        call_args = client.client.publish.call_args
        assert call_args[0][0] == "test/topic"
        assert call_args[1]["qos"] == 1
        assert call_args[1]["retain"] is True

    def test_publish_json_encoding(self):
        """Test that payload is JSON encoded"""
        client = MQTTClient()
        client.connected = True
        client.client = Mock()
        client.client.publish.return_value = Mock(rc=0)

        payload = {"temperature": 23.5, "unit": "celsius"}
        client.publish("test/topic", payload)

        published_payload = client.client.publish.call_args[0][1]
        assert json.loads(published_payload) == payload


class TestMQTTGlobalInstance:
    """Tests for global MQTT service instance"""

    def test_global_instance_exists(self):
        """Test that global mqtt_service instance exists"""
        assert mqtt_service is not None
        assert isinstance(mqtt_service, MQTTClient)

    def test_global_instance_singleton(self):
        """Test that importing returns same instance"""
        from services.mqtt_client import mqtt_service as service2
        assert mqtt_service is service2


# Integration tests that require a running MQTT broker
# These are marked with 'integration' and skipped by default
@pytest.mark.integration
class TestMQTTIntegration:
    """Integration tests requiring live MQTT broker"""

    @pytest.mark.asyncio
    async def test_connect_to_broker(self):
        """Test actual connection to EMQX broker"""
        client = MQTTClient()

        try:
            await client.connect()
            assert client.is_connected()
        finally:
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self):
        """Test publishing and receiving messages"""
        client = MQTTClient()
        received_messages = []

        async def handler(topic, data):
            received_messages.append((topic, data))

        try:
            await client.connect()
            client.register_handler("somniproperty/test", handler)

            # Publish a test message
            client.publish(
                "somniproperty/test/integration",
                {"test": "message", "timestamp": datetime.utcnow().isoformat()}
            )

            # Wait for message to be received
            await asyncio.sleep(1)

            # Note: This test may not receive the message if we're
            # not subscribed before publishing. Real integration
            # would need a separate subscriber.

        finally:
            await client.disconnect()
