"""Clinic Media - Stub implementation returning 501 Not Implemented.

Endpoints (4 total):
- POST   /clinic-media/upload - Upload media (STUB)
- GET    /clinic-media/list - List media (STUB)
- PUT    /clinic-media/{id} - Update media (STUB)
- DELETE /clinic-media/{id} - Delete media (STUB)

Consolidated: 2026-02 (Oceanic API Restructure - Phase Consolidation)
Migrated from: backend/api/routers/clinic/public/clinic_media_stub.py
Note: Full implementation planned when storage layer is ready.
"""

from __future__ import annotations

from fastapi import APIRouter

from . import clinic_media

# Router with /clinic-media prefix (added here, not in clinic_media.py)
router = APIRouter(prefix="/clinic-media", tags=["Clinic Media"])
router.include_router(clinic_media.router)

__all__ = ["router", "clinic_media"]
