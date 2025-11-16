"""Task-based HDF5 repository for session data.

Philosophy:
  - 1 Session = 1 medical consultation (AURITY)
  - 1 Session → N Tasks (each type appears MAX 1 time)
  - Task = purpose (TRANSCRIPTION, DIARIZATION, etc.)
  - Job = execution metadata (job_id, status, progress)

Storage structure:
  /sessions/{session_id}/tasks/
    ├── TRANSCRIPTION/
    │   ├── chunks/chunk_N/
    │   └── job_metadata.json
    ├── DIARIZATION/
    │   ├── speakers/speaker_N/
    │   ├── segments/segment_N/
    │   └── job_metadata.json
    └── [other tasks...]

Rules:
  - Each task type can appear AT MOST ONCE per session
  - ensure_task_exists() enforces uniqueness (raises ValueError if exists)
  - Metadata and data are colocated within task directory

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Architecture refactor - task-based HDF5
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional, Union

import h5py

from backend.logger import get_logger
from backend.models.task_type import TaskStatus, TaskType

logger = get_logger(__name__)

# HDF5 corpus path
CORPUS_PATH = Path(__file__).parent.parent.parent / "storage" / "corpus.h5"

# Global lock for HDF5 file access (HDF5 is not thread-safe for concurrent writes)
# Using RLock to allow same thread to acquire lock multiple times
_h5_lock = threading.RLock()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SWMR MODE HELPERS (Single Writer Multiple Readers)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# SWMR mode permite lecturas y escrituras simultáneas en HDF5.
# Sin SWMR, el archivo no puede estar abierto en READ y WRITE al mismo tiempo.


@contextmanager
def open_h5_read() -> Iterator[h5py.File]:
    """Open HDF5 in SWMR read mode (allows concurrent writer).

    SWMR = Single Writer Multiple Readers.
    Multiple threads can read while one thread writes.
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _h5_lock:
        f = h5py.File(CORPUS_PATH, "r", swmr=True, libver="latest")
        try:
            yield f  # type: ignore[misc]
        finally:
            f.close()


