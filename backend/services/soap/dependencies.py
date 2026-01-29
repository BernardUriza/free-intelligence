"""FastAPI Dependency Injection providers for SOAP service.

Provides dependency injection for routers using FastAPI Depends().
Direct repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-28 (Phase 4A - eliminate get_container)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from pathlib import Path

from backend.repositories.interfaces import ITaskRepository
from backend.repositories.task_repository import HDF5TaskRepository

# Corpus path (centralized configuration)
_CORPUS_PATH = Path(__file__).parent.parent.parent.parent / "storage" / "corpus.h5"


def get_task_repository() -> ITaskRepository:
    """Get task repository - direct instantiation (Phase 4A).

    Returns:
        ITaskRepository instance (HDF5TaskRepository)

    Note:
        No longer uses service locator (get_container).
        Direct instantiation enables better testability and explicit dependencies.
    """
    return HDF5TaskRepository(_CORPUS_PATH)
