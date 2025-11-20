"""Session management endpoints (AURITY-only).

Contains:
- router.py → Main session CRUD
- finalize.py → Session finalization + encryption + diarization
- checkpoint.py → Incremental audio concatenation on pause

Removed (FI-STRIDE deprecated):
- athlete_sessions.py (deleted 2025-11-14)
- designs.py (deleted 2025-11-14)
"""

from __future__ import annotations

from . import checkpoint, finalize
from .router import router

__all__ = ["checkpoint", "finalize", "router"]
