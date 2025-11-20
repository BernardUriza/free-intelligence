"""Synchronous worker functions (replaces Celery tasks).

DEPRECATED: Use backend.workers.tasks.* modules instead.

This file is kept for backward compatibility only.
Imports are re-exported from modular task implementations.

Created: 2025-11-15
Refactored: 2025-11-15 (DRY, Python 3.14 best practices)
"""

from __future__ import annotations

# Re-export from modular implementations
from backend.workers.tasks.audit_worker import log_audit_event_worker
from backend.workers.tasks.diarization_worker import diarize_session_worker
from backend.workers.tasks.soap_worker import generate_soap_worker
from backend.workers.tasks.transcription_worker import transcribe_chunk_worker

__all__ = [
    "diarize_session_worker",
    "generate_soap_worker",
    "log_audit_event_worker",
    "transcribe_chunk_worker",
]
