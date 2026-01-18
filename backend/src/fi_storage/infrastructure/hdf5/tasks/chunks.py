"""Chunk-related operations for HDF5 task storage.

Handles all chunk CRUD operations within transcription tasks:
- append_chunk_to_task: Add new transcription chunk (append-only)
- count_task_chunks: Fast chunk counting (no data reading)
- get_task_chunks: Retrieve all chunks for a task
- get_task_transcript: Get concatenated transcript
- create_empty_chunk: Create placeholder chunk for audio storage
- update_chunk_dataset: Update a single field in a chunk
- batch_update_chunk_datasets: Atomically update multiple chunk fields

Author: Bernard Uriza Orozco
Created: 2025-11-14
Refactored: 2026-01-18 (modularization)
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from typing import Any, Union

import h5py
from backend.models.task_type import TaskType
from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_storage.infrastructure.hdf5.session_locks import locked_session_h5
from backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle import task_exists
from backend.src.fi_storage.infrastructure.hdf5.tasks.metadata import get_task_metadata

logger = get_logger(__name__)

# Thread lock for HDF5 file access (prevents concurrent access errors)
_h5_lock = threading.RLock()


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
    provider: str = "deepgram",
    polling_attempts: int = 0,
    resolution_time_seconds: float = 0.0,
    retry_attempts: int = 0,
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
        provider: STT provider used (deepgram, azure_whisper)
        polling_attempts: Number of polling attempts until completion
        resolution_time_seconds: Time from upload to completion (seconds)
        retry_attempts: Number of retries before success

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

    with locked_session_h5(session_id, mode="a") as f:
        task_group = f[task_path]  # type: ignore[index]

        # Create chunks group if not exists
        if "chunks" not in task_group:  # type: ignore[operator]
            task_group.create_group("chunks")  # type: ignore[index]

        chunks_group = task_group["chunks"]  # type: ignore[index]

        # Check if chunk already exists (append-only)
        if f"chunk_{chunk_idx}" in chunks_group:  # type: ignore[operator]
            raise ValueError(
                f"Chunk {chunk_idx} already exists for task {task_type_str} (append-only violation)"
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
        # NEW: Transcription metrics
        chunk_group.create_dataset(  # type: ignore[attr-defined]
            "provider",
            data=provider,
            dtype=h5py.string_dtype(encoding="utf-8"),
        )
        chunk_group.create_dataset("polling_attempts", data=polling_attempts, dtype="int32")  # type: ignore[attr-defined]
        chunk_group.create_dataset(
            "resolution_time_seconds", data=resolution_time_seconds, dtype="float32"
        )  # type: ignore[attr-defined]
        chunk_group.create_dataset("retry_attempts", data=retry_attempts, dtype="int32")  # type: ignore[attr-defined]

    logger.info(
        "CHUNK_APPENDED_TO_TASK",
        session_id=session_id,
        task_type=task_type_str,
        chunk_idx=chunk_idx,
        chunk_path=chunk_path,
        transcript_length=len(transcript),
        duration=duration,
        provider=provider,
        polling_attempts=polling_attempts,
        resolution_time_seconds=resolution_time_seconds,
        retry_attempts=retry_attempts,
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

        with locked_session_h5(session_id, mode="r") as f:
            if chunks_path not in f:  # type: ignore[operator]
                # Task exists but no chunks yet
                return (expected_total, 0)

            chunks_group = f[chunks_path]  # type: ignore[index]

            # Count chunks that have VALID transcripts (non-empty)
            # Fix: Cannot trust chunk existence alone - must verify transcript content
            processed = 0
            for chunk_key in chunks_group:  # type: ignore[union-attr]
                chunk_group = chunks_group[chunk_key]  # type: ignore[index]

                # Check if transcript exists and is non-empty
                if "transcript" in chunk_group:  # type: ignore[operator]
                    transcript_data = chunk_group["transcript"][()]  # type: ignore[index]

                    # Handle both string and bytes
                    if isinstance(transcript_data, bytes):
                        transcript_text = transcript_data.decode("utf-8", errors="ignore")
                    else:
                        transcript_text = str(transcript_data)

                    # Only count if transcript has actual content
                    if transcript_text and transcript_text.strip():
                        processed += 1

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
        with locked_session_h5(session_id, mode="r") as f:
            if chunks_path not in f:  # type: ignore[operator]
                return []

            chunks_group = f[chunks_path]  # type: ignore[index]
            chunks = []

            for chunk_name in sorted(chunks_group):  # type: ignore[union-attr]
                chunk_group = chunks_group[chunk_name]  # type: ignore[index]
                chunk_idx = int(chunk_name.split("_")[1])
                transcript = chunk_group["transcript"][()].decode("utf-8")  # type: ignore[index]

                # Determine status based on transcript presence
                status = "completed" if transcript else "pending"

                # Read metrics (with fallback for older chunks)
                provider = (
                    chunk_group["provider"][()].decode("utf-8")
                    if "provider" in chunk_group  # type: ignore[operator]
                    else "unknown"
                )  # type: ignore[index]
                polling_attempts = (
                    int(chunk_group["polling_attempts"][()])
                    if "polling_attempts" in chunk_group  # type: ignore[operator]
                    else 0
                )  # type: ignore[index]
                resolution_time_seconds = (
                    float(chunk_group["resolution_time_seconds"][()])
                    if "resolution_time_seconds" in chunk_group  # type: ignore[operator]
                    else 0.0
                )  # type: ignore[index]
                retry_attempts = (
                    int(chunk_group["retry_attempts"][()]) if "retry_attempts" in chunk_group else 0  # type: ignore[operator]
                )  # type: ignore[index]

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
                        # NEW: Transcription metrics
                        "provider": provider,
                        "polling_attempts": polling_attempts,
                        "resolution_time_seconds": resolution_time_seconds,
                        "retry_attempts": retry_attempts,
                        # Legacy fields
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
    if not task_exists(session_id, task_type):
        raise ValueError(f"Task {task_type.value} does not exist")

    task_path = f"/sessions/{session_id}/tasks/{task_type.value}"
    chunk_path = f"{task_path}/chunks/chunk_{chunk_idx}"

    with (
        _h5_lock,
        locked_session_h5(session_id, mode="a") as f,
    ):  # Lock H5 file to prevent concurrent access errors
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
        with (
            _h5_lock,
            locked_session_h5(session_id, mode="a") as f,
        ):  # Lock H5 file to prevent concurrent access errors
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

    return False


def batch_update_chunk_datasets(
    session_id: str,
    task_type: Union[TaskType, str],
    chunk_idx: int,
    updates: dict[str, Union[str, float, int]],
    max_retries: int = 5,
    initial_backoff: float = 0.1,
) -> bool:
    """Atomically update multiple chunk fields with exponential backoff retry.

    This solves the SWMR race condition where concurrent readers block writes.
    All fields are updated in a single transaction to maintain consistency.

    Args:
        session_id: Session identifier
        task_type: Type of task
        chunk_idx: Chunk index
        updates: Dict of field_name -> value to update
        max_retries: Maximum retry attempts (default 5)
        initial_backoff: Initial backoff time in seconds (default 0.1s)

    Returns:
        True if all updates succeeded, False otherwise

    Example:
        batch_update_chunk_datasets(
            session_id="abc123",
            task_type=TaskType.TRANSCRIPTION,
            chunk_idx=6,
            updates={
                "transcript": "Hello world",
                "language": "es",
                "confidence": 0.95,
                "duration": 7.5,
                "provider": "deepgram",
            }
        )
    """
    if not task_exists(session_id, task_type):
        logger.warning("TASK_NOT_EXISTS", session_id=session_id, task_type=str(task_type))
        return False

    task_type_str = task_type.value if isinstance(task_type, TaskType) else task_type
    chunk_path = f"/sessions/{session_id}/tasks/{task_type_str}/chunks/chunk_{chunk_idx}"

    for attempt in range(max_retries):
        try:
            with (
                _h5_lock,
                locked_session_h5(session_id, mode="a") as f,
            ):  # Lock H5 file to prevent concurrent access errors
                if chunk_path not in f:  # type: ignore[operator]
                    logger.warning(
                        "CHUNK_NOT_FOUND",
                        session_id=session_id,
                        task_type=task_type_str,
                        chunk_idx=chunk_idx,
                    )
                    return False

                chunk_group = f[chunk_path]  # type: ignore[index]

                # Update all fields atomically
                for field, value in updates.items():
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
                        "BATCH_CHUNK_UPDATE_SUCCESS",
                        session_id=session_id,
                        task_type=task_type_str,
                        chunk_idx=chunk_idx,
                        fields=list(updates.keys()),
                        attempt=attempt + 1,
                    )
                    return True

        except (OSError, BlockingIOError) as e:
            # HDF5 lock conflict - retry with exponential backoff
            backoff = initial_backoff * (2**attempt)
            if "already open" in str(e) or "Unable to synchronously open" in str(e):
                if attempt < max_retries - 1:
                    logger.warning(
                        "HDF5_LOCK_CONFLICT_RETRY",
                        session_id=session_id,
                        chunk_idx=chunk_idx,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        backoff_ms=int(backoff * 1000),
                        error=str(e)[:200],
                    )
                    time.sleep(backoff)
                    continue
                else:
                    logger.error(
                        "HDF5_LOCK_CONFLICT_MAX_RETRIES",
                        session_id=session_id,
                        chunk_idx=chunk_idx,
                        max_retries=max_retries,
                        error=str(e),
                    )
                    return False
            else:
                # Not a lock error, don't retry
                logger.error(
                    "BATCH_CHUNK_UPDATE_FAILED",
                    session_id=session_id,
                    task_type=task_type_str,
                    chunk_idx=chunk_idx,
                    fields=list(updates.keys()),
                    error=str(e),
                )
                return False

        except Exception as e:
            logger.error(
                "BATCH_CHUNK_UPDATE_UNEXPECTED_ERROR",
                session_id=session_id,
                task_type=task_type_str,
                chunk_idx=chunk_idx,
                fields=list(updates.keys()),
                error=str(e),
            )
            return False

    # Should never reach here
    return False


__all__ = [
    "append_chunk_to_task",
    "count_task_chunks",
    "get_task_chunks",
    "get_task_transcript",
    "create_empty_chunk",
    "update_chunk_dataset",
    "batch_update_chunk_datasets",
]
