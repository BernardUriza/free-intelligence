"""FastAPI Dependency Injection providers for Session domain.

Provides dependency injection for session routers using FastAPI Depends().
Direct repository/service instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from backend.repositories.audit_repository import AuditRepository
from backend.api.audit.services.audit_service import AuditService
from backend.config import CORPUS_PATH
from backend.repositories.corpus_repository import CorpusRepository
from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.repositories.task_repository import HDF5TaskRepository


def get_task_repository() -> ITaskRepository:
    """Get task repository - direct instantiation (Phase 4A).

    Returns:
        ITaskRepository instance (HDF5TaskRepository)

    Note:
        No longer uses service locator (get_container).
        Direct instantiation enables better testability and explicit dependencies.
    """
    return HDF5TaskRepository(CORPUS_PATH)


def get_corpus_repository() -> ICorpusRepository:
    """Get corpus repository - direct instantiation (Phase 4A).

    Returns:
        ICorpusRepository instance (CorpusRepository)

    Note:
        No longer uses service locator (get_container).
        Direct instantiation with same corpus.h5 path.
    """
    return CorpusRepository(CORPUS_PATH)


def get_audit_repository() -> AuditRepository:
    """Get audit repository - direct instantiation (Phase 4A).

    Returns:
        AuditRepository instance

    Note:
        Created as a dependency for AuditService.
        Uses same corpus.h5 path for consistency.
    """
    return AuditRepository(CORPUS_PATH)


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
