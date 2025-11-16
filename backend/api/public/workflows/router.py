"""Aurity Workflow Orchestrator - PUBLIC API (Modular Architecture).

Main router that aggregates all workflow sub-routers following SOLID principles:
- Transcription: Audio streaming and transcription jobs
- Sessions: Diarization, SOAP generation, finalization, monitoring
- SOAP: Clinical notes CRUD + AI assistant
- Orders: Medical orders CRUD
- Timeline: Session listing and history

Architecture:
  ├─ /workflows/aurity/stream → transcription.router
  ├─ /workflows/aurity/jobs/{id} → transcription.router
  ├─ /workflows/aurity/sessions/{id}/* → sessions.router
  ├─ /workflows/aurity/sessions/{id}/soap → soap.router
  ├─ /workflows/aurity/sessions/{id}/orders → orders.router
  └─ /workflows/aurity/timeline/sessions → timeline.router

Design Pattern (SOLIS - Single Responsibility Organization with Layered Isolation Structure):
- Single Responsibility: Each sub-router handles ONE functional domain
- Organization: Modular file structure prevents monolithic routers
- Layered: Clean separation between PUBLIC → SERVICE → REPOSITORY
- Isolation: Sub-routers are independent, can be tested in isolation
- Structure: Predictable layout mirrors API endpoint structure

Benefits:
- Maintainability: ~200-500 lines per file vs 2175 in monolithic
- Testability: Each module can be tested independently
- Scalability: Easy to add new workflows without touching existing code
- Clarity: Developer can find endpoints quickly by domain

Author: Bernard Uriza Orozco
Created: 2025-11-10
Refactored: 2025-11-15 (SOLIS modular architecture)
"""

from __future__ import annotations

from fastapi import APIRouter

# Import sub-routers (modular architecture following SOLIS pattern)
from backend.api.public.workflows import orders, sessions, soap, timeline, transcription
from backend.logger import get_logger

logger = get_logger(__name__)

# Main router
router = APIRouter(prefix="/workflows/aurity", tags=["workflows-aurity"])

# ============================================================================
# Include Sub-Routers (SOLIS Pattern: Organized by functional domain)
# ============================================================================

# TRANSCRIPTION: Audio streaming and job status
router.include_router(transcription.router, tags=["workflows-transcription"])

# SESSIONS: Lifecycle management (diarization, SOAP, finalization, monitoring)
router.include_router(sessions.router, tags=["workflows-sessions"])

# SOAP: Clinical notes CRUD + AI assistant
router.include_router(soap.router, tags=["workflows-soap"])

# ORDERS: Medical orders CRUD
router.include_router(orders.router, tags=["workflows-orders"])

# TIMELINE: Session history and summaries
router.include_router(timeline.router, tags=["workflows-timeline"])

logger.info(
    "WORKFLOWS_ROUTER_INITIALIZED",
    modules=["transcription", "sessions", "soap", "orders", "timeline"],
    pattern="SOLIS",
)
