"""FastAPI Dependency Injection providers for Audit API.

Provides dependency injection for routers using FastAPI Depends().
Direct service instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-28 (Phase 4A - eliminate get_container)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from pathlib import Path

from backend.api.audit.repositories.audit_repository import AuditRepository
from backend.api.audit.services.audit_service import AuditService

# Corpus path (centralized configuration)
_CORPUS_PATH = Path(__file__).parent.parent.parent / "storage" / "corpus.h5"


def get_audit_repository() -> AuditRepository:
    """Get audit repository - direct instantiation (Phase 4A).

    Returns:
        AuditRepository instance

    Note:
        Uses centralized corpus.h5 path.
    """
    return AuditRepository(_CORPUS_PATH)


def get_audit_service() -> AuditService:
    """Get audit service - direct instantiation (Phase 4A).

    Returns:
        AuditService instance with injected AuditRepository

    Note:
        No longer uses service locator (get_container).
        Directly injects AuditRepository dependency.
    """
    return AuditService(repository=get_audit_repository())
