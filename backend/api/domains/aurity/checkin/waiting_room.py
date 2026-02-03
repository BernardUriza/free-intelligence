"""Waiting Room Endpoints.

GET       /checkin/waiting-room/{clinic_id} - Get waiting room state
WebSocket /checkin/waiting-room/{clinic_id}/ws - Real-time updates

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

import contextlib

from backend.database import get_db_dependency
from backend.infrastructure.auth.adapters.fastapi_adapter import User, get_current_user
from backend.infrastructure.auth.domain.entities.user import UserRole
from backend.models.checkin_models import Clinic
from backend.schemas.api.checkin import GetWaitingRoomResponse
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from .helpers import get_waiting_room_state, waiting_room_connections

logger = get_logger(__name__)

router = APIRouter(tags=["Check-in - Waiting Room"])


@router.get("/waiting-room/{clinic_id}", response_model=GetWaitingRoomResponse)
def get_waiting_room(
    clinic_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_dependency),
):
    """Get current waiting room state for a clinic.

    SECURITY (Multi-Tenancy): Requires authentication.
    Users can only access waiting room for their own clinic.
    SUPERADMIN can view any clinic (admin override).
    """
    # SECURITY: Validate user can access this clinic
    if UserRole.SUPERADMIN not in current_user.roles:
        if clinic_id != current_user.clinic_id:
            logger.error(
                "WAITING_ROOM_ACCESS_DENIED",
                requested_clinic=clinic_id,
                user_clinic=current_user.clinic_id,
                user_id=current_user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied: Cannot access waiting room for clinic '{clinic_id}'. "
                    f"You are authorized for clinic '{current_user.clinic_id}' only."
                ),
            )

    # Verify clinic exists
    clinic = db.query(Clinic).filter(Clinic.clinic_id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail=f"Clinic {clinic_id} not found")

    state = get_waiting_room_state(db, clinic_id)

    return GetWaitingRoomResponse(state=state)


@router.websocket("/waiting-room/{clinic_id}/ws")
async def waiting_room_websocket(websocket: WebSocket, clinic_id: str):
    """WebSocket endpoint for real-time waiting room updates.

    TV displays connect here to receive live updates when
    patients check in or are called.
    """
    await websocket.accept()

    # Add to connections
    if clinic_id not in waiting_room_connections:
        waiting_room_connections[clinic_id] = []
    waiting_room_connections[clinic_id].append(websocket)

    logger.info("WEBSOCKET_CONNECTED", clinic_id=clinic_id)

    try:
        # Keep connection alive
        while True:
            # Wait for messages (mainly for ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info("WEBSOCKET_DISCONNECTED", clinic_id=clinic_id)
    finally:
        # Clean up
        if clinic_id in waiting_room_connections:
            with contextlib.suppress(ValueError):
                waiting_room_connections[clinic_id].remove(websocket)
