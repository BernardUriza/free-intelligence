"""FastAPI Dependency Injection providers for Audit API.

Provides dependency injection for routers using FastAPI Depends().
Direct service instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from backend.repositories.audit_repository import AuditRepository
from backend.api.audit.services.di_audit_service import DIAuditService
from backend.config import CORPUS_PATH
from backend.utils.common.logging.logger import get_logger


def get_audit_repository() -> AuditRepository:
    """Get audit repository - direct instantiation (Phase 4A).

    Returns:
        AuditRepository instance

    Note:
        Uses centralized corpus.h5 path from backend.config.
    """
    return AuditRepository(CORPUS_PATH)


def get_audit_service() -> DIAuditService:
    """Get audit service - direct instantiation (Phase 4A).

    Returns:
        DIAuditService instance with injected AuditRepository and logger

    Note:
        No longer uses service locator (get_container).
        Directly injects AuditRepository and logger dependencies.
        Uses DIAuditService for multi-tenancy support (clinic_id).
    """
    logger = get_logger(__name__)
    return DIAuditService(logger=logger, repository=get_audit_repository())
