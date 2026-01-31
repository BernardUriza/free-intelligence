"""FastAPI Dependency Injection providers for Memory service.

Author: Claude Code
Created: 2026-01-28
Updated: 2026-01-31 (Phase 2.4 - IMemoryStore injection)
Card: DI Refactor Phase 2.4 - Memory Service DI
"""

from backend.config import CORPUS_PATH
from backend.repositories.hdf5_memory_store import HDF5MemoryStore
from backend.repositories.interfaces.imemory_store import IMemoryStore
from backend.services.memory.services.di_memory_service import DIMemoryService
from backend.infrastructure.interfaces.ilogger import ILogger
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


def get_memory_store() -> IMemoryStore:
    """Get memory store implementation (HDF5-based).

    Returns:
        IMemoryStore instance (HDF5MemoryStore)
    """
    return HDF5MemoryStore(
        corpus_path=get_corpus_path(),
        logger=get_memory_logger(),
    )


def get_memory_service() -> DIMemoryService:
    """Get memory service with injected dependencies.

    FastAPI provider for DIMemoryService.

    Returns:
        DIMemoryService instance with memory_store and logger

    Clean Architecture:
        Router → DIMemoryService (business logic) → IMemoryStore (interface) → HDF5MemoryStore (implementation)
    """
    return DIMemoryService(
        memory_store=get_memory_store(),
        logger=get_memory_logger(),
    )
