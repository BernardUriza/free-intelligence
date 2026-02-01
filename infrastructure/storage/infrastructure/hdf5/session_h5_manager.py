"""Session-Level HDF5 Manager - Zero Concurrency Conflicts Architecture.

Philosophy:
  - 1 Session = 1 HDF5 File
  - Each worker writes to its own session file
  - No locks needed (no shared file access)
  - Consolidation to corpus.h5 happens lazily (offline or async)

Benefits:
  - ✅ Zero concurrency conflicts (workers don't share files)
  - ✅ Scalable to 100+ concurrent workers
  - ✅ Fault isolation (corrupted session doesn't affect others)
  - ✅ Append-only by design
  - ✅ Simplified code (no locks, no SWMR complexity)

Migration Strategy:
  - New sessions → session-level files
  - Existing sessions in corpus.h5 → read-only (backward compatible)
  - Consolidation → merge session files into corpus.h5 periodically

Created: 2025-12-03
Author: Claude Code (P0 Architecture Fix)
Pattern: Session-Isolated Storage
"""

from __future__ import annotations

import h5py
from backend.utils.common.logging.logger import get_logger
from pathlib import Path

logger = get_logger(__name__)

# Storage paths
STORAGE_DIR = Path(__file__).parent.parent.parent / "storage"
CORPUS_PATH = STORAGE_DIR / "corpus.h5"
SESSIONS_DIR = STORAGE_DIR / "sessions"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SESSION-LEVEL FILE MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_session_h5_path(session_id: str) -> Path:
    """Get path to session-specific HDF5 file.

    Each session gets its own HDF5 file to eliminate concurrency conflicts.

    Args:
        session_id: Session identifier

    Returns:
        Path to session HDF5 file (storage/sessions/{session_id}.h5)

    Example:
        >>> path = get_session_h5_path("abc-123-def")
        >>> print(path)
        storage/sessions/abc-123-def.h5
    """
    return SESSIONS_DIR / f"{session_id}.h5"


def session_h5_exists(session_id: str) -> bool:
    """Check if session HDF5 file exists.

    Args:
        session_id: Session identifier

    Returns:
        True if session file exists, False otherwise
    """
    return get_session_h5_path(session_id).exists()


def ensure_session_h5_exists(session_id: str) -> Path:
    """Create session HDF5 file if it doesn't exist.

    Initializes the file with the session root group.

    Args:
        session_id: Session identifier

    Returns:
        Path to session HDF5 file

    Note:
        This operation is idempotent - safe to call multiple times.
    """
    path = get_session_h5_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        logger.info(
            "SESSION_H5_CREATE",
            session_id=session_id,
            path=str(path),
        )
        with h5py.File(path, "w") as f:
            # Create root session group
            session_group = f.create_group(f"/sessions/{session_id}")
            # Initialize metadata
            session_group.attrs["session_id"] = session_id
            session_group.attrs["created_at"] = str(Path(__file__).stat().st_ctime)

    return path


