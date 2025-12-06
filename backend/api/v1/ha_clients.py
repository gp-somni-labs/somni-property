"""
Home Assistant Client Management API
MSP endpoints for managing multiple customer Home Assistant instances
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from services.ha_client_manager import get_ha_client_manager, HAClientManager, HAClientConfig

router = APIRouter(prefix="/ha-clients", tags=["Home Assistant Clients"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ClientInfo(BaseModel):
    """Client information response model"""
    client_id: str
    name: str
    ha_url: str
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

    class Config:
        from_attributes = True


class ServiceCallRequest(BaseModel):
    """Request model for calling HA services"""
    domain: str
    service: str
    service_data: Optional[Dict[str, Any]] = None


class NotificationRequest(BaseModel):
    """Request model for sending notifications"""
    message: str
    title: Optional[str] = None
    target: Optional[str] = None


class LightControlRequest(BaseModel):
    """Request model for light control"""
    entity_id: str


class TemperatureSetRequest(BaseModel):
    """Request model for setting temperature"""
    entity_id: str
    temperature: float


# ============================================================================
# Client Management Endpoints
# ============================================================================

@router.get("", response_model=List[ClientInfo])
async def get_all_clients(
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Get list of all managed Home Assistant client instances

    Returns client configurations with metadata (tokens excluded for security)
    """
    clients = manager.get_all_clients()
    return [ClientInfo.model_validate(client) for client in clients]


@router.get("/{client_id}", response_model=ClientInfo)
async def get_client(
    client_id: str,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Get detailed information about a specific client

    Args:
        client_id: Client ID (e.g., "001")
    """
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    return ClientInfo.model_validate(config)


@router.get("/ids/list", response_model=List[str])
async def get_client_ids(
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """Get list of all client IDs"""
    return manager.get_client_ids()


# ============================================================================
# Health & Monitoring Endpoints
# ============================================================================

@router.get("/{client_id}/health")
async def check_client_health(
    client_id: str,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Check health status of a client's Home Assistant instance

    Tests API connectivity and response time
    """
    return await manager.check_health(client_id)


@router.get("/health/all")
async def check_all_clients_health(
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Check health status of all client Home Assistant instances

    Useful for monitoring dashboards and alerting
    """
    return await manager.check_all_clients_health()


# ============================================================================
# Home Assistant State Endpoints
# ============================================================================

@router.get("/{client_id}/states")
async def get_client_states(
    client_id: str,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Get all entity states from a client's Home Assistant instance

    Returns list of all entities with their current states and attributes
    """
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    states = await manager.get_states(client_id)
    return {
        "client_id": client_id,
        "client_name": config.name,
        "entity_count": len(states),
        "states": states
    }


@router.get("/{client_id}/states/{entity_id:path}")
async def get_entity_state(
    client_id: str,
    entity_id: str,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Get state of a specific entity

    Args:
        client_id: Client ID
        entity_id: Entity ID (e.g., "light.kitchen", "sensor.temperature")
    """
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    state = await manager.get_state(client_id, entity_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Entity {entity_id} not found for client {client_id}"
        )

    return state


@router.get("/states/all")
async def get_all_clients_states(
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Get states from all client instances

    Warning: This can return a large amount of data for many clients
    """
    return await manager.get_all_clients_states()


# ============================================================================
# Home Assistant Service Call Endpoints
# ============================================================================

@router.post("/{client_id}/services/call")
async def call_service(
    client_id: str,
    request: ServiceCallRequest,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Call a Home Assistant service

    Examples:
        - Turn on light: domain="light", service="turn_on", service_data={"entity_id": "light.kitchen"}
        - Set climate: domain="climate", service="set_temperature", service_data={"entity_id": "climate.main", "temperature": 72}
        - Send notification: domain="notify", service="persistent_notification", service_data={"message": "Test"}
    """
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    success = await manager.call_service(
        client_id,
        request.domain,
        request.service,
        request.service_data
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to call service {request.domain}.{request.service}"
        )

    return {
        "success": True,
        "client_id": client_id,
        "client_name": config.name,
        "service": f"{request.domain}.{request.service}"
    }


@router.post("/{client_id}/notify")
async def send_notification(
    client_id: str,
    request: NotificationRequest,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Send a notification to a client's Home Assistant instance

    The notification will appear in the HA frontend
    """
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    await manager.send_notification(
        client_id,
        request.message,
        request.title,
        request.target
    )

    return {
        "success": True,
        "client_id": client_id,
        "client_name": config.name,
        "message": request.message
    }


# ============================================================================
# Convenience Control Endpoints
# ============================================================================

@router.post("/{client_id}/lights/turn_on")
async def turn_on_light(
    client_id: str,
    request: LightControlRequest,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """Turn on a light for a specific client"""
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    success = await manager.turn_on_light(client_id, request.entity_id)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to turn on light {request.entity_id}"
        )

    return {
        "success": True,
        "client_id": client_id,
        "entity_id": request.entity_id,
        "action": "turn_on"
    }


@router.post("/{client_id}/lights/turn_off")
async def turn_off_light(
    client_id: str,
    request: LightControlRequest,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """Turn off a light for a specific client"""
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    success = await manager.turn_off_light(client_id, request.entity_id)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to turn off light {request.entity_id}"
        )

    return {
        "success": True,
        "client_id": client_id,
        "entity_id": request.entity_id,
        "action": "turn_off"
    }


@router.post("/{client_id}/climate/set_temperature")
async def set_temperature(
    client_id: str,
    request: TemperatureSetRequest,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """Set temperature for a client's thermostat"""
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    success = await manager.set_temperature(
        client_id,
        request.entity_id,
        request.temperature
    )
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set temperature for {request.entity_id}"
        )

    return {
        "success": True,
        "client_id": client_id,
        "entity_id": request.entity_id,
        "temperature": request.temperature
    }


# ============================================================================
# History & Reporting Endpoints
# ============================================================================

@router.get("/{client_id}/history/{entity_id:path}")
async def get_entity_history(
    client_id: str,
    entity_id: str,
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Get historical data for an entity

    Args:
        client_id: Client ID
        entity_id: Entity ID
        start_time: Start time (ISO format, defaults to 24 hours ago)
        end_time: End time (ISO format, defaults to now)
    """
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    history = await manager.get_history(client_id, entity_id, start_time, end_time)

    return {
        "client_id": client_id,
        "client_name": config.name,
        "entity_id": entity_id,
        "record_count": len(history),
        "history": history
    }


# ============================================================================
# Configuration Endpoints
# ============================================================================

@router.get("/{client_id}/config")
async def get_client_config(
    client_id: str,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Get Home Assistant configuration for a client

    Returns HA version, location, units, etc.
    """
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    ha_config = await manager.get_config(client_id)
    if not ha_config:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get configuration for client {client_id}"
        )

    return {
        "client_id": client_id,
        "client_name": config.name,
        "ha_config": ha_config
    }


@router.get("/{client_id}/services")
async def get_client_services(
    client_id: str,
    manager: HAClientManager = Depends(get_ha_client_manager)
):
    """
    Get available services in client's Home Assistant

    Returns all domains and services available in the HA instance
    """
    config = manager.get_client_config(client_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")

    services = await manager.get_services(client_id)
    if services is None:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get services for client {client_id}"
        )

    return {
        "client_id": client_id,
        "client_name": config.name,
        "services": services
    }
