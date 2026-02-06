"""Free-Intelligence Assistant WebSocket API.

Real-time chat synchronization via WebSocket.
Allows cross-device message sync without polling.

Architecture:
  - One WebSocket connection per doctor_id
  - Broadcasts new messages to all connected clients of same doctor
  - Lightweight ping/pong for connection health
  - JWT auth required via query param

Endpoints (2 total):
- WS  /ws - WebSocket connection for real-time sync
- GET /ws/stats - Connection statistics

Author: Bernard Uriza Orozco
Created: 2025-11-20
Migrated: 2026-02-03 (Domain Migration)
Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.infrastructure.auth import UserRole
from backend.infrastructure.auth.infrastructure.middleware.auth_middleware import get_auth_provider
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


async def _validate_websocket_auth(token: str | None, doctor_id: str) -> bool:
    """Validate WebSocket JWT token and doctor_id access.

    Returns True if valid, False otherwise.
    SUPERADMIN can access any doctor_id.
    """
    if not token:
        return False

    try:
        provider = get_auth_provider()
        payload = await provider.token_service.validate(token)

        # SUPERADMIN can access any doctor
        if UserRole.SUPERADMIN in payload.roles:
            return True

        # Regular user: must match doctor_id
        return payload.subject == doctor_id

    except ValueError:
        return False


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
        self.connections: dict[str, set[WebSocket]] = {}

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

            if not self.connections[doctor_id]:
                del self.connections[doctor_id]

            logger.info(
                "WEBSOCKET_DISCONNECTED",
                doctor_id=doctor_id,
                remaining_connections=len(self.connections.get(doctor_id, [])),
            )

    async def broadcast(self, doctor_id: str, message: dict) -> None:
        """Broadcast message to all connections of a doctor."""
        if doctor_id not in self.connections:
            return

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
# Models
# ============================================================================


class NewMessageEvent(BaseModel):
    """Event: New message sent by user."""

    type: str = "new_message"
    role: str
    content: str
    timestamp: str
    persona: str | None = None
    model: str | None = None


# ============================================================================
# Endpoints
# ============================================================================


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    doctor_id: str = Query(..., description="Doctor ID (JWT user.sub)"),
    token: str | None = Query(None, description="JWT access token for auth"),
    audit_service: DIAuditService = Depends(get_audit_service),
) -> None:
    """WebSocket endpoint for real-time chat sync.

    Client connects with doctor_id and JWT token, receives real-time updates
    when messages are sent from other devices.

    Auth:
        Requires valid JWT token as query param.
        User can only connect to their own doctor_id (SUPERADMIN can connect to any).

    Protocol:
        Client → Server: "ping" for keepalive
        Server → Client: {"type": "new_message", "role": "...", "content": "..."}

    Example:
        const ws = new WebSocket("wss://backend/api/aurity/assistant/ws?doctor_id=user-123&token=eyJ...")
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data)
            if (message.type === "new_message") {
                addMessageToUI(message)
            }
        }
    """
    # Validate auth before accepting connection
    if not await _validate_websocket_auth(token, doctor_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning(
            "WEBSOCKET_AUTH_FAILED",
            doctor_id=doctor_id,
            has_token=bool(token),
        )
        return

    await manager.connect(websocket, doctor_id)

    try:
        await websocket.send_json(
            {
                "type": "connected",
                "doctor_id": doctor_id,
                "message": "WebSocket connected successfully",
            }
        )

        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket, doctor_id)
        logger.info("WEBSOCKET_CLIENT_DISCONNECTED", doctor_id=doctor_id)
    except Exception as e:
        audit_service.log_action(
            action="websocket_error",
            user_id=doctor_id,
            resource="websocket_connection",
            result="failure",
            details={"error": str(e)},
        )
        manager.disconnect(websocket, doctor_id)


@router.get("/ws/stats")
async def get_websocket_stats() -> dict:
    """Get WebSocket connection statistics."""
    return manager.get_stats()


# ============================================================================
# Helper: Broadcast new message (used by infrastructure/llm)
# ============================================================================


async def broadcast_new_message(
    doctor_id: str,
    role: str,
    content: str,
    timestamp: str,
    persona: str | None = None,
    model: str | None = None,
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
        model: LLM model that generated the response (optional)
    """
    event = NewMessageEvent(
        type="new_message",
        role=role,
        content=content,
        timestamp=timestamp,
        persona=persona,
        model=model,
    )

    await manager.broadcast(doctor_id, event.model_dump())

    logger.info(
        "WEBSOCKET_BROADCAST",
        doctor_id=doctor_id,
        role=role,
        content_length=len(content),
    )