def get_session_file_size(session_id: str) -> int:
    """Get size of session HDF5 file in bytes.

    Args:
        session_id: Session identifier

    Returns:
        File size in bytes, or 0 if file doesn't exist
    """
    path = get_session_h5_path(session_id)
    if path.exists():
        return path.stat().st_size
    return 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSOLIDATION - Merge session files into corpus.h5
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def consolidate_session_to_corpus(session_id: str, delete_after: bool = True) -> bool:
    """Consolidate session HDF5 file into main corpus.h5.

    Copies all data from session file to corpus, then optionally deletes session file.

    Args:
        session_id: Session identifier
        delete_after: If True, delete session file after successful consolidation

    Returns:
        True if consolidation succeeded, False otherwise

    Raises:
        FileNotFoundError: If session file doesn't exist
        ValueError: If session data already exists in corpus

    Example:
        >>> consolidate_session_to_corpus("abc-123", delete_after=True)
        True
    """
    session_path = get_session_h5_path(session_id)

    if not session_path.exists():
        raise FileNotFoundError(f"Session file not found: {session_path}")

    # Ensure corpus file exists
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CORPUS_PATH.exists():
        logger.info("CORPUS_CREATE", path=str(CORPUS_PATH))
        with h5py.File(CORPUS_PATH, "w") as f:
            f.create_group("/sessions")

    logger.info(
        "CONSOLIDATION_START",
        session_id=session_id,
        session_file=str(session_path),
        corpus_file=str(CORPUS_PATH),
    )

    try:
        # Copy session data to corpus
        with h5py.File(session_path, "r") as src, h5py.File(CORPUS_PATH, "a") as dst:
            session_group_path = f"/sessions/{session_id}"

            # Check if already exists in corpus
            if session_group_path in dst:
                raise ValueError(
                    f"Session {session_id} already exists in corpus. "
                    "Use force=True to overwrite or delete_after=False to keep session file."
                )

            # Copy entire session tree
            src.copy(session_group_path, dst["/sessions"], name=session_id)

            logger.info(
                "CONSOLIDATION_COPY_SUCCESS",
                session_id=session_id,
                groups_copied=len(list(dst[session_group_path].keys())),
            )

        # Delete session file after successful consolidation
        if delete_after:
            session_path.unlink()
            logger.info(
                "CONSOLIDATION_CLEANUP_SUCCESS",
                session_id=session_id,
                deleted=str(session_path),
            )

        logger.info("CONSOLIDATION_SUCCESS", session_id=session_id)
        return True

    except Exception as e:
        logger.error(
            "CONSOLIDATION_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        return False


def consolidate_all_sessions(max_sessions: int | None = None) -> dict[str, int]:
    """Consolidate all session files into corpus.h5.

    Args:
        max_sessions: Maximum number of sessions to consolidate (None = all)

    Returns:
        Dict with consolidation stats:
            - success: Number of successfully consolidated sessions
            - failed: Number of failed consolidations
            - skipped: Number of skipped sessions

    Example:
        >>> stats = consolidate_all_sessions(max_sessions=10)
        >>> print(f"Consolidated {stats['success']} sessions")
    """
    stats = {"success": 0, "failed": 0, "skipped": 0}

    if not SESSIONS_DIR.exists():
        logger.warning("SESSIONS_DIR_NOT_FOUND", path=str(SESSIONS_DIR))
        return stats

    session_files = list(SESSIONS_DIR.glob("*.h5"))
    if max_sessions:
        session_files = session_files[:max_sessions]

    logger.info(
        "CONSOLIDATION_BATCH_START",
        total_sessions=len(session_files),
        max_sessions=max_sessions,
    )

    for session_path in session_files:
        session_id = session_path.stem  # Remove .h5 extension
        try:
            if consolidate_session_to_corpus(session_id, delete_after=True):
                stats["success"] += 1
            else:
                stats["failed"] += 1
        except Exception as e:
            logger.error(
                "CONSOLIDATION_BATCH_ERROR",
                session_id=session_id,
                error=str(e),
            )
            stats["failed"] += 1

    logger.info(
        "CONSOLIDATION_BATCH_COMPLETE",
        **stats,
    )

    return stats


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BACKWARD COMPATIBILITY - Read from corpus.h5 for legacy sessions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_h5_file_for_session(session_id: str, mode: str = "r") -> tuple[h5py.File, str]:
    """Get HDF5 file handle for session (session-level or corpus).

    Tries session-level file first, falls back to corpus.h5 for legacy sessions.

    Args:
        session_id: Session identifier
        mode: File open mode ('r', 'r+', 'a')

    Returns:
        Tuple of (h5py.File handle, source: 'session' | 'corpus')

    Raises:
        FileNotFoundError: If session not found in either location

    Example:
        >>> f, source = get_h5_file_for_session("abc-123", mode="r")
        >>> print(f"Reading from {source}")
        >>> f.close()
    """
    # Try session-level file first (new architecture)
    session_path = get_session_h5_path(session_id)
    if session_path.exists():
        logger.debug("SESSION_READ_FROM_SESSION_FILE", session_id=session_id)
        return h5py.File(session_path, mode), "session"

    # Fallback to corpus.h5 (legacy sessions)
    if CORPUS_PATH.exists():
        with h5py.File(CORPUS_PATH, "r") as f:
            if f"/sessions/{session_id}" in f:
                logger.debug("SESSION_READ_FROM_CORPUS", session_id=session_id)
                # Reopen in requested mode
                return h5py.File(CORPUS_PATH, mode), "corpus"

    raise FileNotFoundError(f"Session {session_id} not found in session files or corpus.h5")


def list_all_sessions() -> list[str]:
    """List all session IDs (from both session files and corpus).

    Returns:
        List of session IDs

    Example:
        >>> sessions = list_all_sessions()
        >>> print(f"Found {len(sessions)} sessions")
    """
    session_ids = set()

    # Get sessions from session files
    if SESSIONS_DIR.exists():
        for path in SESSIONS_DIR.glob("*.h5"):
            session_ids.add(path.stem)

    # Get sessions from corpus
    if CORPUS_PATH.exists():
        with h5py.File(CORPUS_PATH, "r") as f:
            if "/sessions" in f:
                for session_id in f["/sessions"]:
                    session_ids.add(session_id)

    return sorted(session_ids)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DIAGNOSTICS & MAINTENANCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_storage_stats() -> dict[str, any]:
    """Get storage statistics for session files and corpus.

    Returns:
        Dict with storage stats:
            - session_files_count: Number of session files
            - session_files_size_mb: Total size of session files in MB
            - corpus_size_mb: Size of corpus.h5 in MB
            - total_sessions: Total unique sessions
    """
    stats = {
        "session_files_count": 0,
        "session_files_size_mb": 0.0,
        "corpus_size_mb": 0.0,
        "total_sessions": 0,
    }

    # Session files
    if SESSIONS_DIR.exists():
        session_files = list(SESSIONS_DIR.glob("*.h5"))
        stats["session_files_count"] = len(session_files)
        total_size = sum(f.stat().st_size for f in session_files)
        stats["session_files_size_mb"] = round(total_size / (1024 * 1024), 2)

    # Corpus
    if CORPUS_PATH.exists():
        stats["corpus_size_mb"] = round(CORPUS_PATH.stat().st_size / (1024 * 1024), 2)

    # Total sessions
    stats["total_sessions"] = len(list_all_sessions())

    return stats