@contextmanager
def open_h5_write() -> Iterator[h5py.File]:
    """Open HDF5 in SWMR write mode (allows concurrent readers).

    SWMR = Single Writer Multiple Readers.
    One writer can write while multiple readers read.
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _h5_lock:
        f = h5py.File(CORPUS_PATH, "a", libver="latest")
        try:
            # Enable SWMR write mode AFTER opening
            if not f.swmr_mode:  # type: ignore[attr-defined]
                f.swmr_mode = True  # type: ignore[attr-defined]
            yield f  # type: ignore[misc]
        finally:
            f.close()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TASK MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def ensure_task_exists(
    session_id: str,
    task_type: Union[TaskType, str],
    allow_existing: bool = False,
) -> str:
    """Ensure task group exists for session.

    Args:
        session_id: Session identifier
        task_type: Type of task (TaskType enum or string)
        allow_existing: If True, don't raise error if task exists

    Returns:
        HDF5 path to task group

    Raises:
        ValueError: If task already exists and allow_existing=False
    """
    task_type_str = task_type.value if isinstance(task_type, TaskType) else task_type
    task_path = f"/sessions/{session_id}/tasks/{task_type_str}"

    with open_h5_write() as f:
        # Check if task already exists
        if task_path in f:  # type: ignore[operator]
            if not allow_existing:
                raise ValueError(
                    f"Task {task_type_str} already exists for session {session_id}. "
                    f"Each task type can appear AT MOST ONCE per session."
                )
            logger.info(
                "TASK_ALREADY_EXISTS",
                session_id=session_id,
                task_type=task_type_str,
                path=task_path,
            )
            return task_path

        # Create session group if not exists
        if "sessions" not in f:  # type: ignore[operator]
            f.create_group("sessions")  # type: ignore[attr-defined]

        if f"/sessions/{session_id}" not in f:  # type: ignore[operator]
            f["sessions"].create_group(session_id)  # type: ignore[index]

        session_group = f[f"/sessions/{session_id}"]  # type: ignore[index]

        # Create tasks group if not exists
        if "tasks" not in session_group:  # type: ignore[operator]
            session_group.create_group("tasks")  # type: ignore[index]

        tasks_group = session_group["tasks"]  # type: ignore[index]

        # Create task group
        task_group = tasks_group.create_group(task_type_str)  # type: ignore[attr-defined]

        # Initialize job_metadata with default values
        default_metadata = {
            "job_id": None,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "progress_percent": 0,
            "total_chunks": 0,
            "processed_chunks": 0,
        }

        metadata_json = json.dumps(default_metadata)
        task_group.create_dataset(  # type: ignore[attr-defined]
            "job_metadata",
            data=metadata_json,
            dtype=h5py.string_dtype(encoding="utf-8"),
        )

        logger.info(
            "TASK_CREATED",
            session_id=session_id,
            task_type=task_type_str,
            path=task_path,
        )

    return task_path


def task_exists(session_id: str, task_type: Union[TaskType, str]) -> bool:
    """Check if task exists for session.

    Args:
        session_id: Session identifier
        task_type: Type of task

    Returns:
        True if task exists, False otherwise
    """
    if not CORPUS_PATH.exists():
        return False

    task_type_str = task_type.value if isinstance(task_type, TaskType) else task_type
    task_path = f"/sessions/{session_id}/tasks/{task_type_str}"

    try:
        with h5py.File(CORPUS_PATH, "r") as f:
            return task_path in f  # type: ignore[operator]
    except OSError:
        # File exists but is not a valid HDF5 file
        return False


def list_session_tasks(session_id: str) -> list[str]:
    """List all task types for a session.

    Args:
        session_id: Session identifier

    Returns:
        List of task type strings (e.g., ["TRANSCRIPTION", "DIARIZATION"])
    """
    if not CORPUS_PATH.exists():
        return []

    tasks_path = f"/sessions/{session_id}/tasks"

    try:
        with h5py.File(CORPUS_PATH, "r") as f:
            if tasks_path not in f:  # type: ignore[operator]
                return []

            tasks_group = f[tasks_path]  # type: ignore[index]
            return list(tasks_group.keys())  # type: ignore[return-value]
    except Exception as e:
        logger.error("LIST_TASKS_FAILED", session_id=session_id, error=str(e))
        return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JOB METADATA (within task)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def update_task_metadata(
    session_id: str,
    task_type: Union[TaskType, str],
    metadata: dict[str, Any],
) -> None:
    """Update job metadata for a task.

    Args:
        session_id: Session identifier
        task_type: Type of task
        metadata: Metadata dictionary (partial update)

    Raises:
        ValueError: If task does not exist
    """
    task_type_str = task_type.value if isinstance(task_type, TaskType) else task_type

    if not task_exists(session_id, task_type_str):
        raise ValueError(
            f"Task {task_type_str} does not exist for session {session_id}. "
            f"Call ensure_task_exists() first."
        )

    task_path = f"/sessions/{session_id}/tasks/{task_type_str}"

    with _h5_lock:  # Lock H5 file to prevent concurrent access errors
        with h5py.File(CORPUS_PATH, "a") as f:
            task_group = f[task_path]  # type: ignore[index]

            # Read existing metadata
            if "job_metadata" in task_group:  # type: ignore[operator]
                existing_json = task_group["job_metadata"][()]  # type: ignore[index]
                if isinstance(existing_json, bytes):
                    existing_json = existing_json.decode("utf-8")
                existing_metadata = json.loads(existing_json)
            else:
                existing_metadata = {}

            # Merge with new metadata
            existing_metadata.update(metadata)
            existing_metadata["updated_at"] = datetime.now(UTC).isoformat()

            # Write back
            metadata_json = json.dumps(existing_metadata)

            # Delete old dataset
            if "job_metadata" in task_group:  # type: ignore[operator]
                del task_group["job_metadata"]  # type: ignore[index]

            # Create new dataset
            task_group.create_dataset(  # type: ignore[attr-defined]
                "job_metadata",
                data=metadata_json,
                dtype=h5py.string_dtype(encoding="utf-8"),
            )

            logger.info(
                "TASK_METADATA_UPDATED",
                session_id=session_id,
                task_type=task_type_str,
                metadata_keys=list(metadata.keys()),
            )


def get_task_metadata(session_id: str, task_type: Union[TaskType, str]) -> Optional[dict[str, Any]]:
    """Get job metadata for a task.

    Args:
        session_id: Session identifier
        task_type: Type of task

    Returns:
        Metadata dictionary or None if task doesn't exist
    """
    if not task_exists(session_id, task_type):
        return None

    task_type_str = task_type.value if isinstance(task_type, TaskType) else task_type
    task_path = f"/sessions/{session_id}/tasks/{task_type_str}"

    try:
        with h5py.File(CORPUS_PATH, "r") as f:
            task_group = f[task_path]  # type: ignore[index]

            if "job_metadata" not in task_group:  # type: ignore[operator]
                return None

            metadata_json = task_group["job_metadata"][()]  # type: ignore[index]
            if isinstance(metadata_json, bytes):
                metadata_json = metadata_json.decode("utf-8")

            return json.loads(metadata_json)  # type: ignore[return-value]
    except Exception as e:
        logger.error(
            "GET_METADATA_FAILED",
            session_id=session_id,
            task_type=task_type_str,
            error=str(e),
        )
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRANSCRIPTION TASK - CHUNKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def append_chunk_to_task(
    session_id: str,
    task_type: Union[TaskType, str],
    chunk_idx: int,
    transcript: str,
    audio_hash: str,
    duration: float,
    language: str,
    timestamp_start: float,
    timestamp_end: float,
    confidence: float = 0.95,
    audio_quality: float = 0.85,
) -> str:
    """Append transcription chunk to task.

    Args:
        session_id: Session identifier
        task_type: Type of task (usually TRANSCRIPTION)
        chunk_idx: Chunk index (0-based)
        transcript: Transcribed text
        audio_hash: SHA256 hash of audio
        duration: Audio duration (seconds)
        language: Language code (es, en, etc.)
        timestamp_start: Start time (seconds)
        timestamp_end: End time (seconds)
        confidence: Transcription confidence (0-1)
        audio_quality: Audio quality score (0-1)

    Returns:
        HDF5 path to chunk

    Raises:
        ValueError: If task doesn't exist or chunk already exists
    """
    task_type_str = task_type.value if isinstance(task_type, TaskType) else task_type

    if not task_exists(session_id, task_type_str):
        raise ValueError(f"Task {task_type_str} does not exist. Call ensure_task_exists() first.")

    task_path = f"/sessions/{session_id}/tasks/{task_type_str}"
    chunk_path = f"{task_path}/chunks/chunk_{chunk_idx}"
    created_at = datetime.now(UTC).isoformat()

    with _h5_lock:  # Lock H5 file to prevent concurrent access errors
        with h5py.File(CORPUS_PATH, "a") as f:
            task_group = f[task_path]  # type: ignore[index]

            # Create chunks group if not exists
            if "chunks" not in task_group:  # type: ignore[operator]
                task_group.create_group("chunks")  # type: ignore[index]

            chunks_group = task_group["chunks"]  # type: ignore[index]

            # Check if chunk already exists (append-only)
            if f"chunk_{chunk_idx}" in chunks_group:  # type: ignore[operator]
                raise ValueError(
                    f"Chunk {chunk_idx} already exists for task {task_type_str} "
                    f"(append-only violation)"
                )

            # Create chunk group
            chunk_group = chunks_group.create_group(f"chunk_{chunk_idx}")  # type: ignore[attr-defined]

            # Write datasets
            chunk_group.create_dataset(  # type: ignore[attr-defined]
                "transcript",
                data=transcript,
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            chunk_group.create_dataset(  # type: ignore[attr-defined]
                "audio_hash",
                data=audio_hash,
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            chunk_group.create_dataset("duration", data=duration, dtype="float64")  # type: ignore[attr-defined]
            chunk_group.create_dataset(  # type: ignore[attr-defined]
                "language",
                data=language,
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            chunk_group.create_dataset("timestamp_start", data=timestamp_start, dtype="float64")  # type: ignore[attr-defined]
            chunk_group.create_dataset("timestamp_end", data=timestamp_end, dtype="float64")  # type: ignore[attr-defined]
            chunk_group.create_dataset("confidence", data=confidence, dtype="float32")  # type: ignore[attr-defined]
            chunk_group.create_dataset("audio_quality", data=audio_quality, dtype="float32")  # type: ignore[attr-defined]
            chunk_group.create_dataset(  # type: ignore[attr-defined]
                "created_at",
                data=created_at,
                dtype=h5py.string_dtype(encoding="utf-8"),
            )

        logger.info(
            "CHUNK_APPENDED_TO_TASK",
            session_id=session_id,
            task_type=task_type_str,
            chunk_idx=chunk_idx,
            chunk_path=chunk_path,
            transcript_length=len(transcript),
            duration=duration,
        )

    return chunk_path


def count_task_chunks(session_id: str, task_type: Union[TaskType, str]) -> tuple[int, int]:
    """Count total chunks and processed chunks (fast, no data reading).

    Args:
        session_id: Session identifier
        task_type: Type of task

    Returns:
        Tuple of (total_chunks, processed_chunks) where:
        - total_chunks: expected total from metadata
        - processed_chunks: actual chunks written to HDF5
    """
    if not task_exists(session_id, task_type):
        return (0, 0)

    task_type_str = task_type.value if isinstance(task_type, TaskType) else task_type

    try:
        # Get expected total from metadata
        metadata = get_task_metadata(session_id, task_type_str) or {}
        expected_total = metadata.get("total_chunks", 0)

        # Count actual chunks in HDF5 (fast: just count group keys)
        chunks_path = f"/sessions/{session_id}/tasks/{task_type_str}/chunks"

        with h5py.File(CORPUS_PATH, "r") as f:
            if chunks_path not in f:  # type: ignore[operator]
                # Task exists but no chunks yet
                return (expected_total, 0)

            chunks_group = f[chunks_path]  # type: ignore[index]
            processed = len(chunks_group.keys())  # type: ignore[union-attr]

            # OPTIMIZATION: Chunks are only created when processed (append-only)
            # So we just count keys, no need to read datasets
            return (expected_total, processed)

    except Exception as e:
        logger.error(
            "COUNT_CHUNKS_FAILED",
            session_id=session_id,
            task_type=task_type_str,
            error=str(e),
        )
        return (0, 0)


def get_task_chunks(session_id: str, task_type: Union[TaskType, str]) -> list[dict[str, Any]]:
    """Get all chunks for a task.

    Args:
        session_id: Session identifier
        task_type: Type of task

    Returns:
        List of chunk dictionaries (ordered by chunk_idx)
    """
    if not task_exists(session_id, task_type):
        return []

    task_type_str = task_type.value if isinstance(task_type, TaskType) else task_type
    chunks_path = f"/sessions/{session_id}/tasks/{task_type_str}/chunks"

    try:
        with h5py.File(CORPUS_PATH, "r") as f:
            if chunks_path not in f:  # type: ignore[operator]
                return []

            chunks_group = f[chunks_path]  # type: ignore[index]
            chunks = []

            for chunk_name in sorted(chunks_group.keys()):  # type: ignore[union-attr]
                chunk_group = chunks_group[chunk_name]  # type: ignore[index]
                chunk_idx = int(chunk_name.split("_")[1])
                transcript = chunk_group["transcript"][()].decode("utf-8")  # type: ignore[index]

                # Determine status based on transcript presence
                status = "completed" if transcript else "pending"

                chunks.append(
                    {
                        "chunk_idx": chunk_idx,
                        "chunk_number": chunk_idx,  # Alias for frontend compatibility
                        "status": status,
                        "transcript": transcript,
                        "audio_hash": chunk_group["audio_hash"][()].decode("utf-8"),  # type: ignore[index]
                        "duration": float(chunk_group["duration"][()]),  # type: ignore[index]
                        "language": chunk_group["language"][()].decode("utf-8"),  # type: ignore[index]
                        "timestamp_start": float(chunk_group["timestamp_start"][()]),  # type: ignore[index]
                        "timestamp_end": float(chunk_group["timestamp_end"][()]),  # type: ignore[index]
                        "confidence": float(chunk_group["confidence"][()]),  # type: ignore[index]
                        "audio_quality": float(chunk_group["audio_quality"][()]),  # type: ignore[index]
                        "created_at": chunk_group["created_at"][()].decode("utf-8"),  # type: ignore[index]
                        "audio_size_bytes": None,  # Not stored in new schema
                        "error_message": None,  # Not stored in new schema
                    }
                )

            return chunks

    except Exception as e:
        logger.error(
            "GET_CHUNKS_FAILED",
            session_id=session_id,
            task_type=task_type_str,
            error=str(e),
        )
        return []


def get_task_transcript(session_id: str, task_type: Union[TaskType, str]) -> str:
    """Get full transcript for task (all chunks concatenated).

    Args:
        session_id: Session identifier
        task_type: Type of task

    Returns:
        Full transcript text
    """
    chunks = get_task_chunks(session_id, task_type)
    return " ".join(chunk["transcript"] for chunk in chunks)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BACKWARDS COMPATIBILITY (reads old schema)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_session_chunks_compat(session_id: str) -> list[dict[str, Any]]:
    """Backwards compatible chunk reader.

    Tries multiple locations in order:
    1. /sessions/{id}/tasks/TRANSCRIPTION/chunks/ (new)
    2. /sessions/{id}/production/chunks/ (old dual schema)
    3. /sessions/{id}/chunks/ (legacy)

    Args:
        session_id: Session identifier

    Returns:
        List of chunk dictionaries
    """
    # Try new task-based schema first
    if task_exists(session_id, TaskType.TRANSCRIPTION):
        return get_task_chunks(session_id, TaskType.TRANSCRIPTION)

    # Try old production/ schema
    production_path = f"/sessions/{session_id}/production/chunks"
    if CORPUS_PATH.exists():
        with h5py.File(CORPUS_PATH, "r") as f:
            if production_path in f:  # type: ignore[operator]
                # Read from old schema (same logic as get_task_chunks)
                chunks_group = f[production_path]  # type: ignore[index]
                chunks = []
                for chunk_name in sorted(chunks_group.keys()):  # type: ignore[union-attr]
                    chunk_group = chunks_group[chunk_name]  # type: ignore[index]
                    chunks.append(
                        {
                            "chunk_idx": int(chunk_name.split("_")[1]),
                            "transcript": chunk_group["transcript"][()].decode("utf-8"),  # type: ignore[index]
                            "audio_hash": chunk_group["audio_hash"][()].decode("utf-8"),  # type: ignore[index]
                            "duration": float(chunk_group["duration"][()]),  # type: ignore[index]
                            "language": chunk_group["language"][()].decode("utf-8")
                            if chunk_group["language"][()]
                            else "es",  # type: ignore[index]
                            "timestamp_start": float(chunk_group["timestamp_start"][()]),  # type: ignore[index]
                            "timestamp_end": float(chunk_group["timestamp_end"][()]),  # type: ignore[index]
                            "created_at": chunk_group["created_at"][()].decode("utf-8"),  # type: ignore[index]
                        }
                    )
                return chunks

    # Try legacy schema (very old)
    legacy_path = f"/sessions/{session_id}/chunks"
    if CORPUS_PATH.exists():
        with h5py.File(CORPUS_PATH, "r") as f:
            if legacy_path in f:  # type: ignore[operator]
                logger.warning(
                    "USING_LEGACY_SCHEMA",
                    session_id=session_id,
                    path=legacy_path,
                    recommendation="Migrate to task-based schema",
                )
                # Return empty for now (legacy schema has different structure)
                return []

    return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRANSCRIPTION SOURCES (3 sources + audio files)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def add_webspeech_transcripts(
    session_id: str, transcripts: list[str], task_type: TaskType = TaskType.TRANSCRIPTION
) -> str:
    """Add WebSpeech instant preview transcripts to TRANSCRIPTION task.

    Args:
        session_id: Session identifier
        transcripts: List of WebSpeech transcript strings
        task_type: Task type (default TRANSCRIPTION)

    Returns:
        HDF5 path to webspeech_final dataset
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(CORPUS_PATH, "a") as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"Task {task_type.value} does not exist for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        # Delete existing webspeech_final if present
        if "webspeech_final" in task_group:  # type: ignore[operator]
            del task_group["webspeech_final"]  # type: ignore[index]

        # Create webspeech_final dataset (list of strings)
        transcripts_json = json.dumps(transcripts)
        task_group.create_dataset(  # type: ignore[union-attr]
            "webspeech_final",
            data=transcripts_json,
            dtype=h5py.string_dtype(encoding="utf-8"),
        )

    webspeech_path = f"{task_path}/webspeech_final"
    logger.info(
        "WEBSPEECH_ADDED",
        session_id=session_id,
        task_type=task_type.value,
        transcript_count=len(transcripts),
        path=webspeech_path,
    )

    return webspeech_path


