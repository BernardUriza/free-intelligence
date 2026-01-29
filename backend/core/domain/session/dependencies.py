"""FastAPI Dependency Injection providers for Session domain.

Provides dependency injection for session routers using FastAPI Depends().

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - core/domain cleanup
"""

from backend.api.audit.services.audit_service import AuditService
from backend.container import get_container
from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.repositories.session_service import SessionService


def get_task_repository() -> ITaskRepository:
    """Get task repository from container.

    Note: This is a temporary bridge during migration.
    Eventually, this will be replaced with direct repository instantiation.

    Returns:
        ITaskRepository instance
    """
    return get_container().get_task_repository()


def get_corpus_repository() -> ICorpusRepository:
    """Get corpus repository from container.

    Note: This is a temporary bridge during migration.
    Eventually, this will be replaced with direct repository instantiation.

    Returns:
        ICorpusRepository instance
    """
    return get_container().get_corpus_repository()


def get_session_service() -> SessionService:
    """Get session service from container.

    Note: This is a temporary bridge during migration.
    Eventually, SessionService will use constructor injection.

    Returns:
        SessionService instance
    """
    return get_container().get_session_service()


def get_audit_service() -> AuditService:
    """Get audit service from container.

    Note: This is a temporary bridge during migration.
    Eventually, AuditService will be injected directly.

    Returns:
        AuditService instance
    """
    return get_container().get_audit_service()
