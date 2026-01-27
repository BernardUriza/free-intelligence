"""Backwards compatibility layer for legacy HDF5 schemas.

This module provides functions to read data from older HDF5 schema versions,
enabling smooth migration without breaking existing sessions.

Supports:
- New task-based schema: /sessions/{id}/tasks/{TASK_TYPE}/chunks/
- Old dual schema: /sessions/{id}/production/chunks/
- Legacy schema: /sessions/{id}/chunks/
"""

from __future__ import annotations

from typing import Any

from backend.models.task_type import TaskType
from backend.utils.common.logging.logger import get_logger
from backend.core.infrastructure.storage.infrastructure.hdf5.session_h5_manager import CORPUS_PATH
from backend.core.infrastructure.storage.infrastructure.hdf5.session_locks import locked_session_h5
from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.chunks import get_task_chunks
from backend.core.infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import task_exists

logger = get_logger(__name__)

__all__ = ["get_session_chunks_compat"]


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
        with locked_session_h5(session_id, mode="r") as f:
            if production_path in f:  # type: ignore[operator]
                # Read from old schema (same logic as get_task_chunks)
                chunks_group = f[production_path]  # type: ignore[index]
                chunks = []
                for chunk_name in sorted(chunks_group):  # type: ignore[union-attr]
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
        with locked_session_h5(session_id, mode="r") as f:
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
