"""Internal API endpoints (localhost-only).

Atomic resources accessible only from localhost (no CORS).
In production, restricted by InternalOnlyMiddleware.

Structure:
- athletes/         → Athlete management
- coaches/          → Coach management
- sessions/         → Session CRUD + athlete sessions + designs
- diarization/      → Audio diarization
- transcribe/       → Transcription
- triage/           → Triage intake
- kpis/             → KPI aggregation
- library/          → Consultation library
- fi_diag/          → System diagnostics
- audit/            → Audit logs
- evidence/         → Evidence packs
- timeline_verify/  → Timeline verification
- exports/          → Export utilities
"""

from __future__ import annotations

from . import (
    athletes,
    audit,
    coaches,
    diarization,
    evidence,
    exports,
    fi_diag,
    kpis,
    library,
    sessions,
    timeline_verify,
    transcribe,
    triage,
)

__all__ = [
    "athletes",
    "coaches",
    "sessions",
    "diarization",
    "transcribe",
    "triage",
    "kpis",
    "library",
    "fi_diag",
    "audit",
    "evidence",
    "timeline_verify",
    "exports",
]