def add_full_transcription(
    session_id: str, full_text: str, task_type: TaskType = TaskType.TRANSCRIPTION
) -> str:
    """Add full concatenated transcription to TRANSCRIPTION task.

    Args:
        session_id: Session identifier
        full_text: Complete transcription text
        task_type: Task type (default TRANSCRIPTION)

    Returns:
        HDF5 path to full_transcription dataset
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(CORPUS_PATH, "a") as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"Task {task_type.value} does not exist for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        # Delete existing full_transcription if present
        if "full_transcription" in task_group:  # type: ignore[operator]
            del task_group["full_transcription"]  # type: ignore[index]

        # Create full_transcription dataset
        task_group.create_dataset(  # type: ignore[union-attr]
            "full_transcription",
            data=full_text,
            dtype=h5py.string_dtype(encoding="utf-8"),
        )

    full_path = f"{task_path}/full_transcription"
    logger.info(
        "FULL_TRANSCRIPTION_ADDED",
        session_id=session_id,
        task_type=task_type.value,
        text_length=len(full_text),
        path=full_path,
    )

    return full_path


def add_full_audio(
    session_id: str,
    audio_bytes: bytes,
    filename: str = "full_audio.webm",
    task_type: TaskType = TaskType.TRANSCRIPTION,
) -> str:
    """Add full audio file to TRANSCRIPTION task.

    Args:
        session_id: Session identifier
        audio_bytes: Raw audio bytes
        filename: Audio filename (default full_audio.webm)
        task_type: Task type (default TRANSCRIPTION)

    Returns:
        HDF5 path to audio dataset
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(CORPUS_PATH, "a") as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"Task {task_type.value} does not exist for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        # Delete existing audio if present
        if filename in task_group:  # type: ignore[operator]
            del task_group[filename]  # type: ignore[index]

        # Create audio dataset (binary data with opaque dtype)
        import numpy as np

        task_group.create_dataset(  # type: ignore[union-attr]
            filename, data=np.frombuffer(audio_bytes, dtype=np.uint8)
        )

    audio_path = f"{task_path}/{filename}"
    logger.info(
        "FULL_AUDIO_ADDED",
        session_id=session_id,
        task_type=task_type.value,
        filename=filename,
        size_bytes=len(audio_bytes),
        path=audio_path,
    )

    return audio_path


