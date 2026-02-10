"""Singleton Repository Factories - Lifecycle-managed via FastAPI Lifespan.

Provides singleton instances for repositories that are:
- Thread-safe (HDF5 with h5py locks)
- Stateless or read-mostly
- Instantiated with same config (CORPUS_PATH)

Lifecycle:
    init_repositories()     → called from FastAPI lifespan (startup)
    shutdown_repositories() → called from FastAPI lifespan (shutdown)
    get_*_repository()      → fail-fast RuntimeError if called before init

Author: Claude Code
Created: 2026-02-02
Migrated: 2026-02-07 (lru_cache → lifespan lifecycle management)
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.repositories.audit_repository import AuditRepository
    from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
    from backend.repositories.interfaces.itask_repository import ITaskRepository
    from backend.repositories.interfaces.idocument_repository import IDocumentRepository

# Module-level registry: populated by init_repositories(), cleared by shutdown_repositories()
_repos: dict[str, Any] = {}

_NOT_INITIALIZED_MSG = (
    "Repositories not initialized. "
    "Call init_repositories() first (happens automatically via FastAPI lifespan)."
)


def init_repositories() -> None:
    """Initialize all repository singletons. Called from app lifespan startup."""
    from backend.repositories.audit_repository import AuditRepository
    from backend.repositories.task import HDF5TaskRepository
    from backend.repositories.corpus_repository import CorpusRepository
    from backend.repositories.hdf5_document_repository import HDF5DocumentRepository
    from backend.config import CORPUS_PATH

    _repos["audit"] = AuditRepository(CORPUS_PATH)
    _repos["task"] = HDF5TaskRepository(CORPUS_PATH)
    _repos["corpus"] = CorpusRepository(CORPUS_PATH)
    _repos["document"] = HDF5DocumentRepository()


def shutdown_repositories() -> None:
    """Cleanup repository singletons. Called from app lifespan shutdown."""
    _repos.clear()


def get_audit_repository_singleton() -> "AuditRepository":
    """Get singleton audit repository instance.

    Returns:
        AuditRepository instance (singleton)

    Raises:
        RuntimeError: If called before init_repositories()
    """
    try:
        return _repos["audit"]
    except KeyError:
        raise RuntimeError(_NOT_INITIALIZED_MSG) from None


def get_task_repository_singleton() -> "ITaskRepository":
    """Get singleton task repository instance.

    Returns:
        ITaskRepository instance (HDF5TaskRepository singleton)

    Raises:
        RuntimeError: If called before init_repositories()
    """
    try:
        return _repos["task"]
    except KeyError:
        raise RuntimeError(_NOT_INITIALIZED_MSG) from None


def get_corpus_repository_singleton() -> "ICorpusRepository":
    """Get singleton corpus repository instance.

    Returns:
        ICorpusRepository instance (CorpusRepository singleton)

    Raises:
        RuntimeError: If called before init_repositories()
    """
    try:
        return _repos["corpus"]
    except KeyError:
        raise RuntimeError(_NOT_INITIALIZED_MSG) from None


def get_document_repository_singleton() -> "IDocumentRepository":
    """Get singleton HDF5 document repository instance.

    Returns:
        IDocumentRepository instance (HDF5DocumentRepository singleton)

    Raises:
        RuntimeError: If called before init_repositories()
    """
    try:
        return _repos["document"]
    except KeyError:
        raise RuntimeError(_NOT_INITIALIZED_MSG) from None


# Convenience aliases for FastAPI Depends()
# IMPORTANT: Import from HERE, not from individual dependencies.py files.
get_audit_repository = get_audit_repository_singleton
get_task_repository = get_task_repository_singleton
get_corpus_repository = get_corpus_repository_singleton
get_document_repository = get_document_repository_singleton

__all__ = [
    # Lifecycle management
    "init_repositories",
    "shutdown_repositories",
    # Explicit singleton names
    "get_audit_repository_singleton",
    "get_task_repository_singleton",
    "get_corpus_repository_singleton",
    "get_document_repository_singleton",
    # Short aliases for FastAPI Depends()
    "get_audit_repository",
    "get_task_repository",
    "get_corpus_repository",
    "get_document_repository",
]
