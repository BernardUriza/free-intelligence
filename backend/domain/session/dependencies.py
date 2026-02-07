"""FastAPI Dependency Injection providers for Session domain.

Provides dependency injection for session routers using FastAPI Depends().
Direct repository/service instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Updated: 2026-02-03 (Fix #2 - add missing get_task_repository, get_corpus_repository)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from typing import TYPE_CHECKING

from backend.services.audit.services.audit_service import AuditService

from backend.infrastructure.common.repository_singletons import (
    get_audit_repository,
    get_task_repository_singleton,
    get_corpus_repository_singleton,
)

if TYPE_CHECKING:
    from backend.repositories.interfaces.itask_repository import ITaskRepository
    from backend.repositories.interfaces.icorpus_repository import ICorpusRepository


def get_task_repository() -> "ITaskRepository":
    """Get task repository - delegates to singleton.

    Returns:
        ITaskRepository instance (HDF5TaskRepository singleton)
    """
    return get_task_repository_singleton()


def get_corpus_repository() -> "ICorpusRepository":
    """Get corpus repository - delegates to singleton.

    Returns:
        ICorpusRepository instance (CorpusRepository singleton)
    """
    return get_corpus_repository_singleton()


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
    return SessionService(repository=None)