def create_empty_chunk(
    session_id: str,
    task_type: TaskType,
    chunk_idx: int,
) -> str:
    """Create an empty chunk structure (for audio storage before transcription).

    Args:
        session_id: Session identifier
        task_type: Task type
        chunk_idx: Chunk index

    Returns:
        HDF5 path to chunk

    Raises:
        ValueError: If task doesn't exist or chunk already exists
    """
    import h5py

    if not task_exists(session_id, task_type):
        raise ValueError(f"Task {task_type.value} does not exist")

    task_path = f"/sessions/{session_id}/tasks/{task_type.value}"
    chunk_path = f"{task_path}/chunks/chunk_{chunk_idx}"

    with _h5_lock:  # Lock H5 file to prevent concurrent access errors
        with h5py.File(CORPUS_PATH, "a") as f:
            task_group = f[task_path]  # type: ignore[index]

            # Create chunks group if not exists
            if "chunks" not in task_group:  # type: ignore[operator]
                task_group.create_group("chunks")  # type: ignore[index]

            chunks_group = task_group["chunks"]  # type: ignore[index]

            # Check if chunk already exists
            if f"chunk_{chunk_idx}" in chunks_group:  # type: ignore[operator]
                # Already exists, that's ok for this use case (idempotent)
                logger.info(
                    "EMPTY_CHUNK_ALREADY_EXISTS",
                    session_id=session_id,
                    task_type=task_type.value,
                    chunk_idx=chunk_idx,
                )
                return chunk_path

            # Create chunk group
            chunk_group = chunks_group.create_group(f"chunk_{chunk_idx}")  # type: ignore[attr-defined]

            # Create placeholder datasets (will be updated by worker after transcription)
            # These are required by get_task_chunks() function
            chunk_group.create_dataset(  # type: ignore[union-attr]
                "transcript",
                data="",
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            chunk_group.create_dataset(  # type: ignore[union-attr]
                "audio_hash",
                data="",
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            chunk_group.create_dataset("duration", data=0.0, dtype="float64")  # type: ignore[union-attr]
            chunk_group.create_dataset(  # type: ignore[union-attr]
                "language",
                data="",
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            chunk_group.create_dataset("timestamp_start", data=0.0, dtype="float64")  # type: ignore[union-attr]
            chunk_group.create_dataset("timestamp_end", data=0.0, dtype="float64")  # type: ignore[union-attr]
            chunk_group.create_dataset("confidence", data=0.0, dtype="float32")  # type: ignore[union-attr]
            chunk_group.create_dataset("audio_quality", data=0.0, dtype="float32")  # type: ignore[union-attr]
            chunk_group.create_dataset(  # type: ignore[union-attr]
                "created_at",
                data=datetime.now(UTC).isoformat(),
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            chunk_group.create_dataset(
                "status", data="pending", dtype=h5py.string_dtype(encoding="utf-8")
            )  # type: ignore[union-attr]

            logger.info(
                "EMPTY_CHUNK_CREATED",
                session_id=session_id,
                task_type=task_type.value,
                chunk_idx=chunk_idx,
            )

    return chunk_path


def add_audio_to_chunk(
    session_id: str,
    chunk_idx: int,
    audio_bytes: bytes,
    filename: str = "audio.webm",
    task_type: TaskType = TaskType.TRANSCRIPTION,
) -> str:
    """Add audio file to an existing chunk.

    Args:
        session_id: Session identifier
        chunk_idx: Chunk index
        audio_bytes: Raw audio bytes
        filename: Audio filename (default audio.webm)
        task_type: Task type (default TRANSCRIPTION)

    Returns:
        HDF5 path to chunk audio dataset
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _h5_lock:  # Lock H5 file to prevent concurrent access errors
        with h5py.File(CORPUS_PATH, "a") as f:
            chunk_path = f"/sessions/{session_id}/tasks/{task_type.value}/chunks/chunk_{chunk_idx}"

            if chunk_path not in f:  # type: ignore[operator]
                raise ValueError(f"Chunk {chunk_idx} does not exist for session {session_id}")

            chunk_group = f[chunk_path]  # type: ignore[index]

            # Delete existing audio if present
            if filename in chunk_group:  # type: ignore[operator]
                del chunk_group[filename]  # type: ignore[index]

            # Create audio dataset (binary data with opaque dtype)
            import numpy as np

            chunk_group.create_dataset(  # type: ignore[union-attr]
                filename, data=np.frombuffer(audio_bytes, dtype=np.uint8)
            )

        audio_path = f"{chunk_path}/{filename}"
        logger.info(
            "CHUNK_AUDIO_ADDED",
            session_id=session_id,
            task_type=task_type.value,
            chunk_idx=chunk_idx,
            filename=filename,
            size_bytes=len(audio_bytes),
            path=audio_path,
        )

    return audio_path


def get_chunk_audio_bytes(
    session_id: str,
    task_type: TaskType,
    chunk_idx: int,
    filename: str = "audio.webm",
) -> Optional[bytes]:
    """Get audio bytes from a chunk.

    Args:
        session_id: Session identifier
        task_type: Task type
        chunk_idx: Chunk index
        filename: Audio filename (default audio.webm)

    Returns:
        Audio bytes or None if not found
    """
    import h5py

    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        with h5py.File(CORPUS_PATH, "r") as f:
            chunk_path = f"/sessions/{session_id}/tasks/{task_type.value}/chunks/chunk_{chunk_idx}"

            if chunk_path not in f:  # type: ignore[operator]
                logger.warning(
                    "CHUNK_NOT_FOUND",
                    session_id=session_id,
                    task_type=task_type.value,
                    chunk_idx=chunk_idx,
                )
                return None

            chunk_group = f[chunk_path]  # type: ignore[index]

            if filename not in chunk_group:  # type: ignore[operator]
                logger.warning(
                    "AUDIO_NOT_FOUND_IN_CHUNK",
                    session_id=session_id,
                    task_type=task_type.value,
                    chunk_idx=chunk_idx,
                    filename=filename,
                )
                return None

            # Read audio dataset
            audio_dataset = chunk_group[filename]  # type: ignore[index]
            audio_bytes = bytes(audio_dataset[()])  # type: ignore[index]

            logger.info(
                "CHUNK_AUDIO_READ",
                session_id=session_id,
                task_type=task_type.value,
                chunk_idx=chunk_idx,
                filename=filename,
                size_bytes=len(audio_bytes),
            )

            return audio_bytes

    except Exception as e:
        logger.error(
            "GET_CHUNK_AUDIO_FAILED",
            session_id=session_id,
            task_type=task_type.value,
            chunk_idx=chunk_idx,
            error=str(e),
        )
        return None


def update_chunk_dataset(
    session_id: str,
    task_type: Union[TaskType, str],
    chunk_idx: int,
    field: str,
    value: Union[str, float, int],
) -> bool:
    """Update a single field in a chunk dataset.

    Args:
        session_id: Session identifier
        task_type: Type of task
        chunk_idx: Chunk index
        field: Field name (transcript, confidence, duration, language, etc.)
        value: New value for the field

    Returns:
        True if successful, False otherwise
    """
    if not task_exists(session_id, task_type):
        logger.warning("TASK_NOT_EXISTS", session_id=session_id, task_type=str(task_type))
        return False

    task_type_str = task_type.value if isinstance(task_type, TaskType) else task_type
    chunk_path = f"/sessions/{session_id}/tasks/{task_type_str}/chunks/chunk_{chunk_idx}"

    try:
        with _h5_lock:  # Lock H5 file to prevent concurrent access errors
            with h5py.File(CORPUS_PATH, "a") as f:
                if chunk_path not in f:  # type: ignore[operator]
                    logger.warning(
                        "CHUNK_NOT_FOUND",
                        session_id=session_id,
                        task_type=task_type_str,
                        chunk_idx=chunk_idx,
                    )
                    return False

                chunk_group = f[chunk_path]  # type: ignore[index]

                # Delete existing dataset if present
                if field in chunk_group:  # type: ignore[operator]
                    del chunk_group[field]  # type: ignore[index]

                # Create new dataset with appropriate dtype
                if isinstance(value, str):
                    chunk_group.create_dataset(  # type: ignore[union-attr]
                        field,
                        data=value,
                        dtype=h5py.string_dtype(encoding="utf-8"),
                    )
                elif isinstance(value, float):
                    chunk_group.create_dataset(field, data=value, dtype="float64")  # type: ignore[union-attr]
                elif isinstance(value, int):
                    chunk_group.create_dataset(field, data=value, dtype="int32")  # type: ignore[union-attr]
                else:
                    # Try to convert to string
                    chunk_group.create_dataset(  # type: ignore[union-attr]
                        field,
                        data=str(value),
                        dtype=h5py.string_dtype(encoding="utf-8"),
                    )

                logger.info(
                    "CHUNK_DATASET_UPDATED",
                    session_id=session_id,
                    task_type=task_type_str,
                    chunk_idx=chunk_idx,
                    field=field,
                    value=str(value)[:100],  # Log first 100 chars
                )
                return True

    except Exception as e:
        logger.error(
            "UPDATE_CHUNK_DATASET_FAILED",
            session_id=session_id,
            task_type=task_type_str,
            chunk_idx=chunk_idx,
            field=field,
            error=str(e),
        )
        return False


def save_diarization_segments(
    session_id: str,
    segments: list,
    task_type: TaskType = TaskType.DIARIZATION,
) -> str:
    """Save diarization segments to HDF5.

    Args:
        session_id: Session identifier
        segments: List of DiarizationSegment objects
        task_type: Task type (default DIARIZATION)

    Returns:
        HDF5 path to segments group
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(CORPUS_PATH, "a") as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"Task {task_type.value} does not exist for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        # Delete existing segments if present
        if "segments" in task_group:  # type: ignore[operator]
            del task_group["segments"]  # type: ignore[index]

        # Create segments group
        segments_group = task_group.create_group("segments")  # type: ignore[union-attr]

        # Save each segment
        for i, segment in enumerate(segments):
            seg_group = segments_group.create_group(f"segment_{i}")

            # Save segment attributes (Speaker is a dataclass, extract speaker_id string)
            seg_group.create_dataset("speaker", data=segment.speaker.speaker_id.encode("utf-8"))
            seg_group.create_dataset("text", data=segment.text.encode("utf-8"))
            seg_group.create_dataset("start_time", data=segment.start_time)
            seg_group.create_dataset("end_time", data=segment.end_time)

            if hasattr(segment, "confidence") and segment.confidence is not None:
                seg_group.create_dataset("confidence", data=segment.confidence)

            if hasattr(segment, "improved_text") and segment.improved_text:
                seg_group.create_dataset(
                    "improved_text", data=segment.improved_text.encode("utf-8")
                )

    segments_path = f"{task_path}/segments"
    logger.info(
        "DIARIZATION_SEGMENTS_SAVED",
        session_id=session_id,
        task_type=task_type.value,
        segment_count=len(segments),
        path=segments_path,
    )

    return segments_path


def get_diarization_segments(
    session_id: str,
    task_type: TaskType = TaskType.DIARIZATION,
) -> list[dict[str, Any]]:
    """Get diarization segments from HDF5.

    Args:
        session_id: Session identifier
        task_type: Task type (default DIARIZATION)

    Returns:
        List of segment dictionaries with speaker, text, times, etc.

    Raises:
        ValueError: If task or segments not found
    """
    if not CORPUS_PATH.exists():
        raise ValueError(f"Corpus file not found: {CORPUS_PATH}")

    with open_h5_read() as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"Task {task_type.value} not found for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        if "segments" not in task_group:  # type: ignore[operator]
            raise ValueError(f"No segments found for session {session_id}")

        segments_group = task_group["segments"]  # type: ignore[index]
        segments = []

        # Read all segments in order
        segment_keys = sorted(segments_group.keys(), key=lambda x: int(x.split("_")[1]))

        for seg_key in segment_keys:
            seg_group = segments_group[seg_key]  # type: ignore[index]

            segment = {
                "speaker": seg_group["speaker"][()].decode("utf-8"),  # type: ignore[index]
                "text": seg_group["text"][()].decode("utf-8"),  # type: ignore[index]
                "start_time": float(seg_group["start_time"][()]),  # type: ignore[index]
                "end_time": float(seg_group["end_time"][()]),  # type: ignore[index]
            }

            # Optional fields
            if "confidence" in seg_group:  # type: ignore[operator]
                segment["confidence"] = float(seg_group["confidence"][()])  # type: ignore[index]

            if "improved_text" in seg_group:  # type: ignore[operator]
                segment["improved_text"] = seg_group["improved_text"][()].decode("utf-8")  # type: ignore[index]

            segments.append(segment)

    logger.info(
        "DIARIZATION_SEGMENTS_LOADED",
        session_id=session_id,
        task_type=task_type.value,
        segment_count=len(segments),
    )

    return segments


def update_diarization_segment_text(
    session_id: str,
    segment_index: int,
    new_text: str,
    task_type: TaskType = TaskType.DIARIZATION,
) -> dict[str, Any]:
    """Update text of a specific diarization segment.

    Args:
        session_id: Session identifier
        segment_index: Index of segment to update (0-based)
        new_text: New text content for the segment
        task_type: Task type (default DIARIZATION)

    Returns:
        Updated segment dictionary

    Raises:
        ValueError: If session, task, or segment not found
    """
    if not CORPUS_PATH.exists():
        raise ValueError(f"Corpus file not found: {CORPUS_PATH}")

    with h5py.File(CORPUS_PATH, "a") as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"Task {task_type.value} not found for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        if "segments" not in task_group:  # type: ignore[operator]
            raise ValueError(f"No segments found for session {session_id}")

        segments_group = task_group["segments"]  # type: ignore[index]
        segment_key = f"segment_{segment_index}"

        if segment_key not in segments_group:  # type: ignore[operator]
            raise ValueError(f"Segment {segment_index} not found for session {session_id}")

        seg_group = segments_group[segment_key]  # type: ignore[index]

        # Delete old text dataset
        if "text" in seg_group:  # type: ignore[operator]
            del seg_group["text"]  # type: ignore[index]

        # Create new text dataset with updated value
        seg_group.create_dataset("text", data=new_text.encode("utf-8"))  # type: ignore[union-attr]

        # Read back the updated segment to return
        segment = {
            "speaker": seg_group["speaker"][()].decode("utf-8"),  # type: ignore[index]
            "text": new_text,
            "start_time": float(seg_group["start_time"][()]),  # type: ignore[index]
            "end_time": float(seg_group["end_time"][()]),  # type: ignore[index]
        }

        # Optional fields
        if "confidence" in seg_group:  # type: ignore[operator]
            segment["confidence"] = float(seg_group["confidence"][()])  # type: ignore[index]

        if "improved_text" in seg_group:  # type: ignore[operator]
            segment["improved_text"] = seg_group["improved_text"][()].decode("utf-8")  # type: ignore[index]

    logger.info(
        "DIARIZATION_SEGMENT_UPDATED",
        session_id=session_id,
        segment_index=segment_index,
        text_length=len(new_text),
    )

    return segment


# ============================================================================
# SOAP CRUD Operations
# ============================================================================


def save_soap_data(
    session_id: str,
    soap_data: dict[str, Any],
    task_type: TaskType = TaskType.SOAP_GENERATION,
) -> str:
    """Save SOAP data to HDF5.

    Args:
        session_id: Session identifier
        soap_data: SOAP note data (subjective, objective, assessment, plan)
        task_type: Task type (default SOAP_GENERATION)

    Returns:
        HDF5 path to SOAP data
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _h5_lock:
        with h5py.File(CORPUS_PATH, "a") as f:
            task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

            # Create task if doesn't exist
            if task_path not in f:  # type: ignore[operator]
                f.create_group(task_path)  # type: ignore[union-attr]

            task_group = f[task_path]  # type: ignore[index]

            # Save SOAP data as JSON
            soap_json = json.dumps(soap_data)

            # Delete existing if present
            if "soap_data" in task_group:  # type: ignore[operator]
                del task_group["soap_data"]  # type: ignore[index]

            task_group.create_dataset(  # type: ignore[union-attr]
                "soap_data", data=soap_json.encode("utf-8")
            )

            # Save version to history (audit trail)
            if "version_history" not in task_group:  # type: ignore[operator]
                task_group.create_group("version_history")  # type: ignore[union-attr]

            history_group = task_group["version_history"]  # type: ignore[index]
            version_key = f"v_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            history_group.create_dataset(  # type: ignore[union-attr]
                version_key, data=soap_json.encode("utf-8")
            )

            logger.info(
                "SOAP_DATA_SAVED",
                session_id=session_id,
                task_type=task_type.value,
                version=version_key,
            )

    return f"{task_path}/soap_data"


def get_soap_data(
    session_id: str,
    task_type: TaskType = TaskType.SOAP_GENERATION,
) -> dict[str, Any]:
    """Get SOAP data from HDF5.

    Args:
        session_id: Session identifier
        task_type: Task type (default SOAP_GENERATION)

    Returns:
        SOAP data dictionary

    Raises:
        ValueError: If task or SOAP data not found
    """
    if not CORPUS_PATH.exists():
        raise ValueError(f"Corpus file not found: {CORPUS_PATH}")

    with open_h5_read() as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"Task {task_type.value} not found for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        if "soap_data" not in task_group:  # type: ignore[operator]
            raise ValueError(f"No SOAP data found for session {session_id}")

        soap_json = task_group["soap_data"][()].decode("utf-8")  # type: ignore[index]
        soap_data = json.loads(soap_json)

    logger.info(
        "SOAP_DATA_LOADED",
        session_id=session_id,
        task_type=task_type.value,
    )

    return soap_data


# ============================================================================
# ORDERS CRUD Operations
# ============================================================================


def create_order(
    session_id: str,
    order: dict[str, Any],
    task_type: TaskType = TaskType.ORDERS,
) -> str:
    """Create a new medical order.

    Args:
        session_id: Session identifier
        order: Order data {type, description, details}
        task_type: Task type (default ORDERS)

    Returns:
        Order ID
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    order_id = f"order_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}"

    with _h5_lock:
        with h5py.File(CORPUS_PATH, "a") as f:
            task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

            # Create task if doesn't exist
            if task_path not in f:  # type: ignore[operator]
                f.create_group(task_path)  # type: ignore[union-attr]

            task_group = f[task_path]  # type: ignore[index]

            # Create orders group if doesn't exist
            if "orders" not in task_group:  # type: ignore[operator]
                task_group.create_group("orders")  # type: ignore[union-attr]

            orders_group = task_group["orders"]  # type: ignore[index]

            # Save order as JSON
            order_data = {
                "id": order_id,
                "created_at": datetime.now(UTC).isoformat(),
                **order,
            }
            order_json = json.dumps(order_data)
            orders_group.create_dataset(order_id, data=order_json.encode("utf-8"))  # type: ignore[union-attr]

            logger.info(
                "ORDER_CREATED",
                session_id=session_id,
                order_id=order_id,
                order_type=order.get("type"),
            )

    return order_id


def get_orders(
    session_id: str,
    task_type: TaskType = TaskType.ORDERS,
) -> list[dict[str, Any]]:
    """Get all orders for a session.

    Args:
        session_id: Session identifier
        task_type: Task type (default ORDERS)

    Returns:
        List of order dictionaries
    """
    if not CORPUS_PATH.exists():
        raise ValueError(f"Corpus file not found: {CORPUS_PATH}")

    with open_h5_read() as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            # No orders task yet, return empty list
            return []

        task_group = f[task_path]  # type: ignore[index]

        if "orders" not in task_group:  # type: ignore[operator]
            return []

        orders_group = task_group["orders"]  # type: ignore[index]
        orders = []

        for order_key in orders_group.keys():
            order_json = orders_group[order_key][()].decode("utf-8")  # type: ignore[index]
            order_data = json.loads(order_json)
            orders.append(order_data)

    logger.info(
        "ORDERS_LOADED",
        session_id=session_id,
        order_count=len(orders),
    )

    return orders


def update_order(
    session_id: str,
    order_id: str,
    order: dict[str, Any],
    task_type: TaskType = TaskType.ORDERS,
) -> None:
    """Update an existing order.

    Args:
        session_id: Session identifier
        order_id: Order ID
        order: Updated order data
        task_type: Task type (default ORDERS)

    Raises:
        ValueError: If order not found
    """
    with _h5_lock:
        with h5py.File(CORPUS_PATH, "a") as f:
            task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

            if task_path not in f:  # type: ignore[operator]
                raise ValueError(f"No orders found for session {session_id}")

            task_group = f[task_path]  # type: ignore[index]

            if "orders" not in task_group:  # type: ignore[operator]
                raise ValueError(f"No orders found for session {session_id}")

            orders_group = task_group["orders"]  # type: ignore[index]

            if order_id not in orders_group:  # type: ignore[operator]
                raise ValueError(f"Order {order_id} not found")

            # Update order
            order_data = {
                "id": order_id,
                "updated_at": datetime.now(UTC).isoformat(),
                **order,
            }
            order_json = json.dumps(order_data)

            # Delete and recreate (HDF5 doesn't support in-place update)
            del orders_group[order_id]  # type: ignore[index]
            orders_group.create_dataset(order_id, data=order_json.encode("utf-8"))  # type: ignore[union-attr]

            logger.info(
                "ORDER_UPDATED",
                session_id=session_id,
                order_id=order_id,
            )


def delete_order(
    session_id: str,
    order_id: str,
    task_type: TaskType = TaskType.ORDERS,
) -> None:
    """Delete an order.

    Args:
        session_id: Session identifier
        order_id: Order ID
        task_type: Task type (default ORDERS)

    Raises:
        ValueError: If order not found
    """
    with _h5_lock:
        with h5py.File(CORPUS_PATH, "a") as f:
            task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

            if task_path not in f:  # type: ignore[operator]
                raise ValueError(f"No orders found for session {session_id}")

            task_group = f[task_path]  # type: ignore[index]

            if "orders" not in task_group:  # type: ignore[operator]
                raise ValueError(f"No orders found for session {session_id}")

            orders_group = task_group["orders"]  # type: ignore[index]

            if order_id not in orders_group:  # type: ignore[operator]
                raise ValueError(f"Order {order_id} not found")

            del orders_group[order_id]  # type: ignore[index]

            logger.info(
                "ORDER_DELETED",
                session_id=session_id,
                order_id=order_id,
            )
