"""Task and session metadata CRUD operations.

Handles job_metadata storage within tasks:
- update_task_metadata: Update task metadata (partial merge)
- get_task_metadata: Read task metadata

Author: Bernard Uriza Orozco
Created: 2025-11-14
Refactored: 2026-01-18 (modularization)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Union

import h5py
from backend.models.task_type import TaskType
from backend.utils.common.logging.logger import get_logger
from infrastructure.storage.infrastructure.hdf5.session_locks import locked_session_h5
from infrastructure.storage.infrastructure.hdf5.tasks.lifecycle import task_exists

logger = get_logger(__name__)


def update_task_metadata(
    session_id: str,
    task_type: Union[TaskType, str],
    metadata: dict[str, Any],
) -> None:
    """Update job metadata for a task.

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files.

    WARNING: Contains del operation violating append-only pattern.
    See docs/CRITICAL_TECH_DEBT_EVENT_SOURCING.md for remediation plan.

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

    with locked_session_h5(session_id, mode="a") as f:
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

        # Delete old dataset (VIOLATION: append-only)
        if "job_metadata" in task_group:  # type: ignore[operator]
            # Log deletion for audit trail (HIPAA compliance)
            old_data = task_group["job_metadata"][()]  # type: ignore[index]
            old_value = old_data.decode("utf-8", errors="ignore") if isinstance(old_data, bytes) else str(old_data)
            logger.warning(
                "DATASET_DELETED",
                session_id=session_id,
                path=f"{task_path}/job_metadata",
                old_value_size=len(old_value),
                old_value_preview=old_value[:100],
                reason="metadata_update",
                timestamp=datetime.now(UTC).isoformat(),
            )
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


def get_task_metadata(session_id: str, task_type: Union[TaskType, str]) -> dict[str, Any] | None:
    """Get job metadata for a task.

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files.

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
        with locked_session_h5(session_id, mode="r") as f:
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


__all__ = [
    "get_task_metadata",
    "update_task_metadata",
]
