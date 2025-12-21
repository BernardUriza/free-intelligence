"""DEPRECATED: Use fi_common.infrastructure.persistence.hdf5.task_repository instead.

This module is deprecated and maintained only for backward compatibility.
All new code should use task_repository.py with the task-based architecture.

Migration:
  OLD: from backend.src.fi_storage.infrastructure.hdf5.session_chunks_schema import append_chunk_to_session
  NEW: from backend.src.fi_common.infrastructure.persistence.hdf5.task_repository import append_chunk_to_task, ensure_task_exists

  OLD: append_chunk_to_session(session_id, chunk_idx, ...)
  NEW: ensure_task_exists(session_id, TaskType.TRANSCRIPTION)
       append_chunk_to_task(session_id, TaskType.TRANSCRIPTION, chunk_idx, ...)

Author: Bernard Uriza Orozco
Deprecated: 2025-11-14
Card: Architecture refactor - task-based HDF5
"""

from __future__ import annotations

import warnings
from backend.src.fi_common.infrastructure.persistence.hdf5.task_repository import (
    append_chunk_to_task,
    ensure_task_exists,
    get_task_chunks,
    get_task_transcript,
)

from backend.src.fi_common.logging.logger import get_logger
from backend.models.task_type import TaskType

logger = get_logger(__name__)


def _deprecation_warning(old_function: str, new_function: str) -> None:
    """Emit deprecation warning."""
    warnings.warn(
        f"{old_function}() is deprecated. Use {new_function}() from task_repository instead.",
        DeprecationWarning,
        stacklevel=3,
    )
    logger.warning(
        "DEPRECATED_FUNCTION_CALL",
        old_function=old_function,
        new_function=new_function,
        recommendation="Migrate to task_repository.py",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DEPRECATED FUNCTIONS (wrappers to task_repository)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def ensure_session_group(session_id: str) -> str:
    """DEPRECATED: Use ensure_task_exists() instead."""
    _deprecation_warning("ensure_session_group", "ensure_task_exists")
    return ensure_task_exists(session_id, TaskType.TRANSCRIPTION, allow_existing=True)


def append_chunk_to_session(
    session_id: str,
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
    """DEPRECATED: Use append_chunk_to_task() instead.

    This function automatically ensures TRANSCRIPTION task exists and appends chunk to it.
    """
    _deprecation_warning("append_chunk_to_session", "append_chunk_to_task")

    # Ensure task exists (backward compat)
    ensure_task_exists(session_id, TaskType.TRANSCRIPTION, allow_existing=True)

    # Append chunk
    return append_chunk_to_task(
        session_id=session_id,
        task_type=TaskType.TRANSCRIPTION,
        chunk_idx=chunk_idx,
        transcript=transcript,
        audio_hash=audio_hash,
        duration=duration,
        language=language,
        timestamp_start=timestamp_start,
        timestamp_end=timestamp_end,
        confidence=confidence,
        audio_quality=audio_quality,
    )


def get_session_chunks(session_id: str) -> list[dict]:
    """DEPRECATED: Use get_task_chunks() instead."""
    _deprecation_warning("get_session_chunks", "get_task_chunks")
    return get_task_chunks(session_id, TaskType.TRANSCRIPTION)


def get_session_transcript(session_id: str) -> str:
    """DEPRECATED: Use get_task_transcript() instead."""
    _deprecation_warning("get_session_transcript", "get_task_transcript")
    return get_task_transcript(session_id, TaskType.TRANSCRIPTION)


def update_ml_quality_flags(
    session_id: str,
    usable_for_training: bool = True,  # noqa: ARG001
    human_verified: bool = True,  # noqa: ARG001
) -> None:
    """DEPRECATED: ML quality flags are no longer used in task-based architecture.

    This function is a no-op for backward compatibility.
    """
    _deprecation_warning("update_ml_quality_flags", "N/A (removed)")
    logger.info(
        "ML_QUALITY_FLAGS_NOOP",
        session_id=session_id,
        reason="ml_ready/ structure removed in task-based architecture",
    )


def get_ml_sessions(
    usable_only: bool = True,  # noqa: ARG001
    verified_only: bool = False,  # noqa: ARG001
) -> list[str]:
    """DEPRECATED: ML sessions filtering is no longer available.

    Returns empty list for backward compatibility.
    """
    _deprecation_warning("get_ml_sessions", "N/A (removed)")
    logger.info(
        "ML_SESSIONS_NOOP",
        reason="ml_ready/ structure removed in task-based architecture",
    )
    return []


def save_full_audio_metadata(
    session_id: str,
    audio_path: str,
    total_duration: float,
    total_chunks: int,
) -> None:
    """DEPRECATED: Use update_task_metadata() instead.

    This function is a no-op for backward compatibility.
    """
    _deprecation_warning("save_full_audio_metadata", "update_task_metadata")
    logger.info(
        "AUDIO_METADATA_NOOP",
        session_id=session_id,
        audio_path=audio_path,
        total_duration=total_duration,
        total_chunks=total_chunks,
        reason="Use update_task_metadata() for task-specific metadata",
    )
