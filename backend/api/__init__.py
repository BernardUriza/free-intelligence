"""API routers organized by domain.

Architecture:
- Each domain has its own directory with router.py
- Exports router via __init__.py for clean imports
- Example: from backend.api import athletes → athletes.router

Structure:
- workflows/    → Public orchestrators (CORS enabled)
- system/       → Health checks
- athletes/     → Athlete management
- coaches/      → Coach management
- sessions/     → Session tracking
- diarization/  → Audio diarization (internal)
- transcribe/   → Transcription (internal)
- triage/       → Triage intake
- katniss/      → KATNISS analysis
- kpis/         → KPI aggregation
- library/      → Resource library
- t21_resources/→ T21 resources
- fi_diag/      → Diagnostics
- audit/        → Audit logs
- evidence/     → Evidence storage
- timeline_verify/ → Timeline verification
- exports/      → Export utilities

File: backend/api/__init__.py
Updated: 2025-11-08
"""

from __future__ import annotations

# Import all routers for easy access in main.py
from . import (
    athletes,
    audit,
    coaches,
    diarization,
    evidence,
    exports,
    fi_diag,
    katniss,
    kpis,
    library,
    sessions,
    system,
    t21_resources,
    timeline_verify,
    transcribe,
    triage,
    workflows,
)

__all__ = [
    "athletes",
    "audit",
    "coaches",
    "diarization",
    "evidence",
    "exports",
    "fi_diag",
    "katniss",
    "kpis",
    "library",
    "sessions",
    "system",
    "t21_resources",
    "timeline_verify",
    "transcribe",
    "triage",
    "workflows",
]
