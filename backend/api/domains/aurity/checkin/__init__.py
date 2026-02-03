"""Check-in Domain - Patient self-service check-in system.

FI Receptionist Check-in system for medical clinics.
Supports QR code check-in, multiple identification methods,
pending actions, and real-time waiting room updates.

Sub-modules:
- qr_code: QR code generation for TV displays
- sessions: Check-in session management
- identification: Patient identification (code, CURP, name)
- actions: Pending actions (payments, signatures, documents)
- complete: Check-in completion and queue management
- waiting_room: Real-time waiting room state and WebSocket
- conversation: Conversational AI check-in flow

Endpoints (16 total):
- POST   /qr/generate - Generate QR code
- POST   /session/start - Start session
- GET    /session/{id} - Get session state
- POST   /identify/code - Identify by code
- POST   /identify/curp - Identify by CURP
- POST   /identify/name - Identify by name
- GET    /actions/{appointment_id} - Get pending actions
- POST   /actions/{id}/complete - Complete action
- POST   /actions/{id}/skip - Skip action
- POST   /complete - Complete check-in
- GET    /waiting-room/{clinic_id} - Get waiting room state
- WS     /waiting-room/{clinic_id}/ws - WebSocket updates
- POST   /conversation/start - Start conversation
- POST   /conversation/{id}/message - Send message
- GET    /conversation/{id}/context - Get context
- DELETE /conversation/{id} - End conversation

Migrated from: backend/api/routers/checkin/checkin.py (1012 lines)
Card: FI-CHECKIN-001
Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration)
"""

from __future__ import annotations

from fastapi import APIRouter

from . import actions, complete, conversation, identification, qr_code, sessions, waiting_room

# Aggregated router for check-in domain
router = APIRouter(prefix="/checkin", tags=["Check-in"])

# QR Code: 1 endpoint
router.include_router(qr_code.router)

# Sessions: 2 endpoints
router.include_router(sessions.router)

# Identification: 3 endpoints
router.include_router(identification.router)

# Actions: 3 endpoints
router.include_router(actions.router)

# Complete: 1 endpoint
router.include_router(complete.router)

# Waiting Room: 2 endpoints (1 WebSocket)
router.include_router(waiting_room.router)

# Conversation: 4 endpoints
router.include_router(conversation.router)

__all__ = ["router"]
