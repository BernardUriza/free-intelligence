"""Audio blob storage per chunk in HDF5.

Handles audio file storage and retrieval for transcription chunks:
- add_audio_to_chunk: Attach audio bytes to an existing chunk
- get_chunk_audio_bytes: Retrieve audio from chunk (session-first, corpus fallback)
- _get_chunk_audio_legacy: Legacy implementation kept for reference

Audio is stored as numpy uint8 arrays within chunk groups, enabling
efficient binary storage alongside transcription metadata.

Author: Bernard Uriza Orozco
Created: 2025-11-14
Refactored: 2026-01-18 (modularization)
"""

from __future__ import annotations

import h5py
import numpy as np
from backend.models.task_type import TaskType
from backend.utils.common.logging.logger import get_logger
from backend.core.infrastructure.storage.infrastructure.hdf5.session_h5_manager import CORPUS_PATH
from backend.core.infrastructure.storage.infrastructure.hdf5.session_locks import locked_session_h5
from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.h5_file_access import _h5_lock

logger = get_logger(__name__)

__all__ = [
    "add_audio_to_chunk",
    "get_chunk_audio_bytes",
    "_get_chunk_audio_legacy",
]


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

    with (
        _h5_lock,
        locked_session_h5(session_id, mode="a") as f,
    ):  # Lock H5 file to prevent concurrent access errors
        chunk_path = f"/sessions/{session_id}/tasks/{task_type.value}/chunks/chunk_{chunk_idx}"

        if chunk_path not in f:  # type: ignore[operator]
            raise ValueError(f"Chunk {chunk_idx} does not exist for session {session_id}")

        chunk_group = f[chunk_path]  # type: ignore[index]

        # Delete existing audio if present
        if filename in chunk_group:  # type: ignore[operator]
            del chunk_group[filename]  # type: ignore[index]

        # Create audio dataset (binary data with opaque dtype)
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
) -> bytes | None:
    """Get audio bytes from a chunk.

    Searches in two locations (fallback pattern):
    1. Session-specific HDF5 (storage/sessions/{session_id}.h5)
    2. Corpus HDF5 (storage/corpus.h5) - for medical chunks

    Args:
        session_id: Session identifier
        task_type: Task type
        chunk_idx: Chunk index
        filename: Audio filename (default audio.webm)

    Returns:
        Audio bytes or None if not found
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 1. Try session-specific HDF5 first
    try:
        with locked_session_h5(session_id, mode="r") as f:
            chunk_path = f"/sessions/{session_id}/tasks/{task_type.value}/chunks/chunk_{chunk_idx}"

            if chunk_path in f:  # type: ignore[operator]
                chunk_group = f[chunk_path]  # type: ignore[index]
                if filename in chunk_group:  # type: ignore[operator]
                    audio_dataset = chunk_group[filename]  # type: ignore[index]
                    audio_bytes = bytes(audio_dataset[()])  # type: ignore[index]
                    logger.info(
                        "CHUNK_AUDIO_READ",
                        session_id=session_id,
                        source="session_h5",
                        chunk_idx=chunk_idx,
                        size_bytes=len(audio_bytes),
                    )
                    return audio_bytes
    except Exception:
        pass  # Try corpus.h5 as fallback

    # 2. Try corpus.h5 (medical chunks saved by MedicalChunkHandler)
    try:
        if CORPUS_PATH.exists():
            with h5py.File(CORPUS_PATH, "r") as f:
                # Medical handler saves as "audio" not "audio.webm"
                for audio_key in ["audio", filename]:
                    audio_path = f"/sessions/{session_id}/tasks/{task_type.name.lower()}/chunks/chunk_{chunk_idx}/{audio_key}"
                    if audio_path in f:  # type: ignore[operator]
                        audio_bytes = bytes(f[audio_path][()])  # type: ignore[index]
                        logger.info(
                            "CHUNK_AUDIO_READ",
                            session_id=session_id,
                            source="corpus_h5",
                            chunk_idx=chunk_idx,
                            audio_key=audio_key,
                            size_bytes=len(audio_bytes),
                        )
                        return audio_bytes
    except Exception as e:
        logger.debug("CORPUS_AUDIO_READ_FAILED", error=str(e))

    # Not found in either location
    logger.warning(
        "AUDIO_NOT_FOUND_IN_CHUNK",
        session_id=session_id,
        task_type=task_type.value,
        chunk_idx=chunk_idx,
        filename=filename,
        searched=["session_h5", "corpus_h5"],
    )
    return None


def _get_chunk_audio_legacy(
    session_id: str,
    task_type: TaskType,
    chunk_idx: int,
    filename: str,
) -> bytes | None:
    """Legacy implementation - kept for reference only."""
    try:
        with locked_session_h5(session_id, mode="r") as f:
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
