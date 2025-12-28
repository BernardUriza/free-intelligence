"""Service layer for business logic.

Architecture:
  Router (HTTP) → Service (Business Logic) → Repository (Data Access)

Services:
  - TranscriptionService: Audio transcription business logic (chunk orchestration)
  - SessionService: Medical session management (all task types)

Repository Pattern:
  - All services use repository abstraction (no direct HDF5 access)
  - Dependency injection for testability
  - Clean separation of concerns

Author: Bernard Uriza Orozco
Created: 2025-11-14
Updated: 2025-11-14 (Complete Clean Architecture refactor)
Card: Clean Architecture Refactor
"""

from __future__ import annotations

from backend.src.fi_audit.services.audit_service import AuditService
from backend.src.fi_common.services.export_service import ExportService
from backend.src.fi_storage.services.corpus_service import CorpusService

# from backend.src.fi_session.services.session_service import SessionService  # Temporarily commented due to import issues
from backend.src.fi_transcription.services.transcription_service import TranscriptionService
from backend.src.fi_workflow.services.triage_service import TriageService

__all__ = [
    "AuditService",
    "CorpusService",
    "ExportService",
    # "SessionService",  # Temporarily commented due to import issues
    "TranscriptionService",
    "TriageService",
]
