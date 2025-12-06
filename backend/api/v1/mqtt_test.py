"""
MQTT Test API Endpoints
For testing and monitoring MQTT connectivity and message flow
"""

import asyncio
import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends

from services.mqtt_client import mqtt_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mqtt", tags=["MQTT Testing"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class MQTTPublishRequest(BaseModel):
    """Request to publish an MQTT message"""
    topic: str = Field(..., description="MQTT topic to publish to")
    payload: Dict[str, Any] = Field(..., description="JSON payload to publish")
    qos: int = Field(default=0, ge=0, le=2, description="QoS level (0, 1, or 2)")
    retain: bool = Field(default=False, description="Whether to retain the message")


class MQTTTestMessage(BaseModel):
    """Test message format"""
    message: str = Field(default="test", description="Test message content")
    timestamp: Optional[str] = None
    source: str = Field(default="api_test", description="Message source identifier")


class MQTTStatusResponse(BaseModel):
    """MQTT connection status response"""
    connected: bool
    broker: str
    port: int
    client_id: str
    subscribed_topics: List[str]


class MQTTLatencyTestResult(BaseModel):
    """Result of latency test"""
    success: bool
    round_trip_ms: Optional[float] = None
    error: Optional[str] = None
    timestamp: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/status", response_model=MQTTStatusResponse)
async def get_mqtt_status():
    """
    Get current MQTT connection status

    Returns connection state, broker info, and subscribed topics.
    """
    return MQTTStatusResponse(
        connected=mqtt_service.is_connected(),
        broker=mqtt_service.broker,
        port=mqtt_service.port,
        client_id=mqtt_service.client_id,
        subscribed_topics=[
            f"{mqtt_service.state_topic}/#",
            f"{mqtt_service.sensor_topic}/#",
            f"{mqtt_service.lock_topic}/#",
            f"{mqtt_service.hvac_topic}/#",
            f"{mqtt_service.alert_topic}/#",
        ]
    )


