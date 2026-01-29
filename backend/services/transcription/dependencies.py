"""FastAPI Dependency Injection providers for Transcription service.

Provides dependency injection for routers using FastAPI Depends().
Direct repository instantiation - no service locator (Phase 4A).

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (Fix #1 - centralized config)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from pathlib import Path

from backend.domain.session import ISessionRepository
from backend.repositories.hdf5_session_repository import HDF5SessionRepository
from backend.repositories.interfaces import ITaskRepository
from backend.repositories.task_repository import HDF5TaskRepository
from backend.services.transcription.services.di_transcription_service import DITranscriptionService
from backend.utils.common.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger
from backend.config import CORPUS_PATH



def get_task_repository() -> ITaskRepository:
    """Get task repository - direct instantiation (Phase 4A).

    Returns:
        ITaskRepository instance (HDF5TaskRepository)

    Note:
        No longer uses service locator (get_container).
        Direct instantiation enables better testability and explicit dependencies.
        Referential integrity (Fix #5) is OPTIONAL - only enabled when session_repository
        is explicitly injected (not needed for most operations).
    """
    return HDF5TaskRepository(CORPUS_PATH)


def get_session_repository() -> ISessionRepository:
    """Get session repository - direct instantiation (Phase 4A).

    Returns:
        ISessionRepository instance (HDF5SessionRepository with typed dataclasses from Fix #3)

    Note:
        Migrated from legacy SessionRepository to HDF5SessionRepository (Phase 3/4A).
        Now uses typed dataclasses (SessionHDF5Metadata) instead of Dict[str, Any].
        Cascade delete (Fix #5) is OPTIONAL - only enabled when task_repository
        is explicitly injected (not needed for most operations).
    """
    return HDF5SessionRepository(CORPUS_PATH)


def get_transcription_logger() -> ILogger:
    """Get logger for transcription service.

    Returns:
        ILogger instance
    """
    return get_logger("transcription")


def get_transcription_service() -> DITranscriptionService:
    """Get transcription service with injected dependencies.

    FastAPI provider for DITranscriptionService.

    Returns:
        DITranscriptionService instance with task_repository, session_repository, and logger
    """
    return DITranscriptionService(
        task_repository=get_task_repository(),
        session_repository=get_session_repository(),
        logger=get_transcription_logger(),
    )
