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

from backend.services.assistant.api.public import assistant, assistant_history, assistant_websocket
from backend.core.domain.clinic.api.public import clinic_media
from backend.utils.common.logging.logger import get_logger
from backend.services.content.api.public import tv_content_seeds
from backend.services.document.api.public import documents
from infrastructure.events.api.public import events
from backend.services.evidence.api.public import evidence
from backend.services.kpi.api.public import kpis
from backend.services.memory.api.public import longitudinal_memory
from backend.core.domain.order.api.public import orders
from backend.core.domain.prescription.api.public import prescriptions
from backend.core.domain.session.api.public import sessions_list
from backend.core.domain.session.api.public import sessions_pkg as sessions
from backend.services.soap.api.public import soap
from backend.utils.system.api.public import system
from backend.services.timeline.api.public import timeline

# Import sub-routers (modular architecture following SOLIS pattern)
# Note: After migration, imports point to the new module locations
from backend.services.transcription.api.public import transcription
from backend.api.widget.api.public import widget_configs
from backend.services.workflow.api.public import waiting_room
from fastapi import APIRouter

logger = get_logger(__name__)

# Main router
router = APIRouter(prefix="/workflows/aurity", tags=["workflows-aurity"])

# ============================================================================
# Include Sub-Routers (SOLIS Pattern: Organized by functional domain)
# ============================================================================

# TRANSCRIPTION: Audio streaming and job status
router.include_router(transcription.router, tags=["Transcription"])

# SESSIONS: Lifecycle management (diarization, SOAP, finalization, monitoring)
router.include_router(sessions.router, tags=["Sessions"])

# SOAP: Clinical notes CRUD + AI assistant
router.include_router(soap.router, tags=["SOAP Notes", "AI Assistant"])

# ORDERS: Medical orders CRUD
router.include_router(orders.router, tags=["SOAP Notes"])

# PRESCRIPTIONS: Medical prescriptions template engine (FI-RX-002)
router.include_router(prescriptions.router, tags=["Prescriptions"])

# EVIDENCE: Evidence packs CRUD
router.include_router(evidence.router, tags=["Evidence Packs"])

# TIMELINE: Session history and summaries
router.include_router(timeline.router, tags=["Sessions"])

# SESSIONS LIST: Lightweight direct HDF5 read (alternative to Timeline)
router.include_router(sessions_list.router, tags=["Sessions"])

# KPIs: System metrics and performance dashboard
router.include_router(kpis.router, tags=["KPIs"])

# ASSISTANT: Free-Intelligence AI persona (onboarding, chat)
router.include_router(assistant.router, tags=["AI Assistant"])

# ASSISTANT HISTORY: Conversation history search (semantic search over embeddings)
router.include_router(assistant_history.router, tags=["AI Assistant"])

# ASSISTANT WEBSOCKET: Real-time chat sync via WebSocket
router.include_router(assistant_websocket.router, tags=["AI Assistant"])

# LONGITUDINAL MEMORY: Memoria Longitudinal (chat + audio chronologically)
router.include_router(longitudinal_memory.router, tags=["Longitudinal Memory"])

# WAITING ROOM: Dynamic content generation for TV displays
router.include_router(waiting_room.router, prefix="/waiting-room", tags=["Waiting Room"])

# CLINIC MEDIA: Multimedia upload for TV displays
router.include_router(clinic_media.router, tags=["Clinic Media"])

# TV CONTENT SEEDS: FI default content management (editable seeds)
router.include_router(tv_content_seeds.router, tags=["TV Content"])

# WIDGET CONFIGS: Configurable widget data (trivia, breathing, tips)
router.include_router(widget_configs.router, tags=["Widget Configs"])

# DOCUMENTS: Knowledge Base document upload and RAG (FI-API-FEAT-020)
router.include_router(documents.router, tags=["Knowledge Base"])

# SYSTEM: Disk usage and memory management
router.include_router(system.router, tags=["System"])

# EVENTS: Event sourcing and audit trail (append-only event store)
router.include_router(events.router, tags=["Events"])

logger.info(
    "WORKFLOWS_ROUTER_INITIALIZED",
    modules=[
        "transcription",
        "sessions",
        "soap",
        "orders",
        "prescriptions",
        "timeline",
        "sessions_list",
        "kpis",
        "assistant",
        "waiting_room",
        "clinic_media",
        "tv_content_seeds",
        "widget_configs",
        "events",
    ],
    pattern="SOLIS",
)
