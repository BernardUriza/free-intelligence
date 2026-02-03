"""Timeline Domain - Session history and longitudinal memory.

Sub-modules:
- sessions: Session CRUD and listing
- memory: Longitudinal memory (chat + audio unified timeline)

Endpoints (5 total):
- GET  /timeline/sessions - List all sessions (paginated)
- GET  /timeline/sessions/{id} - Get session details
- GET  /timeline/memory - Get longitudinal memory (paginated)
- GET  /timeline/memory/search - Search memory by text
- GET  /timeline/memory/stats - Get memory statistics

Features:
- Multi-tenancy: Sessions filtered by clinic_id
- SUPERADMIN bypass for all-clinic access
- HDF5-based session storage
- Unified timeline: "No existen sesiones. Solo una conversación infinita."

Consolidated: 2026-02 (Oceanic API Restructure - Phase Consolidation)
Migrated from: backend/services/timeline/api/public/timeline.py
             + backend/api/routers/memory/public/longitudinal_memory.py
"""

from __future__ import annotations

from fastapi import APIRouter

from . import memory, sessions

# Router with /timeline prefix (added here, not in sub-modules)
router = APIRouter(prefix="/timeline", tags=["Timeline"])
router.include_router(sessions.router)
router.include_router(memory.router)

__all__ = ["router", "sessions", "memory"]
