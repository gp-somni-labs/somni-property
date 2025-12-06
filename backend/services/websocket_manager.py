"""
WebSocket Connection Manager
Manages WebSocket connections for real-time updates
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, List, Optional
import logging
import json
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with support for:
    - User-specific connections
    - Room-based broadcasting
    - Authentication-aware messaging
    """

    def __init__(self):
        # Active connections by user ID
        self.active_connections: Dict[str, Set[WebSocket]] = {}

        # Room subscriptions (e.g., property, building, unit)
        self.rooms: Dict[str, Set[WebSocket]] = {}

        # WebSocket to user mapping
        self.connection_users: Dict[WebSocket, str] = {}

        logger.info("WebSocket ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, user_id: str):
        """
        Accept and register a new WebSocket connection

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Authenticated user ID
        """
        await websocket.accept()

        # Add to user's connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

        # Map connection to user
        self.connection_users[websocket] = user_id

        logger.info(f"WebSocket connected for user {user_id}")

        # Send welcome message
        await self.send_personal_message({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id
        }, websocket)

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection

        Args:
            websocket: FastAPI WebSocket instance
        """
        # Get user ID
        user_id = self.connection_users.get(websocket)

        if user_id:
            # Remove from user's connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            # Remove from all rooms
            for room_connections in self.rooms.values():
                room_connections.discard(websocket)

            # Remove from connection mapping
            del self.connection_users[websocket]

            logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection

        Args:
            message: Message dict to send (will be JSON serialized)
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def send_to_user(self, message: dict, user_id: str):
        """
        Send a message to all connections of a specific user

        Args:
            message: Message dict to send
            user_id: Target user ID
        """
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
                    disconnected.append(connection)

            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)

    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected clients

        Args:
            message: Message dict to send
        """
        disconnected = []
        for user_connections in self.active_connections.values():
            for connection in user_connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting: {e}")
                    disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def join_room(self, websocket: WebSocket, room: str):
        """
        Add a WebSocket connection to a room

        Args:
            websocket: WebSocket connection
            room: Room identifier (e.g., "property:uuid", "building:uuid")
        """
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(websocket)

        user_id = self.connection_users.get(websocket)
        logger.info(f"User {user_id} joined room: {room}")

        await self.send_personal_message({
            "type": "room_joined",
            "room": room,
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)

    async def leave_room(self, websocket: WebSocket, room: str):
        """
        Remove a WebSocket connection from a room

        Args:
            websocket: WebSocket connection
            room: Room identifier
        """
        if room in self.rooms:
            self.rooms[room].discard(websocket)
            if not self.rooms[room]:
                del self.rooms[room]

            user_id = self.connection_users.get(websocket)
            logger.info(f"User {user_id} left room: {room}")

    async def broadcast_to_room(self, message: dict, room: str):
        """
        Broadcast a message to all connections in a room

        Args:
            message: Message dict to send
            room: Target room identifier
        """
        if room in self.rooms:
            disconnected = []
            for connection in self.rooms[room]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to room {room}: {e}")
                    disconnected.append(connection)

            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn)

    async def send_payment_update(self, payment_id: UUID, status: str, user_id: str, amount: float):
        """
        Send a payment status update to a specific user

        Args:
            payment_id: Payment UUID
            status: New payment status
            user_id: User to notify
            amount: Payment amount
        """
        message = {
            "type": "payment_update",
            "payment_id": str(payment_id),
            "status": status,
            "amount": amount,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(message, user_id)
        logger.info(f"Sent payment update to user {user_id}: {status}")

    async def send_work_order_update(self, work_order_id: UUID, status: str, title: str, room: Optional[str] = None):
        """
        Send a work order status update

        Args:
            work_order_id: Work order UUID
            status: New status
            title: Work order title
            room: Optional room to broadcast to (e.g., "property:uuid")
        """
        message = {
            "type": "work_order_update",
            "work_order_id": str(work_order_id),
            "status": status,
            "title": title,
            "timestamp": datetime.utcnow().isoformat()
        }

        if room:
            await self.broadcast_to_room(message, room)
        else:
            await self.broadcast(message)

        logger.info(f"Sent work order update: {work_order_id} - {status}")

    async def send_iot_alert(self, alert_type: str, device_id: str, message_text: str, severity: str, room: str):
        """
        Send an IoT device alert to a room

        Args:
            alert_type: Type of alert (e.g., "water_leak", "temperature")
            device_id: Device identifier
            message_text: Alert message
            severity: Alert severity (emergency, high, normal)
            room: Room to broadcast to
        """
        message = {
            "type": "iot_alert",
            "alert_type": alert_type,
            "device_id": device_id,
            "message": message_text,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.broadcast_to_room(message, room)
        logger.warning(f"Sent IoT alert to room {room}: {alert_type}")

    def get_active_users(self) -> List[str]:
        """Get list of currently connected user IDs"""
        return list(self.active_connections.keys())

    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        return len(self.active_connections.get(user_id, set()))

    def get_room_connection_count(self, room: str) -> int:
        """Get number of connections in a room"""
        return len(self.rooms.get(room, set()))


# Global connection manager instance
manager = ConnectionManager()


async def get_ws_manager() -> ConnectionManager:
    """Dependency to get WebSocket manager"""
    return manager
