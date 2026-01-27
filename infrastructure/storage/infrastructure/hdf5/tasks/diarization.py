"""Diarization segment storage operations for HDF5 task storage.

Handles all diarization segment CRUD operations:
- save_diarization_segments: Save speaker-attributed segments (append-only)
- get_diarization_segments: Retrieve all segments for a session
- update_diarization_segment_text: Update text of a specific segment

Segments include speaker attribution, text, timestamps, and optional
confidence scores and improved text from post-processing.

Author: Bernard Uriza Orozco
Created: 2025-11-14
Refactored: 2026-01-18 (modularization)
"""

from __future__ import annotations

from typing import Any

from backend.models.task_type import TaskType
from backend.utils.common.logging.logger import get_logger
from infrastructure.storage.infrastructure.hdf5.session_h5_manager import (
    CORPUS_PATH,
    get_session_h5_path,
)
from infrastructure.storage.infrastructure.hdf5.session_locks import locked_session_h5
from infrastructure.storage.infrastructure.hdf5.tasks.h5_file_access import open_h5_read

__all__ = [
    "save_diarization_segments",
    "get_diarization_segments",
    "update_diarization_segment_text",
]

logger = get_logger(__name__)


def save_diarization_segments(
    session_id: str,
    segments: list,
    task_type: TaskType = TaskType.DIARIZATION,
) -> str:
    """Save diarization segments to HDF5.

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files + per-session locks.

    Args:
        session_id: Session identifier
        segments: List of DiarizationSegment objects
        task_type: Task type (default DIARIZATION)

    Returns:
        HDF5 path to segments group
    """
    # P0.5 FIX: Use session-level file with per-session lock (safe for concurrent tasks)
    with locked_session_h5(session_id, mode="a") as f:
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
        segment_keys = sorted(segments_group, key=lambda x: int(x.split("_")[1]))

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

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files + per-session locks.

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
    # P0.5 FIX: Use session-level file with per-session lock (safe for concurrent tasks)
    session_h5_path = get_session_h5_path(session_id)
    if not session_h5_path.exists():
        raise ValueError(f"Session file not found: {session_h5_path}")

    with locked_session_h5(session_id, mode="a") as f:
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
