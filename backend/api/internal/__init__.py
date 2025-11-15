"""Internal API endpoints (localhost-only, AURITY-only).

Atomic resources accessible only from localhost (no CORS).
In production, restricted by InternalOnlyMiddleware.

AURITY-ONLY endpoints:
- sessions/         → Session CRUD + finalize + checkpoint
- transcribe/       → Transcription (Whisper ASR)
- triage/           → Triage intake
- kpis/             → KPI aggregation
- audit/            → Audit logs
- exports/          → Export utilities

Removed (FI-STRIDE deprecated):
- athletes/ (deleted 2025-11-14)
- coaches/ (deleted 2025-11-14)
- diarization/ (deleted 2025-11-14)
- evidence/ (deleted 2025-11-14)
- fi_diag/ (deleted 2025-11-14)
- library/ (deleted 2025-11-14)
- timeline_verify/ (deleted 2025-11-14)
"""

from __future__ import annotations

from . import audit, exports, kpis, sessions, transcribe, triage

__all__ = [
    "sessions",
    "transcribe",
    "triage",
    "kpis",
    "audit",
    "exports",
]
