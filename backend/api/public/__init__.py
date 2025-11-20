"""Public API endpoints (CORS enabled, AURITY-only).

Orchestrators and public-facing endpoints accessible via CORS.

AURITY-ONLY endpoints:
- workflows/      → Aurity orchestrator (end-to-end workflows, includes timeline)
- system/         → Health checks
- patients/       → Patient CRUD (FI-DATA-DB-001)
- providers/      → Provider CRUD (FI-DATA-DB-001)
- audit/          → Audit logs (read-only, FI-UI-FEAT-206)
- assistant/      → Free-Intelligence AI assistant (persona-based conversations)

Removed (FI-STRIDE deprecated):
- katniss/ (deleted 2025-11-14)
- t21_resources/ (deleted 2025-11-14)
- tts/ (deleted 2025-11-14)
- timeline/ (moved into workflows 2025-11-15)
"""

from __future__ import annotations

from . import audit, patients, providers, system, workflows

__all__ = ["audit", "patients", "providers", "system", "workflows"]
# NOTE: assistant moved to workflows/assistant.py (AURITY-specific architecture)
