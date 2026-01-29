"""FastAPI Dependency Injection providers for Memory service.

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-28 (Phase 4A - remove unused get_container import)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

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


def get_memory_service() -> DIMemoryService:
    """Get memory service with injected dependencies.

    FastAPI provider for DIMemoryService.

    Returns:
        DIMemoryService instance with corpus_path and logger
    """
    return DIMemoryService(
        corpus_path=get_corpus_path(),
        logger=get_memory_logger(),
    )
