"""Transcription source storage operations for HDF5.

This module handles storage of transcription source data within HDF5 task structures:
- WebSpeech instant preview transcripts (real-time browser transcription)
- Full concatenated transcription text
- Full audio file storage

All operations use session-level HDF5 files with per-session locking for thread safety.

Storage paths within task:
    /sessions/{session_id}/tasks/TRANSCRIPTION/
        ├── webspeech_final       # JSON list of WebSpeech transcript strings
        ├── full_transcription    # Complete transcription text
        └── full_audio.webm       # Raw audio bytes (numpy uint8 array)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import h5py
import numpy as np
from backend.models.task_type import TaskType
from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_storage.infrastructure.hdf5.session_locks import locked_session_h5

if TYPE_CHECKING:
    pass

__all__ = [
    "add_webspeech_transcripts",
    "add_full_transcription",
    "add_full_audio",
]

logger = get_logger(__name__)


def add_webspeech_transcripts(
    session_id: str, transcripts: list[str], task_type: TaskType = TaskType.TRANSCRIPTION
) -> str:
    """Add WebSpeech instant preview transcripts to TRANSCRIPTION task.

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files + per-session locks.

    Args:
        session_id: Session identifier
        transcripts: List of WebSpeech transcript strings
        task_type: Task type (default TRANSCRIPTION)

    Returns:
        HDF5 path to webspeech_final dataset
    """
    # P0.5 FIX: Use session-level file with per-session lock (safe for concurrent tasks)
    with locked_session_h5(session_id, mode="a") as f:
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

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files + per-session locks.

    Args:
        session_id: Session identifier
        full_text: Complete transcription text
        task_type: Task type (default TRANSCRIPTION)

    Returns:
        HDF5 path to full_transcription dataset
    """
    # P0.5 FIX: Use session-level file with per-session lock (safe for concurrent tasks)
    with locked_session_h5(session_id, mode="a") as f:
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

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files + per-session locks.

    Args:
        session_id: Session identifier
        audio_bytes: Raw audio bytes
        filename: Audio filename (default full_audio.webm)
        task_type: Task type (default TRANSCRIPTION)

    Returns:
        HDF5 path to audio dataset
    """
    # P0.5 FIX: Use session-level file with per-session lock (safe for concurrent tasks)
    with locked_session_h5(session_id, mode="a") as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"Task {task_type.value} does not exist for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        # Delete existing audio if present
        if filename in task_group:  # type: ignore[operator]
            del task_group[filename]  # type: ignore[index]

        # Create audio dataset (binary data with opaque dtype)
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
