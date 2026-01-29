"""FastAPI Dependency Injection providers for Memory service.

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-29 (TODO cleanup - use centralized config)
Card: Backend Refactor Phase 4A - Eliminate Service Locator
"""

from backend.config import CORPUS_PATH
from backend.services.memory.services.di_memory_service import DIMemoryService
from backend.utils.common.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger


def get_corpus_path() -> str:
    """Get HDF5 corpus path from centralized config.

    Returns:
        Path to corpus.h5 file as string
    """
    return str(CORPUS_PATH)


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
