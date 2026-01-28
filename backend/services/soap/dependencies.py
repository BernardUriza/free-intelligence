"""FastAPI Dependency Injection providers for SOAP service.

Provides dependency injection for routers using FastAPI Depends().

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2 (B) - Services Restantes
"""

from backend.repositories.interfaces import ITaskRepository
from backend.utils.common.infrastructure.container import get_container


def get_task_repository() -> ITaskRepository:
    """Get task repository from container.

    Note: This is a temporary bridge during migration.
    Eventually, this will be replaced with direct repository instantiation.

    Returns:
        ITaskRepository instance
    """
    return get_container().get_task_repository()
