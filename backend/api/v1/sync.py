"""
Somni Property Manager - Hub Sync API
Endpoints for Tier 2/3 hubs to sync devices and report health to Master Hub (Tier 1)
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from db.database import get_db
from db.models import PropertyEdgeNode as EdgeNodeModel, EdgeNodeCommand
from services.hub_sync_service import hub_sync_service

router = APIRouter()


# ========================================================================
# Pydantic Schemas for Sync API
# ========================================================================

class DeviceSyncItem(BaseModel):
    """Single device from Home Assistant for sync"""
    entity_id: str = Field(..., description="Home Assistant entity ID (e.g., 'light.living_room')")
    domain: str = Field(..., description="HA domain (light, switch, sensor, climate, lock, etc.)")
    state: str = Field(..., description="Current state from HA")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="HA attributes JSON")


class DeviceSyncRequest(BaseModel):
    """Request body for device sync from Tier 2/3 hub"""
    hub_id: UUID = Field(..., description="UUID of the PropertyEdgeNode (Tier 2/3 hub)")
    devices: List[DeviceSyncItem] = Field(..., description="List of devices discovered from Home Assistant")


class DeviceSyncResponse(BaseModel):
    """Response after processing device sync"""
    added: int = Field(..., description="Number of new devices added")
    updated: int = Field(..., description="Number of devices updated")
    removed: int = Field(..., description="Number of devices marked as inactive")
    sync_id: str = Field(..., description="UUID of the DeviceSync record")


class HubHealthReport(BaseModel):
    """Hub health metrics reported every 60 seconds"""
    hub_id: UUID = Field(..., description="UUID of the PropertyEdgeNode")
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU usage percentage")
    memory_usage: float = Field(..., ge=0, le=100, description="Memory usage percentage")
    disk_usage: float = Field(..., ge=0, le=100, description="Disk usage percentage")
    temperature: Optional[float] = Field(None, description="CPU temperature in Celsius")
    services: Dict[str, str] = Field(
        ...,
        description="Service status map (service_name -> status)",
        example={
            "home-assistant": "running",
            "frigate": "running",
            "tailscale": "running",
            "mosquitto": "running",
            "zigbee2mqtt": "running"
        }
    )


class HubHealthResponse(BaseModel):
    """Response after processing health report"""
    hub_id: str
    status: str
    message: str


class CommandInfo(BaseModel):
    """Command to be executed by edge hub"""
    command_id: str = Field(..., description="UUID of the command")
    type: str = Field(..., description="Command type: service_call, state_change, script, automation")
    target_entity: str = Field(..., description="Target entity ID (e.g., 'light.living_room')")
    action: str = Field(..., description="Action: turn_on, turn_off, lock, unlock, etc.")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")


class CommandsResponse(BaseModel):
    """Response with list of pending commands"""
    commands: List[CommandInfo] = Field(..., description="List of pending commands")


class CommandAcknowledgment(BaseModel):
    """Acknowledgment of command execution from edge hub"""
    status: str = Field(..., description="Execution status: success, failed, timeout")
    result: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Execution result")


class CommandAckResponse(BaseModel):
    """Response after processing command acknowledgment"""
    command_id: str
    status: str
    message: str


# ========================================================================
# Sync API Endpoints (Called BY Tier 2/3 Hubs)
# ========================================================================

@router.post("/devices", response_model=DeviceSyncResponse, status_code=200)
async def sync_devices(
    sync_data: DeviceSyncRequest,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, description="Bearer {hub_api_token}"),
    x_hub_id: Optional[str] = Header(None, description="Hub UUID for validation")
):
    """
    Sync discovered devices from a Tier 2/3 hub to Master Hub (Tier 1)

    This endpoint is called BY Tier 2/3 hubs to push their discovered devices.

    Authentication:
    - Authorization: Bearer {hub_api_token}
    - X-Hub-ID: {hub_uuid}

    Process:
    1. Validate hub_id and auth token
    2. Compare incoming devices with database
    3. Add new devices
    4. Update changed devices
    5. Mark removed devices as inactive
    6. Record sync metadata in DeviceSync table

    Returns:
        DeviceSyncResponse with counts of added/updated/removed devices
    """
    # TODO: Implement token-based authentication
    # For now, just validate hub exists
    # In production:
    # if not authorization or not authorization.startswith("Bearer "):
    #     raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    # token = authorization.split(" ")[1]
    # Validate token against hub.api_token_hash using bcrypt

    # Validate hub_id matches X-Hub-ID header
    if x_hub_id and str(sync_data.hub_id) != x_hub_id:
        raise HTTPException(
            status_code=400,
            detail="hub_id in body does not match X-Hub-ID header"
        )

    # Convert Pydantic models to dict for service
    devices_data = [device.model_dump() for device in sync_data.devices]

    try:
        # Process device sync
        result = await hub_sync_service.process_device_sync(
            hub_id=str(sync_data.hub_id),
            devices=devices_data,
            session=db
        )

        return DeviceSyncResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Device sync failed: {str(e)}")


@router.post("/health", response_model=HubHealthResponse, status_code=200)
async def report_health(
    health_data: HubHealthReport,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, description="Bearer {hub_api_token}"),
    x_hub_id: Optional[str] = Header(None, description="Hub UUID for validation")
):
    """
    Report hub health metrics to Master Hub (Tier 1)

    This endpoint is called BY Tier 2/3 hubs every 60 seconds to report:
    - CPU, memory, disk usage
    - Temperature
    - Service status (Home Assistant, Frigate, Tailscale, etc.)

    Authentication:
    - Authorization: Bearer {hub_api_token}
    - X-Hub-ID: {hub_uuid}

    Process:
    1. Validate hub_id and auth token
    2. Update hub resource metrics in database
    3. Update service status
    4. Check for critical thresholds (auto-create work orders if needed)

    Returns:
        HubHealthResponse confirming receipt
    """
    # TODO: Implement token-based authentication (same as sync_devices)

    # Validate hub_id matches X-Hub-ID header
    if x_hub_id and str(health_data.hub_id) != x_hub_id:
        raise HTTPException(
            status_code=400,
            detail="hub_id in body does not match X-Hub-ID header"
        )

    try:
        # Get hub from database
        stmt = select(EdgeNodeModel).where(EdgeNodeModel.id == health_data.hub_id)
        result = await db.execute(stmt)
        hub = result.scalar_one_or_none()

        if not hub:
            raise HTTPException(status_code=404, detail=f"Hub {health_data.hub_id} not found")

        # Update hub metrics
        hub.cpu_usage = health_data.cpu_usage
        hub.memory_usage = health_data.memory_usage
        hub.disk_usage = health_data.disk_usage
        hub.temperature = health_data.temperature
        hub.last_heartbeat = datetime.now()

        # Update service status (stored in services JSON field)
        hub.services = health_data.services

        # Determine overall status based on metrics
        if health_data.cpu_usage > 90 or health_data.memory_usage > 90 or health_data.disk_usage > 90:
            hub.status = 'warning'
        elif health_data.temperature and health_data.temperature > 80:
            hub.status = 'warning'
        elif any(status != 'running' for status in health_data.services.values()):
            hub.status = 'error'
        else:
            hub.status = 'online'

        await db.commit()

        return HubHealthResponse(
            hub_id=str(health_data.hub_id),
            status="success",
            message=f"Health report received and processed. Hub status: {hub.status}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health report processing failed: {str(e)}")


@router.post("/trigger/{hub_id}", response_model=Dict[str, Any], status_code=200)
async def trigger_sync(
    hub_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger a device sync from a Tier 2/3 hub (Master Hub initiated)

    This endpoint is called BY the Master Hub UI to request a hub to push its devices.

    This would make an API call to the hub's /sync endpoint to trigger
    the hub to call back to POST /api/v1/sync/devices

    Args:
        hub_id: UUID of the PropertyEdgeNode to sync from

    Returns:
        Dict with response from hub
    """
    try:
        result = await hub_sync_service.trigger_sync_from_hub(str(hub_id))
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync trigger failed: {str(e)}")


