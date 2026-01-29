"""FastAPI Dependency Injection providers for Export API.

Provides dependency injection for export handlers using FastAPI Depends().
Direct service instantiation - no service locator (Phase 4B).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Phase 4B - eliminate get_container)
Card: Backend Refactor Phase 4B - Complete Service Locator Elimination
"""

from pathlib import Path

from backend.api.audit.repositories.audit_repository import AuditRepository
from backend.api.audit.services.audit_service import AuditService
from backend.utils.common.services.export_service import ExportService

# Corpus path (centralized configuration)
_CORPUS_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "storage" / "corpus.h5"


def get_audit_repository() -> AuditRepository:
    """Get audit repository - direct instantiation (Phase 4B).

    Returns:
        AuditRepository instance

    Note:
        Uses centralized corpus.h5 path.
    """
    return AuditRepository(_CORPUS_PATH)


def get_audit_service() -> AuditService:
    """Get audit service - direct instantiation (Phase 4B).

    Returns:
        AuditService instance with injected AuditRepository

    Note:
        No longer uses service locator (get_container).
        Directly injects AuditRepository dependency.
    """
    return AuditService(repository=get_audit_repository())


def get_export_service() -> ExportService:
    """Get export service - direct instantiation (Phase 4B).

    Returns:
        ExportService instance with default configuration

    Note:
        No longer uses service locator (get_container).
        Uses default export_dir, signing_key, and git_commit values.
    """
    return ExportService()
