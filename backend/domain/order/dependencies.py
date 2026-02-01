"""FastAPI Dependency Injection providers for Order domain.

Provides dependency injection for order routers using FastAPI Depends().
Direct repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from backend.config import CORPUS_PATH
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.repositories.task_repository import HDF5TaskRepository


def get_task_repository() -> ITaskRepository:
    """Get task repository - direct instantiation (Phase 4A).

    Returns:
        ITaskRepository instance (HDF5TaskRepository)

    Note:
        No longer uses service locator (get_container).
        Direct instantiation enables better testability and explicit dependencies.
        Uses centralized corpus path from backend.config.
    """
    return HDF5TaskRepository(CORPUS_PATH)
