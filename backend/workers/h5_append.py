"""HDF5 Append Atómico para Celery Workers.

Card: AUR-PROMPT-4.2 (Fix Pack)
Problem: h5py + prefork deadlock en append concurrente
Solution: File lock + retry + typed dtypes + single-writer pattern

File: backend/workers/h5_append.py
Created: 2025-11-10
"""

from __future__ import annotations

import random
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from backend.logger import get_logger

logger = get_logger(__name__)

# Try to import filelock, fall back to best-effort
try:
    from filelock import FileLock, Timeout

    _have_filelock = True
except ImportError:
    _have_filelock = False
    logger.warning(
        "H5_APPEND_NO_FILELOCK",
        message="filelock not installed - using best-effort locking (not NFS-safe)",
    )


def _utf8():
    """Get h5py UTF-8 string dtype."""
    import h5py

    return h5py.string_dtype(encoding="utf-8")


@contextmanager
def _lock_for(path: Path, timeout: float = 15.0):
    """
    Acquire exclusive file lock for HDF5 write.

    Uses filelock if available, otherwise best-effort (not NFS-safe).
    """
    lock_path = Path(f"{path}.lock")
    if _have_filelock:
        lock = FileLock(lock_path.as_posix())  # type: ignore[possibly-unbound]
        try:
            lock.acquire(timeout=timeout)
            try:
                yield
            finally:
                lock.release()
        except Timeout:  # type: ignore[misc]
            logger.error("H5_LOCK_TIMEOUT", path=str(path), timeout=timeout)
            raise
    else:
        # Best-effort without filelock dependency
        yield


def append_chunk_h5(
    corpus_path: str,
    session_id: str,
    chunk_number: int,
    transcript: str,
    audio_hash: str,
    timestamp_start: float,
    timestamp_end: float,
    language: str = "es",
    duration: float = 0.0,
    max_retries: int = 5,
) -> bool:
    """
    Atomic append to /sessions/{session_id}/chunks in HDF5 corpus.

    Uses file lock + exponential backoff to avoid h5py prefork deadlocks.

    Args:
        corpus_path: Path to HDF5 corpus file
        session_id: Session identifier
        chunk_number: Chunk index (0-based)
        transcript: Transcription text
        audio_hash: SHA256 hash of audio file
        timestamp_start: Start time in seconds
        timestamp_end: End time in seconds
        language: Language code (default: es)
        duration: Audio duration in seconds
        max_retries: Max retry attempts on lock failure

    Returns:
        True if append succeeded

    Raises:
        Exception: If all retries exhausted
    """
    import h5py
    import numpy as np

    p = Path(corpus_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(max_retries):
        try:
            with _lock_for(p, timeout=30.0):
                # Set HDF5_USE_FILE_LOCKING=FALSE to avoid OS-level locking issues
                with h5py.File(p.as_posix(), "a", libver="latest") as f:
                    # Ensure session group exists
                    grp = f.require_group(f"/sessions/{session_id}")

                    # Create or get chunks dataset
                    ds_name = "chunks"
                    if ds_name not in grp:
                        # Typed dtype (NO object types)
                        dt = np.dtype(
                            [
                                ("chunk_id", "S64"),
                                ("session_id", "S64"),
                                ("chunk_number", "i4"),
                                ("timestamp_start", "f8"),
                                ("timestamp_end", "f8"),
                                ("duration", "f8"),
                                ("language", "S8"),
                                ("transcription", _utf8()),
                                ("audio_hash", "S64"),
                                ("created_at", _utf8()),
                            ]
                        )
                        grp.create_dataset(ds_name, shape=(0,), maxshape=(None,), dtype=dt)
                        logger.info("H5_CHUNKS_DATASET_CREATED", session_id=session_id)

                    ds = grp[ds_name]
                    n = ds.shape[0]

                    # Resize and append
                    ds.resize((n + 1,))
                    chunk_id = f"{session_id}_chunk_{chunk_number}".encode("utf-8")
                    created_at = datetime.now(timezone.utc).isoformat()

                    ds[n] = (
                        chunk_id,
                        session_id.encode("utf-8"),
                        int(chunk_number),
                        float(timestamp_start),
                        float(timestamp_end),
                        float(duration),
                        language.encode("utf-8"),
                        transcript,
                        audio_hash.encode("utf-8"),
                        created_at,
                    )

                    # Explicit flush to disk
                    f.flush()

                logger.info(
                    "H5_CHUNK_APPENDED",
                    session_id=session_id,
                    chunk_number=chunk_number,
                    transcript_length=len(transcript),
                    attempt=attempt + 1,
                )
                return True

        except Exception as e:
            # Exponential backoff with jitter to avoid thundering herd
            if attempt == max_retries - 1:
                logger.error(
                    "H5_APPEND_FAILED",
                    session_id=session_id,
                    chunk_number=chunk_number,
                    error=str(e),
                    attempts=max_retries,
                )
                raise

            backoff = 0.15 * (2**attempt) + random.random() * 0.2
            logger.warning(
                "H5_APPEND_RETRY",
                session_id=session_id,
                chunk_number=chunk_number,
                attempt=attempt + 1,
                backoff_sec=backoff,
                error=str(e),
            )
            time.sleep(backoff)

    return False
