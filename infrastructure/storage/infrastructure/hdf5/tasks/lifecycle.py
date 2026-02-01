"""Task lifecycle management - creation, existence checks, and listing.

Handles the fundamental operations for task existence:
- ensure_task_exists: Create task if not exists
- task_exists: Check if task exists
- list_session_tasks: List all tasks for a session

Author: Bernard Uriza Orozco
Created: 2025-11-14
Refactored: 2026-01-18 (modularization)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Union

import h5py
from backend.models.task_type import TaskStatus, TaskType
from backend.utils.common.logging.logger import get_logger
from infrastructure.storage.infrastructure.hdf5.session_h5_manager import (
    get_session_h5_path,
)
from infrastructure.storage.infrastructure.hdf5.session_locks import locked_session_h5

logger = get_logger(__name__)


def ensure_task_exists(
    session_id: str,
    task_type: Union[TaskType, str],
    allow_existing: bool = False,
) -> str:
    """Ensure task group exists for session.

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files + per-session locks.

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

    # P0.5 FIX: Use session-level file with per-session lock
    with locked_session_h5(session_id, mode="a") as f:
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

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files.

    Args:
        session_id: Session identifier
        task_type: Type of task

    Returns:
        True if task exists, False otherwise
    """
    session_file = get_session_h5_path(session_id)
    if not session_file.exists():
        return False

    task_type_str = task_type.value if isinstance(task_type, TaskType) else task_type
    task_path = f"/sessions/{session_id}/tasks/{task_type_str}"

    try:
        with locked_session_h5(session_id, mode="r") as f:
            return task_path in f  # type: ignore[operator]
    except OSError:
        # File exists but is not a valid HDF5 file
        return False


def list_session_tasks(session_id: str) -> list[str]:
    """List all task types for a session.

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files.

    Args:
        session_id: Session identifier

    Returns:
        List of task type strings (e.g., ["TRANSCRIPTION", "DIARIZATION"])
    """
    session_file = get_session_h5_path(session_id)
    if not session_file.exists():
        return []

    tasks_path = f"/sessions/{session_id}/tasks"

    try:
        with locked_session_h5(session_id, mode="r") as f:
            if tasks_path not in f:  # type: ignore[operator]
                return []

            tasks_group = f[tasks_path]  # type: ignore[index]
            return list(tasks_group.keys())  # type: ignore[return-value]
    except Exception as e:
        logger.error("LIST_TASKS_FAILED", session_id=session_id, error=str(e))
        return []


__all__ = [
    "ensure_task_exists",
    "list_session_tasks",
    "task_exists",
]
