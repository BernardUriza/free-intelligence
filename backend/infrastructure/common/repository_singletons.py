"""Singleton Repository Factories - Performance Optimization.

Provides @lru_cache singleton instances for repositories that are:
- Thread-safe (HDF5 with h5py locks)
- Stateless or read-mostly
- Instantiated with same config (CORPUS_PATH)

Author: Claude Code
Created: 2026-02-02
Phase: P4-3 Performance Optimization (Holoceno Tardío)
Card: Backend Refactor - Geological Plan

Pattern: Singleton via functools.lru_cache(maxsize=1)
Benefit: Single instance shared across all endpoints (memory + performance)
"""

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.repositories.audit_repository import AuditRepository
    from backend.repositories.corpus_repository import CorpusRepository
    from backend.repositories.task_repository import HDF5TaskRepository
    from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
    from backend.repositories.interfaces.itask_repository import ITaskRepository

from backend.config import CORPUS_PATH


@lru_cache(maxsize=1)
def get_audit_repository_singleton() -> "AuditRepository":
    """Get singleton audit repository instance.

    Thread-safe: h5py handles file locking
    Stateless: Repository only performs I/O operations
    Benefit: Single AuditRepository instance shared across all endpoints

    Returns:
        AuditRepository instance (singleton)

    Usage:
        # In dependencies.py
        from backend.infrastructure.common.repository_singletons import (
            get_audit_repository_singleton
        )

        def get_audit_repository() -> AuditRepository:
            return get_audit_repository_singleton()

    Note:
        Replaces 5 duplicate definitions of get_audit_repository() across:
        - api/audit/dependencies.py
        - infrastructure/common/api/internal/exports/dependencies.py
        - domain/session/dependencies.py
        - services/llm/dependencies.py
        - services/workflow/dependencies.py
    """
    # Lazy import to avoid circular dependency
    from backend.repositories.audit_repository import AuditRepository

    return AuditRepository(CORPUS_PATH)


@lru_cache(maxsize=1)
def get_task_repository_singleton() -> "ITaskRepository":
    """Get singleton task repository instance.

    Thread-safe: h5py handles file locking
    Stateless: Repository only performs I/O operations
    Benefit: Single HDF5TaskRepository instance shared across all endpoints

    Returns:
        ITaskRepository instance (HDF5TaskRepository singleton)

    Usage:
        # In dependencies.py
        from backend.infrastructure.common.repository_singletons import (
            get_task_repository_singleton
        )

        def get_task_repository() -> ITaskRepository:
            return get_task_repository_singleton()

    Note:
        Replaces duplicate definitions of get_task_repository() in:
        - domain/session/dependencies.py
        - services/workflow/dependencies.py
    """
    # Lazy import to avoid circular dependency
    from backend.repositories.task_repository import HDF5TaskRepository

    return HDF5TaskRepository(CORPUS_PATH)


@lru_cache(maxsize=1)
def get_corpus_repository_singleton() -> "ICorpusRepository":
    """Get singleton corpus repository instance.

    Thread-safe: h5py handles file locking
    Stateless: Repository only performs I/O operations
    Benefit: Single CorpusRepository instance shared across all endpoints

    Returns:
        ICorpusRepository instance (CorpusRepository singleton)

    Usage:
        # In dependencies.py
        from backend.infrastructure.common.repository_singletons import (
            get_corpus_repository_singleton
        )

        def get_corpus_repository() -> ICorpusRepository:
            return get_corpus_repository_singleton()

    Note:
        Replaces duplicate definitions of get_corpus_repository() in:
        - domain/session/dependencies.py
        - services/workflow/dependencies.py
    """
    # Lazy import to avoid circular dependency
    from backend.repositories.corpus_repository import CorpusRepository

    return CorpusRepository(CORPUS_PATH)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SINGLETON PATTERN EXPLANATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
Why @lru_cache(maxsize=1)?
--------------------------
1. Singleton Pattern: maxsize=1 → only 1 instance cached
2. Thread-Safe: lru_cache is thread-safe (GIL protection)
3. Lazy Initialization: Instance created on first call
4. Performance: Subsequent calls return cached instance (O(1) lookup)

Example:
--------
# First call: Creates instance
repo1 = get_audit_repository_singleton()  # New AuditRepository(CORPUS_PATH)

# Second call: Returns cached instance
repo2 = get_audit_repository_singleton()  # Returns cached repo1

# Same instance
assert repo1 is repo2  # True

Memory Savings:
--------------
Before: 5 AuditRepository instances (one per dependencies.py)
After:  1 AuditRepository instance (shared singleton)
Savings: ~80% memory for repository instances

Thread Safety:
-------------
- HDF5 repositories use h5py with file-level locking
- Read operations are thread-safe
- Write operations use internal locks

When NOT to use Singleton:
-------------------------
- Repositories with mutable state per-request
- Repositories requiring different config per endpoint
- Test fixtures (override with app.dependency_overrides)
"""
