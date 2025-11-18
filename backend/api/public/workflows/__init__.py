"""Aurity Workflows PUBLIC API - Modular Router Structure.

Exports:
- router: Main aggregated router (includes all sub-routers)
- transcription: Audio streaming and transcription jobs
- sessions: Session lifecycle management
- soap: SOAP notes CRUD + AI assistant
- orders: Medical orders CRUD
- timeline: Session history and summaries

Architecture Pattern (SOLIS):
Single Responsibility Organization with Layered Isolation Structure

Created: 2025-11-10
Refactored: 2025-11-15 (SOLIS modular architecture)
"""

from __future__ import annotations

from backend.api.public.workflows import (
    evidence,
    kpis,
    orders,
    sessions,
    soap,
    timeline,
    transcription,
)
from backend.api.public.workflows.router import router

__all__ = [
    "router",
    "transcription",
    "sessions",
    "soap",
    "orders",
    "timeline",
    "evidence",
    "kpis",
]
