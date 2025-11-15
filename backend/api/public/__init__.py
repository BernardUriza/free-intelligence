"""Public API endpoints (CORS enabled, AURITY-only).

Orchestrators and public-facing endpoints accessible via CORS.

AURITY-ONLY endpoints:
- workflows/      → Aurity orchestrator (end-to-end workflows)
- system/         → Health checks

Removed (FI-STRIDE deprecated):
- katniss/ (deleted 2025-11-14)
- t21_resources/ (deleted 2025-11-14)
- tts/ (deleted 2025-11-14)
"""

from __future__ import annotations

from . import system, workflows

__all__ = ["workflows", "system"]