@router.get("/commands", response_model=CommandsResponse, status_code=200)
async def get_commands(
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, description="Bearer {hub_api_token}"),
    x_hub_id: Optional[str] = Header(None, description="Hub UUID")
):
    """
    Get pending commands for an edge hub

    This endpoint is called BY edge hubs to poll for pending commands.
    Edge hubs poll this endpoint every 60 seconds.

    Authentication:
    - Authorization: Bearer {hub_api_token}
    - X-Hub-ID: {hub_uuid}

    Returns:
        CommandsResponse with list of pending commands
    """
    if not x_hub_id:
        raise HTTPException(status_code=400, detail="X-Hub-ID header required")

    try:
        # Get all pending commands for this hub
        stmt = select(EdgeNodeCommand).where(
            EdgeNodeCommand.hub_id == UUID(x_hub_id),
            EdgeNodeCommand.status == 'pending'
        ).order_by(EdgeNodeCommand.created_at)

        result = await db.execute(stmt)
        commands = result.scalars().all()

        # Mark commands as executing
        for cmd in commands:
            cmd.status = 'executing'

        await db.commit()

        # Convert to response format
        command_list = [
            CommandInfo(
                command_id=str(cmd.id),
                type=cmd.command_type,
                target_entity=cmd.target_entity,
                action=cmd.action,
                parameters=cmd.parameters or {}
            )
            for cmd in commands
        ]

        return CommandsResponse(commands=command_list)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get commands: {str(e)}")


@router.post("/commands/{command_id}/acknowledge", response_model=CommandAckResponse, status_code=200)
async def acknowledge_command(
    command_id: UUID,
    ack: CommandAcknowledgment,
    db: AsyncSession = Depends(get_db),
    authorization: Optional[str] = Header(None, description="Bearer {hub_api_token}"),
    x_hub_id: Optional[str] = Header(None, description="Hub UUID")
):
    """
    Acknowledge command execution from edge hub

    This endpoint is called BY edge hubs after executing a command.

    Authentication:
    - Authorization: Bearer {hub_api_token}
    - X-Hub-ID: {hub_uuid}

    Args:
        command_id: UUID of the command
        ack: CommandAcknowledgment with status and result

    Returns:
        CommandAckResponse confirming receipt
    """
    if not x_hub_id:
        raise HTTPException(status_code=400, detail="X-Hub-ID header required")

    try:
        # Get command
        stmt = select(EdgeNodeCommand).where(EdgeNodeCommand.id == command_id)
        result = await db.execute(stmt)
        command = result.scalar_one_or_none()

        if not command:
            raise HTTPException(status_code=404, detail=f"Command {command_id} not found")

        # Verify command belongs to this hub
        if str(command.hub_id) != x_hub_id:
            raise HTTPException(
                status_code=403,
                detail="Command does not belong to this hub"
            )

        # Update command status
        command.status = ack.status
        command.executed_at = datetime.now()
        command.result = ack.result or {}
        if ack.status == 'failed':
            command.error_message = ack.result.get('error', 'Unknown error')

        await db.commit()

        return CommandAckResponse(
            command_id=str(command_id),
            status="success",
            message=f"Command acknowledgment processed. Status: {ack.status}"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge command: {str(e)}")
