#!/usr/bin/env python3
"""Timeline Verify API Router.

Timeline hash verification for sessions and events.

File: backend/api/timeline_verify/router.py
Card: FI-API-FEAT-003
Reorganized: 2025-11-08 (moved from backend/api/timeline_verify.py)

Endpoints:
- POST /api/timeline/verify-hash -> Verify session/event hashes (batch support)
"""

from __future__ import annotations

from backend.api.internal.timeline_verify import router

__all__ = ["router"]
