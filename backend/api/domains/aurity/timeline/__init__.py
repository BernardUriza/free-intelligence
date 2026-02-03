"""Timeline Domain - Session history and longitudinal memory.

Endpoints:
- GET  /timeline/sessions - List all sessions (paginated)
- GET  /timeline/sessions/{id} - Get session details

Features:
- Multi-tenancy: Sessions filtered by clinic_id
- SUPERADMIN bypass for all-clinic access
- HDF5-based session storage

Consolidated: 2026-02 (Oceanic API Restructure - Phase Consolidation)
Migrated from: backend/services/timeline/api/public/timeline.py
"""

from __future__ import annotations

from fastapi import APIRouter

from . import sessions

# Router with /timeline prefix (added here, not in sessions.py)
router = APIRouter(prefix="/timeline", tags=["Timeline"])
router.include_router(sessions.router)

__all__ = ["router", "sessions"]
