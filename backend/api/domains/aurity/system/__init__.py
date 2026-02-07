"""System Domain - Infrastructure metrics and management.

Endpoints:
- GET  /system/disk-usage - Get disk usage stats
- GET  /system/llm-status - Get LLM provider status
- POST /system/clear-memory - Clear memory cache

Features:
- Disk usage monitoring for storage directory
- LLM status checking (tunnel + local fallback)
- fi-monitor gateway integration

Consolidated: 2026-02 (Oceanic API Restructure - Phase Consolidation)
Migrated from: backend/infrastructure/system/api/public/system.py
"""

from __future__ import annotations

from fastapi import APIRouter

from . import system

# Router with /system prefix (added here, not in system.py)
router = APIRouter(prefix="/system", tags=["System"])
router.include_router(system.router)

__all__ = ["router", "system"]
