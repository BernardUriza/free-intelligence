"""FastAPI Dependency Injection providers for Session domain.

Provides dependency injection for session routers using FastAPI Depends().

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 - core/domain cleanup
"""

from backend.container import get_container
from backend.repositories.interfaces.itask_repository import ITaskRepository


def get_task_repository() -> ITaskRepository:
    """Get task repository from container.

    Note: This is a temporary bridge during migration.
    Eventually, this will be replaced with direct repository instantiation.

    Returns:
        ITaskRepository instance
    """
    return get_container().get_task_repository()
