"""
Somni Property Manager - HA Terminal WebSocket API

Provides interactive SSH terminal access to Home Assistant instances
via WebSocket for the unified Flutter app (SomniHome).
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db, AsyncSessionLocal
from core.websocket_auth import get_ws_auth_manager, WebSocketAuthManager

logger = logging.getLogger(__name__)
router = APIRouter()

# SSH Configuration
SSH_KEY_PATH = os.environ.get("HA_SSH_KEY_PATH", "/etc/secrets/ha-master-key/id_rsa")
SSH_TIMEOUT = int(os.environ.get("HA_SSH_TIMEOUT", "30"))


class SSHTerminalSession:
    """
    Manages an interactive SSH session for a single WebSocket connection.
    Uses asyncio subprocess for SSH communication.
    """

    def __init__(
        self,
        host: str,
        user: str,
        port: int,
        websocket: WebSocket,
        instance_id: str,
        username: str
    ):
        self.host = host
        self.user = user
        self.port = port
        self.websocket = websocket
        self.instance_id = instance_id
        self.username = username
        self.process: Optional[asyncio.subprocess.Process] = None
        self.connected = False
        self.started_at: Optional[datetime] = None

    async def connect(self) -> bool:
        """Establish SSH connection."""
        try:
            # Build SSH command with PTY allocation
            ssh_cmd = [
                "ssh",
                "-tt",  # Force PTY allocation (required for interactive)
                "-i", SSH_KEY_PATH,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", f"ConnectTimeout={SSH_TIMEOUT}",
                "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=3",
                f"{self.user}@{self.host}",
                "-p", str(self.port)
            ]

            logger.info(f"Opening SSH session to {self.user}@{self.host}:{self.port}")

            self.process = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # Merge stderr into stdout
            )

            self.connected = True
            self.started_at = datetime.now(timezone.utc)

            # Notify client of successful connection
            await self.websocket.send_json({
                "type": "connected",
                "instance_id": self.instance_id,
                "host": self.host,
                "timestamp": self.started_at.isoformat()
            })

            return True

        except Exception as e:
            logger.error(f"Failed to establish SSH connection: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": f"SSH connection failed: {str(e)}"
            })
            return False

    async def send_input(self, data: str):
        """Send input to SSH process."""
        if self.process and self.process.stdin:
            try:
                self.process.stdin.write(data.encode())
                await self.process.stdin.drain()
            except Exception as e:
                logger.error(f"Failed to send SSH input: {e}")
                await self.websocket.send_json({
                    "type": "error",
                    "message": f"Failed to send input: {str(e)}"
                })

    async def read_output(self):
        """Read output from SSH process and forward to WebSocket."""
        if not self.process or not self.process.stdout:
            return

        try:
            while self.connected and not self.process.stdout.at_eof():
                try:
                    # Read available data with timeout
                    data = await asyncio.wait_for(
                        self.process.stdout.read(4096),
                        timeout=0.1
                    )

                    if data:
                        # Send output to WebSocket as text
                        await self.websocket.send_json({
                            "type": "output",
                            "data": data.decode("utf-8", errors="replace")
                        })

                except asyncio.TimeoutError:
                    # No data available, continue polling
                    await asyncio.sleep(0.05)

        except Exception as e:
            if self.connected:
                logger.error(f"SSH output read error: {e}")
                await self.websocket.send_json({
                    "type": "error",
                    "message": f"SSH output error: {str(e)}"
                })

    async def resize(self, rows: int, cols: int):
        """
        Resize terminal (for PTY resize events).
        Note: This requires more advanced PTY handling.
        For now, we log the request.
        """
        logger.debug(f"Terminal resize requested: {rows}x{cols}")
        # TODO: Implement PTY resize using stty or escape sequences

    async def close(self):
        """Close SSH session."""
        self.connected = False

        if self.process:
            try:
                # Send exit command
                if self.process.stdin:
                    self.process.stdin.write(b"exit\n")
                    await self.process.stdin.drain()

                # Wait briefly for clean exit
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    # Force kill
                    self.process.kill()
                    await self.process.wait()

            except Exception as e:
                logger.debug(f"Error closing SSH session: {e}")

        # Calculate session duration
        duration = 0
        if self.started_at:
            duration = int((datetime.now(timezone.utc) - self.started_at).total_seconds())

        logger.info(
            f"SSH session closed for {self.username} on {self.host} "
            f"(duration: {duration}s)"
        )


@router.websocket("/{instance_id}/terminal")
async def ha_terminal_websocket(
    websocket: WebSocket,
    instance_id: UUID,
    token: Optional[str] = Query(None),
    ws_auth: WebSocketAuthManager = Depends(get_ws_auth_manager)
):
    """
    Interactive SSH terminal to Home Assistant instance.

    **Authentication:**
    1. Call POST /api/v1/ws/token to get session token
    2. Connect with token: /api/v1/ha-instances/{id}/terminal?token={token}

    **WebSocket Protocol:**

    Server -> Client messages:
    - {"type": "connected", "instance_id": "...", "host": "...", "timestamp": "..."}
    - {"type": "output", "data": "terminal output text"}
    - {"type": "error", "message": "error description"}
    - {"type": "disconnected", "reason": "..."}

    Client -> Server messages:
    - {"action": "input", "data": "text to send to terminal"}
    - {"action": "resize", "rows": 24, "cols": 80}
    - {"action": "ping"} -> Returns {"type": "pong"}

    **Quick Commands (convenience):**
    - {"action": "command", "cmd": "ha core restart"} - Send command + Enter
    - {"action": "command", "cmd": "ha core update"} - Send command + Enter

    **Connection Lifecycle:**
    1. WebSocket connects with valid token
    2. Server validates token and user permissions
    3. Server looks up HA instance in database
    4. Server opens SSH connection to instance
    5. Bidirectional data flow between client and SSH
    6. On disconnect, SSH session is cleanly closed
    """
    # Validate WebSocket token
    session = ws_auth.validate_token(token)

    if not session:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token"
        )
        logger.warning(f"Terminal connection rejected: Invalid token for instance {instance_id}")
        return

    # Check user permissions (must be admin or manager)
    user_groups = session.groups or []
    is_authorized = (
        "admin" in user_groups or
        "manager" in user_groups or
        "administrators" in user_groups or
        "managers" in user_groups
    )

    if not is_authorized:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Insufficient permissions for terminal access"
        )
        logger.warning(
            f"Terminal access denied for user {session.username}: "
            f"groups={user_groups}"
        )
        return

    # Accept WebSocket connection
    await websocket.accept()

    logger.info(f"Terminal connection accepted for user {session.username}")

    # Look up HA instance
    async with AsyncSessionLocal() as db:
        from db.models import HAInstance

        result = await db.execute(
            select(HAInstance).where(HAInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()

        if not instance:
            await websocket.send_json({
                "type": "error",
                "message": f"HA Instance not found: {instance_id}"
            })
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            return

        if not instance.is_enabled:
            await websocket.send_json({
                "type": "error",
                "message": "HA Instance is disabled"
            })
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            return

        # Create SSH session
        ssh_session = SSHTerminalSession(
            host=instance.host,
            user=instance.ssh_user,
            port=instance.ssh_port,
            websocket=websocket,
            instance_id=str(instance_id),
            username=session.username
        )

    # Connect SSH
    if not await ssh_session.connect():
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    # Start output reader task
    output_task = asyncio.create_task(ssh_session.read_output())

    try:
        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                action = message.get("action")

                if action == "input":
                    # Send raw input to SSH
                    input_data = message.get("data", "")
                    await ssh_session.send_input(input_data)

                elif action == "command":
                    # Send command with newline
                    cmd = message.get("cmd", "")
                    await ssh_session.send_input(cmd + "\n")

                elif action == "resize":
                    # Handle terminal resize
                    rows = message.get("rows", 24)
                    cols = message.get("cols", 80)
                    await ssh_session.resize(rows, cols)

                elif action == "ping":
                    # Keepalive ping
                    await websocket.send_json({"type": "pong"})

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON message"
                })

    except WebSocketDisconnect:
        logger.info(f"Terminal WebSocket disconnected for user {session.username}")

    except Exception as e:
        logger.error(f"Terminal WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Connection error: {str(e)}"
            })
        except:
            pass

    finally:
        # Cancel output reader
        output_task.cancel()
        try:
            await output_task
        except asyncio.CancelledError:
            pass

        # Close SSH session
        await ssh_session.close()

        # Send disconnect message
        try:
            await websocket.send_json({
                "type": "disconnected",
                "reason": "Session closed"
            })
        except:
            pass


@router.post("/{instance_id}/terminal/command")
async def execute_terminal_command(
    instance_id: UUID,
    command: str = Query(..., description="Command to execute"),
    timeout: int = Query(30, ge=5, le=300, description="Command timeout in seconds"),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a single command on HA instance (non-interactive).

    This is a REST alternative to WebSocket for simple commands.
    Returns stdout, stderr, and exit code.

    **Note:** For interactive sessions, use the WebSocket endpoint.

    **Common commands:**
    - ha core info
    - ha core restart
    - ha core update
    - ha supervisor info
    - ha host reboot
    """
    from db.models import HAInstance
    from services.ha_instance_service import HAInstanceService
    from core.auth import require_admin, get_auth_user

    # This endpoint requires admin auth (would be injected via dependency)
    # For now, we rely on Authelia middleware for authentication

    # Get instance
    result = await db.execute(
        select(HAInstance).where(HAInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()

    if not instance:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="HA Instance not found")

    # Execute command
    ha_service = HAInstanceService()
    exec_result = await ha_service.execute_ssh_command(
        instance=instance,
        command=command,
        timeout=timeout
    )

    return {
        "instance_id": str(instance_id),
        "instance_name": instance.name,
        "command": command,
        "stdout": exec_result["stdout"],
        "stderr": exec_result["stderr"],
        "exit_code": exec_result["exit_code"],
        "success": exec_result["success"],
        "executed_at": datetime.now(timezone.utc).isoformat()
    }
