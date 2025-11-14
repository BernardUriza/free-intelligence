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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import h5py

from backend.logger import get_logger
from backend.models.task_type import TaskStatus, TaskType

logger = get_logger(__name__)

# HDF5 corpus path
CORPUS_PATH = Path(__file__).parent.parent.parent / "storage" / "corpus.h5"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TASK MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def ensure_task_exists(
    session_id: str,
    task_type: TaskType | str,
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

    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(CORPUS_PATH, "a") as f:
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


def task_exists(session_id: str, task_type: TaskType | str) -> bool:
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

    with h5py.File(CORPUS_PATH, "r") as f:
        return task_path in f  # type: ignore[operator]


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
    task_type: TaskType | str,
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


def get_task_metadata(session_id: str, task_type: TaskType | str) -> Optional[dict[str, Any]]:
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
    task_type: TaskType | str,
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


def get_task_chunks(session_id: str, task_type: TaskType | str) -> list[dict[str, Any]]:
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
                chunks.append(
                    {
                        "chunk_idx": int(chunk_name.split("_")[1]),
                        "transcript": chunk_group["transcript"][()].decode("utf-8"),  # type: ignore[index]
                        "audio_hash": chunk_group["audio_hash"][()].decode("utf-8"),  # type: ignore[index]
                        "duration": float(chunk_group["duration"][()]),  # type: ignore[index]
                        "language": chunk_group["language"][()].decode("utf-8"),  # type: ignore[index]
                        "timestamp_start": float(chunk_group["timestamp_start"][()]),  # type: ignore[index]
                        "timestamp_end": float(chunk_group["timestamp_end"][()]),  # type: ignore[index]
                        "confidence": float(chunk_group["confidence"][()]),  # type: ignore[index]
                        "audio_quality": float(chunk_group["audio_quality"][()]),  # type: ignore[index]
                        "created_at": chunk_group["created_at"][()].decode("utf-8"),  # type: ignore[index]
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


def get_task_transcript(session_id: str, task_type: TaskType | str) -> str:
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
