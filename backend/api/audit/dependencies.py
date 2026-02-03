"""FastAPI Dependency Injection providers for Audit API.

Provides dependency injection for routers using FastAPI Depends().
Direct service instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Updated: 2026-02-02 (Architecture fix: Moved audit services to services/)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.repositories.audit_repository import AuditRepository

from backend.services.audit.services.di_audit_service import DIAuditService
from backend.infrastructure.common.repository_singletons import (
    get_audit_repository_singleton,
)
from backend.utils.common.logging.logger import get_logger


def get_audit_repository() -> "AuditRepository":
    """Get audit repository - singleton instance (Phase 4A + P4-3).

    Returns:
        AuditRepository singleton (shared across all endpoints)

    Note:
        Performance optimization: Uses @lru_cache singleton instead of
        creating new instance per request. Thread-safe via h5py locks.
    """
    return get_audit_repository_singleton()


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
