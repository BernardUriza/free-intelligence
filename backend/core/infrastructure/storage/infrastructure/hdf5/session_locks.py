"""Session-level locks for fine-grained concurrency control.

Philosophy:
  - Global lock (_h5_lock) → bottleneck for ALL sessions
  - Session lock → only serializes operations on SAME session
  - Different sessions → can write in parallel (zero contention)

Why we still need locks with session-level files:
  1. Multiple tasks of SAME session running concurrently
     (e.g., diarization + SOAP both writing to session-123.h5)
  2. Consolidation script reading session file while worker writes
  3. HDF5 is NOT thread-safe even for different groups in same file

Benefits vs global lock:
  - Session A and Session B can write in parallel
  - Only tasks within same session are serialized
  - Consolidation safely acquires per-session lock

Created: 2025-12-03
Author: Claude Code (P0.5 Concurrency Fix)
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager

import h5py
from backend.utils.common.logging.logger import get_logger
from backend.core.infrastructure.storage.infrastructure.hdf5.session_h5_manager import (
    ensure_session_h5_exists,
)

logger = get_logger(__name__)

# Per-session locks (fine-grained)
# Key: session_id → Value: RLock for that session
_session_locks: dict[str, threading.RLock] = defaultdict(threading.RLock)
_locks_lock = threading.Lock()  # Protects _session_locks dict itself


def get_session_lock(session_id: str) -> threading.RLock:
    """Get lock for specific session (thread-safe).

    Each session gets its own lock, allowing parallel operations
    on different sessions while serializing operations on the same session.

    Args:
        session_id: Session identifier

    Returns:
        RLock for that session

    Example:
        >>> lock_a = get_session_lock("session-a")
        >>> lock_b = get_session_lock("session-b")
        >>> lock_a is not lock_b  # Different sessions = different locks
        True
        >>> get_session_lock("session-a") is lock_a  # Same session = same lock
        True
    """
    with _locks_lock:
        return _session_locks[session_id]


@contextmanager
def locked_session_h5(session_id: str, mode: str = "a") -> Iterator[h5py.File]:
    """Open session HDF5 file with automatic locking.

    This is the PREFERRED way to access session HDF5 files.
    Automatically handles locking, file creation, and cleanup.

    Args:
        session_id: Session identifier
        mode: File open mode ('r', 'r+', 'a', 'w')

    Yields:
        h5py.File handle (automatically closed)

    Example:
        >>> with locked_session_h5("session-123", mode="a") as f:
        ...     f.create_dataset("/data", data=[1, 2, 3])

    Concurrency behavior:
        - Session A and Session B → write in parallel (zero contention)
        - Task 1 and Task 2 of Session A → serialized (safe)
    """
    session_lock = get_session_lock(session_id)
    session_path = ensure_session_h5_exists(session_id)

    with session_lock:
        logger.debug(
            "SESSION_H5_LOCK_ACQUIRED",
            session_id=session_id,
            mode=mode,
            path=str(session_path),
        )

        f = h5py.File(session_path, mode)
        try:
            yield f
        finally:
            f.close()
            logger.debug(
                "SESSION_H5_LOCK_RELEASED",
                session_id=session_id,
            )


def clear_session_lock(session_id: str) -> None:
    """Remove lock for session (for cleanup/testing).

    Args:
        session_id: Session identifier

    Note:
        Only use this when you're certain no operations are in progress.
    """
    with _locks_lock:
        if session_id in _session_locks:
            del _session_locks[session_id]
            logger.debug("SESSION_LOCK_CLEARED", session_id=session_id)


def get_active_locks_count() -> int:
    """Get number of active session locks (for monitoring).

    Returns:
        Number of sessions with locks allocated
    """
    with _locks_lock:
        return len(_session_locks)
