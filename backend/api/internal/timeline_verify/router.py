"""Timeline Verify API Router.

Timeline hash verification

File: backend/api/timeline_verify/router.py
Reorganized: 2025-11-08 (moved from backend/api/timeline_verify.py)
"""

from __future__ import annotations

#!/usr/bin/env python3
"""
Free Intelligence - Timeline Verify API

FastAPI router for hash verification of sessions and events.

File: backend/api/timeline_verify.py
Card: FI-API-FEAT-003
Created: 2025-11-03

Endpoints:
- POST /api/timeline/verify-hash -> Verify session/event hashes (batch support)
"""

from __future__ import annotations

from backend.api.internal.timeline_verify import router

__all__ = ["router"]