@router.post("/publish")
async def publish_message(request: MQTTPublishRequest):
    """
    Publish a message to an MQTT topic

    Use this to test MQTT publishing functionality.
    """
    if not mqtt_service.is_connected():
        raise HTTPException(
            status_code=503,
            detail="MQTT client not connected"
        )

    try:
        mqtt_service.publish(
            topic=request.topic,
            payload=request.payload,
            qos=request.qos,
            retain=request.retain
        )

        return {
            "success": True,
            "topic": request.topic,
            "payload": request.payload,
            "qos": request.qos,
            "retain": request.retain,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to publish MQTT message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/sensor")
async def test_sensor_message(test_data: MQTTTestMessage = None):
    """
    Publish a test sensor message

    Publishes to somniproperty/sensor/test with a test payload.
    """
    if not mqtt_service.is_connected():
        raise HTTPException(
            status_code=503,
            detail="MQTT client not connected"
        )

    if test_data is None:
        test_data = MQTTTestMessage()

    payload = {
        "value": 23.5,
        "unit": "celsius",
        "source": test_data.source,
        "message": test_data.message,
        "timestamp": test_data.timestamp or datetime.utcnow().isoformat()
    }

    topic = f"{mqtt_service.sensor_topic}/test"
    mqtt_service.publish(topic, payload, qos=1)

    return {
        "success": True,
        "topic": topic,
        "payload": payload
    }


@router.post("/test/alert")
async def test_alert_message(
    alert_type: str = "test",
    severity: str = "info"
):
    """
    Publish a test alert message

    Publishes to somniproperty/alert/test with specified severity.
    """
    if not mqtt_service.is_connected():
        raise HTTPException(
            status_code=503,
            detail="MQTT client not connected"
        )

    payload = {
        "alert_type": alert_type,
        "severity": severity,
        "message": "This is a test alert from the API",
        "source": "api_test",
        "timestamp": datetime.utcnow().isoformat()
    }

    topic = f"{mqtt_service.alert_topic}/test"
    mqtt_service.publish(topic, payload, qos=1)

    return {
        "success": True,
        "topic": topic,
        "payload": payload
    }


@router.post("/test/lock")
async def test_lock_message(
    event_type: str = "test_access",
    success: bool = True
):
    """
    Publish a test lock event message

    Simulates a smart lock access event.
    """
    if not mqtt_service.is_connected():
        raise HTTPException(
            status_code=503,
            detail="MQTT client not connected"
        )

    payload = {
        "event_type": event_type,
        "success": success,
        "code_type": "test_code",
        "user": "test_user",
        "source": "api_test",
        "timestamp": datetime.utcnow().isoformat()
    }

    topic = f"{mqtt_service.lock_topic}/test"
    mqtt_service.publish(topic, payload, qos=1)

    return {
        "success": True,
        "topic": topic,
        "payload": payload
    }


@router.post("/test/hvac")
async def test_hvac_message(
    temperature: float = 72.0,
    humidity: float = 45.0,
    mode: str = "cooling"
):
    """
    Publish a test HVAC status message

    Simulates thermostat/HVAC state update.
    """
    if not mqtt_service.is_connected():
        raise HTTPException(
            status_code=503,
            detail="MQTT client not connected"
        )

    payload = {
        "current_temperature": temperature,
        "target_temperature": 70.0,
        "humidity": humidity,
        "mode": mode,
        "fan_state": "auto",
        "source": "api_test",
        "timestamp": datetime.utcnow().isoformat()
    }

    topic = f"{mqtt_service.hvac_topic}/test"
    mqtt_service.publish(topic, payload, qos=1)

    return {
        "success": True,
        "topic": topic,
        "payload": payload
    }


@router.post("/test/state")
async def test_state_message(
    device_id: str = "test_device",
    state: str = "online"
):
    """
    Publish a test device state message

    Simulates device state update.
    """
    if not mqtt_service.is_connected():
        raise HTTPException(
            status_code=503,
            detail="MQTT client not connected"
        )

    payload = {
        "device_id": device_id,
        "state": state,
        "battery_level": 85,
        "signal_strength": -45,
        "source": "api_test",
        "timestamp": datetime.utcnow().isoformat()
    }

    topic = f"{mqtt_service.state_topic}/{device_id}"
    mqtt_service.publish(topic, payload, qos=1)

    return {
        "success": True,
        "topic": topic,
        "payload": payload
    }


@router.post("/test/bulk", response_model=Dict[str, Any])
async def test_bulk_messages(count: int = 10, delay_ms: int = 100):
    """
    Send multiple test messages to measure throughput

    Args:
        count: Number of messages to send (max 100)
        delay_ms: Delay between messages in milliseconds

    Returns:
        Statistics about the bulk test
    """
    if not mqtt_service.is_connected():
        raise HTTPException(
            status_code=503,
            detail="MQTT client not connected"
        )

    if count > 100:
        count = 100

    start_time = time.time()
    sent_count = 0
    errors = []

    for i in range(count):
        try:
            payload = {
                "sequence": i + 1,
                "total": count,
                "timestamp": datetime.utcnow().isoformat()
            }
            mqtt_service.publish(
                f"{mqtt_service.sensor_topic}/bulk_test",
                payload,
                qos=0
            )
            sent_count += 1

            if delay_ms > 0 and i < count - 1:
                await asyncio.sleep(delay_ms / 1000)

        except Exception as e:
            errors.append(f"Message {i+1}: {str(e)}")

    elapsed_time = time.time() - start_time

    return {
        "success": len(errors) == 0,
        "total_requested": count,
        "total_sent": sent_count,
        "elapsed_seconds": round(elapsed_time, 3),
        "messages_per_second": round(sent_count / elapsed_time, 2) if elapsed_time > 0 else 0,
        "errors": errors if errors else None
    }


@router.get("/health")
async def mqtt_health_check():
    """
    Comprehensive MQTT health check

    Checks connection status and attempts to verify broker accessibility.
    """
    health_status = {
        "status": "healthy" if mqtt_service.is_connected() else "unhealthy",
        "connected": mqtt_service.is_connected(),
        "broker": mqtt_service.broker,
        "port": mqtt_service.port,
        "client_id": mqtt_service.client_id,
        "checked_at": datetime.utcnow().isoformat()
    }

    if not mqtt_service.is_connected():
        health_status["error"] = "MQTT client not connected to broker"

    return health_status
