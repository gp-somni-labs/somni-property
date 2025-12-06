"""
WebSocket API Endpoints
Real-time updates for payments, work orders, and IoT events
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from typing import Optional
import logging
import json

from services.websocket_manager import manager, get_ws_manager, ConnectionManager
from core.auth import get_auth_user, AuthUser
from core.websocket_auth import get_ws_auth_manager, WebSocketAuthManager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ws/token")
async def create_websocket_token(
    auth_user: AuthUser = Depends(get_auth_user),
    ws_auth: WebSocketAuthManager = Depends(get_ws_auth_manager)
):
    """
    Generate WebSocket authentication token

    This endpoint must be called after Authelia SSO authentication.
    Returns a short-lived token (5 minutes) that can be used to
    establish WebSocket connections.

    **Workflow:**
    1. User authenticates via Authelia (automatic)
    2. Frontend calls this endpoint to get WebSocket token
    3. Frontend connects to /ws?token={token}

    **Returns:**
    - token: WebSocket session token
    - expires_in: Token lifetime in seconds
    - username: Authenticated username
    """
    token = ws_auth.create_token(
        username=auth_user.username,
        email=auth_user.email,
        groups=auth_user.groups
    )

    return {
        "token": token,
        "expires_in": ws_auth.token_lifetime,
        "username": auth_user.username,
        "email": auth_user.email
    }


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    ws_manager: ConnectionManager = Depends(get_ws_manager),
    ws_auth: WebSocketAuthManager = Depends(get_ws_auth_manager)
):
    """
    WebSocket endpoint for real-time updates

    **Authentication:**
    1. Call POST /api/v1/ws/token to get session token
    2. Connect with token: /ws?token={your_token}
    3. Token expires after 5 minutes

    **Message Types:**
    - connection: Connection established
    - payment_update: Payment status changed
    - work_order_update: Work order status changed
    - iot_alert: IoT device alert
    - room_joined: Joined a room
    - error: Error message

    **Client Commands:**
    - join_room: {"action": "join_room", "room": "property:uuid"}
    - leave_room: {"action": "leave_room", "room": "property:uuid"}
    - ping: {"action": "ping"} -> Returns pong
    """

    # Validate WebSocket token
    session = ws_auth.validate_token(token)

    if not session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        logger.warning("WebSocket connection rejected: Invalid token")
        return

    user_id = session.username
    logger.info(f"WebSocket connection authenticated for user: {user_id}")

    try:
        # Connect WebSocket
        await ws_manager.connect(websocket, user_id)

        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                # Handle client actions
                if action == "ping":
                    await ws_manager.send_personal_message({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    }, websocket)

                elif action == "join_room":
                    room = message.get("room")
                    if room:
                        await ws_manager.join_room(websocket, room)
                    else:
                        await ws_manager.send_personal_message({
                            "type": "error",
                            "message": "Room name required"
                        }, websocket)

                elif action == "leave_room":
                    room = message.get("room")
                    if room:
                        await ws_manager.leave_room(websocket, room)
                    else:
                        await ws_manager.send_personal_message({
                            "type": "error",
                            "message": "Room name required"
                        }, websocket)

                else:
                    await ws_manager.send_personal_message({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    }, websocket)

            except json.JSONDecodeError:
                await ws_manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON"
                }, websocket)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected for user {user_id}")

    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        ws_manager.disconnect(websocket)


@router.get("/ws/stats")
async def get_websocket_stats(
    auth_user: AuthUser = Depends(get_auth_user),
    ws_manager: ConnectionManager = Depends(get_ws_manager)
):
    """
    Get WebSocket connection statistics (admin/manager only)

    Returns:
    - active_users: List of connected user IDs
    - total_connections: Total number of WebSocket connections
    - rooms: Active rooms with connection counts
    """
    if not (auth_user.is_admin or auth_user.is_manager):
        return {"error": "Unauthorized"}

    active_users = ws_manager.get_active_users()
    total_connections = sum(
        ws_manager.get_user_connection_count(user_id)
        for user_id in active_users
    )

    # Get room stats
    room_stats = {}
    for room in ws_manager.rooms.keys():
        room_stats[room] = ws_manager.get_room_connection_count(room)

    return {
        "active_users": active_users,
        "total_connections": total_connections,
        "unique_users": len(active_users),
        "rooms": room_stats,
        "room_count": len(room_stats)
    }
