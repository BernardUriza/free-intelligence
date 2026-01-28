"""FastAPI Dependency Injection providers for Transcription service.

Provides dependency injection for routers using FastAPI Depends().

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from backend.container import get_container
from backend.repositories.interfaces import ITaskRepository
from backend.services.transcription.services.di_transcription_service import DITranscriptionService
from backend.utils.common.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger


def get_task_repository() -> ITaskRepository:
    """Get task repository from container.

    Note: This is a temporary bridge during migration.
    Eventually, this will be replaced with direct repository instantiation.

    Returns:
        ITaskRepository instance
    """
    return get_container().get_task_repository()


def get_transcription_logger() -> ILogger:
    """Get logger for transcription service.

    Returns:
        ILogger instance
    """
    return get_logger("transcription")


def get_transcription_service(
    task_repo: ITaskRepository = None,
    logger: ILogger = None,
) -> DITranscriptionService:
    """Get transcription service with injected dependencies.

    FastAPI provider for DITranscriptionService.

    Args:
        task_repo: Task repository (injected by FastAPI)
        logger: Logger instance (injected by FastAPI)

    Returns:
        DITranscriptionService instance
    """
    # Use provided dependencies or get from container (temporary bridge)
    task_repo = task_repo or get_task_repository()
    logger = logger or get_transcription_logger()

    return DITranscriptionService(
        task_repository=task_repo,
        logger=logger,
    )
