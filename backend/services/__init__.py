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

from backend.services.audit_service import AuditService
from backend.services.session_service import SessionService
from backend.services.transcription_service import TranscriptionService

__all__ = [
    "AuditService",
    "TranscriptionService",
    "SessionService",
]
