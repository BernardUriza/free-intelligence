"""FastAPI Dependency Injection providers for Memory service.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.3 - Service Refactoring
"""

from backend.container import get_container
from backend.services.memory.services.di_memory_service import DIMemoryService
from backend.utils.common.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger


def get_corpus_path() -> str:
    """Get HDF5 corpus path.

    Returns:
        Path to corpus.h5 file
    """
    # TODO: Get from config instead of hardcoded
    return "storage/corpus.h5"


def get_memory_logger() -> ILogger:
    """Get logger for memory service.

    Returns:
        ILogger instance
    """
    return get_logger("memory")


def get_memory_service(
    corpus_path: str | None = None,
    logger: ILogger | None = None,
) -> DIMemoryService:
    """Get memory service with injected dependencies.

    FastAPI provider for DIMemoryService.

    Args:
        corpus_path: HDF5 corpus path (optional, uses default)
        logger: Logger instance (optional, uses default)

    Returns:
        DIMemoryService instance
    """
    corpus_path = corpus_path or get_corpus_path()
    logger = logger or get_memory_logger()

    return DIMemoryService(
        corpus_path=corpus_path,
        logger=logger,
    )
