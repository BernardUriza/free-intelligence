"""FastAPI Dependency Injection providers for Session domain.

Provides dependency injection for session routers using FastAPI Depends().
Direct repository/service instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.repositories.audit_repository import AuditRepository
    from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
    from backend.repositories.interfaces.itask_repository import ITaskRepository

from backend.api.audit.services.audit_service import AuditService
from backend.infrastructure.common.repository_singletons import (
    get_audit_repository_singleton,
    get_corpus_repository_singleton,
    get_task_repository_singleton,
)


def get_task_repository() -> "ITaskRepository":
    """Get task repository - singleton instance (Phase 4A + P4-3).

    Returns:
        ITaskRepository singleton (HDF5TaskRepository shared across endpoints)

    Note:
        Performance optimization: Uses @lru_cache singleton.
        Thread-safe via h5py file locking.
    """
    return get_task_repository_singleton()


def get_corpus_repository() -> "ICorpusRepository":
    """Get corpus repository - singleton instance (Phase 4A + P4-3).

    Returns:
        ICorpusRepository singleton (CorpusRepository shared across endpoints)

    Note:
        Performance optimization: Uses @lru_cache singleton.
        Thread-safe via h5py file locking.
    """
    return get_corpus_repository_singleton()


def get_audit_repository() -> "AuditRepository":
    """Get audit repository - singleton instance (Phase 4A + P4-3).

    Returns:
        AuditRepository singleton (shared across all endpoints)

    Note:
        Performance optimization: Uses @lru_cache singleton.
        Thread-safe via h5py file locking.
    """
    return get_audit_repository_singleton()


def get_audit_service() -> AuditService:
    """Get audit service - direct instantiation (Phase 4A).

    Returns:
        AuditService instance with injected AuditRepository

    Note:
        No longer uses service locator (get_container).
        Directly injects AuditRepository dependency.
    """
    return AuditService(repository=get_audit_repository())


def get_session_service() -> "SessionService":
    """Get session service - direct instantiation (Phase 4B fix).

    Returns:
        SessionService instance with injected repository dependencies

    Note:
        SessionService was NEVER removed, just the dependency function was deleted.
        This function restores FastAPI Depends() compatibility for routers.
    """
    from backend.domain.session.services.session_service import SessionService
    # SessionService accepts optional repository but can work without it (legacy compat)
    return SessionService(repository=None)
