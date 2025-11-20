"""
Free-Intelligence Assistant WebSocket API

Real-time chat synchronization via WebSocket.
Allows cross-device message sync without polling.

Architecture:
  - One WebSocket connection per doctor_id
  - Broadcasts new messages to all connected clients of same doctor
  - Lightweight ping/pong for connection health

Author: Bernard Uriza Orozco
Created: 2025-11-20
Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
"""

from __future__ import annotations

from typing import Dict, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# WebSocket Connection Manager
# ============================================================================


class ConnectionManager:
    """Manages WebSocket connections per doctor.

    Architecture:
        connections[doctor_id] = {websocket1, websocket2, ...}

    Each doctor can have multiple devices connected simultaneously.
    When a message is sent, broadcast to all devices of that doctor.
    """

    def __init__(self) -> None:
        # Map: doctor_id -> Set of WebSocket connections
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, doctor_id: str) -> None:
        """Accept WebSocket connection and register it."""
        await websocket.accept()

        if doctor_id not in self.connections:
            self.connections[doctor_id] = set()

        self.connections[doctor_id].add(websocket)

        logger.info(
            "WEBSOCKET_CONNECTED",
            doctor_id=doctor_id,
            total_connections=len(self.connections[doctor_id]),
        )

    def disconnect(self, websocket: WebSocket, doctor_id: str) -> None:
        """Remove WebSocket connection."""
        if doctor_id in self.connections:
            self.connections[doctor_id].discard(websocket)

            # Clean up empty sets
            if not self.connections[doctor_id]:
                del self.connections[doctor_id]

            logger.info(
                "WEBSOCKET_DISCONNECTED",
                doctor_id=doctor_id,
                remaining_connections=len(self.connections.get(doctor_id, [])),
            )

    async def broadcast(self, doctor_id: str, message: dict) -> None:
        """Broadcast message to all connections of a doctor.

        Args:
            doctor_id: Doctor identifier
            message: Message payload (will be JSON serialized)
        """
        if doctor_id not in self.connections:
            return

        # Broadcast to all connected devices
        disconnected = set()

        for connection in self.connections[doctor_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    "WEBSOCKET_SEND_FAILED",
                    doctor_id=doctor_id,
                    error=str(e),
                )
                disconnected.add(connection)

        # Clean up failed connections
        for connection in disconnected:
            self.disconnect(connection, doctor_id)

    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "total_doctors": len(self.connections),
            "total_connections": sum(len(conns) for conns in self.connections.values()),
            "doctors": {doctor_id: len(conns) for doctor_id, conns in self.connections.items()},
        }


# Singleton connection manager
manager = ConnectionManager()


# ============================================================================
# WebSocket Endpoints
# ============================================================================


class NewMessageEvent(BaseModel):
    """Event: New message sent by user."""

    type: str = "new_message"
    role: str
    content: str
    timestamp: str
    persona: str | None = None


@router.websocket("/assistant/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    doctor_id: str = Query(..., description="Doctor ID (Auth0 user.sub)"),
) -> None:
    """WebSocket endpoint for real-time chat sync.

    Client connects with doctor_id, receives real-time updates
    when messages are sent from other devices.

    Protocol:
        Client → Server: None (passive listener)
        Server → Client: {"type": "new_message", "role": "...", "content": "..."}

    Example:
        const ws = new WebSocket("wss://backend/api/workflows/aurity/assistant/ws?doctor_id=auth0|123")
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data)
            if (message.type === "new_message") {
                addMessageToUI(message)
            }
        }

    Args:
        websocket: WebSocket connection
        doctor_id: Doctor identifier (from query params)
    """
    await manager.connect(websocket, doctor_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "type": "connected",
                "doctor_id": doctor_id,
                "message": "WebSocket connected successfully",
            }
        )

        # Keep connection alive (ping/pong)
        while True:
            # Wait for client messages (if any)
            # For now, this is a passive listener - server broadcasts, client receives
            data = await websocket.receive_text()

            # Handle ping/pong for connection health
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket, doctor_id)
        logger.info("WEBSOCKET_CLIENT_DISCONNECTED", doctor_id=doctor_id)
    except Exception as e:
        logger.error(
            "WEBSOCKET_ERROR",
            doctor_id=doctor_id,
            error=str(e),
            exc_info=True,
        )
        manager.disconnect(websocket, doctor_id)


@router.get("/assistant/ws/stats")
async def get_websocket_stats() -> dict:
    """Get WebSocket connection statistics.

    Returns:
        Dict with total doctors connected, total connections, etc.
    """
    return manager.get_stats()


# ============================================================================
# Helper: Broadcast new message to all devices
# ============================================================================


async def broadcast_new_message(
    doctor_id: str,
    role: str,
    content: str,
    timestamp: str,
    persona: str | None = None,
) -> None:
    """Broadcast new message to all connected devices of a doctor.

    Call this function after storing a message in conversation_memory
    to notify all connected devices in real-time.

    Args:
        doctor_id: Doctor identifier
        role: "user" or "assistant"
        content: Message content
        timestamp: ISO timestamp
        persona: Persona used (optional)
    """
    event = NewMessageEvent(
        type="new_message",
        role=role,
        content=content,
        timestamp=timestamp,
        persona=persona,
    )

    await manager.broadcast(doctor_id, event.model_dump())

    logger.info(
        "WEBSOCKET_BROADCAST",
        doctor_id=doctor_id,
        role=role,
        content_length=len(content),
    )
