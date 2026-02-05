"""Task Metadata Mixin - Basic task CRUD operations.

Handles task lifecycle:
- Task creation and metadata storage
- Task existence checks
- Task deletion

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor from monolithic task_repository.py)
"""

from __future__ import annotations

from typing import Any

import h5py

from backend.utils.coder.utils.exceptions import SessionNotFoundError
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class TaskMetadataMixin:
    """Mixin for task metadata operations.

    Requires _HDF5Base as base class (provides h5_file_path, TASKS_GROUP, serializers).
    """

    def get_task_metadata(self, session_id: str, task_type: str) -> dict[str, Any] | None:
        """Get task metadata.

        Args:
            session_id: Session identifier
            task_type: Task type (e.g., "transcription", "soap_generation")

        Returns:
            Task metadata dict or None if task doesn't exist
        """
        try:
            with h5py.File(self.h5_file_path, "r") as f:
                task_path = self._get_task_path(session_id, task_type)
                if task_path not in f:
                    return None

                task_group = f[task_path]
                metadata = dict(task_group.attrs)

                # Deserialize JSON values
                return {key: self._deserialize_value(val) for key, val in metadata.items()}

        except Exception as e:
            logger.error(
                "GET_TASK_METADATA_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            return None

    def task_exists(self, session_id: str, task_type: str) -> bool:
        """Check if task exists.

        Args:
            session_id: Session identifier
            task_type: Task type

        Returns:
            True if task exists
        """
        try:
            with h5py.File(self.h5_file_path, "r") as f:
                task_path = self._get_task_path(session_id, task_type)
                return task_path in f
        except Exception as e:
            logger.error(
                "TASK_EXISTS_CHECK_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            return False

    def ensure_task_exists(
        self, session_id: str, task_type: str, metadata: dict[str, Any] | None = None
    ) -> str:
        """Ensure task exists, create if not (with referential integrity).

        Args:
            session_id: Session identifier
            task_type: Task type
            metadata: Optional initial metadata

        Returns:
            Task identifier (f"{session_id}/{task_type}")

        Raises:
            SessionNotFoundError: If session_repository is injected and session doesn't exist
        """
        # REFERENTIAL INTEGRITY: Validate session exists BEFORE creating task
        if self.session_repository is not None:
            if not self.session_repository.exists(session_id):
                logger.error(
                    "TASK_CREATE_SESSION_NOT_FOUND",
                    session_id=session_id,
                    task_type=task_type,
                    message="Cannot create task for non-existent session",
                )
                raise SessionNotFoundError(
                    f"Session {session_id} not found. Cannot create task {task_type}."
                )

        try:
            with h5py.File(self.h5_file_path, "a") as f:
                task_group = self._ensure_task_group(f, session_id, task_type)

                # Set metadata if provided and task was just created
                if metadata and len(task_group.attrs) == 0:
                    serialized = {
                        key: self._serialize_value(val) for key, val in metadata.items()
                    }
                    for key, value in serialized.items():
                        task_group.attrs[key] = value

                    logger.info(
                        "TASK_CREATED",
                        session_id=session_id,
                        task_type=task_type,
                    )

            return f"{session_id}/{task_type}"

        except Exception as e:
            logger.error(
                "ENSURE_TASK_EXISTS_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            raise

    def save_task_metadata(
        self, session_id: str, task_type: str, metadata: dict[str, Any]
    ) -> None:
        """Save task metadata.

        Args:
            session_id: Session identifier
            task_type: Task type
            metadata: Metadata to save (merged with existing)
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                task_group = self._ensure_task_group(f, session_id, task_type)

                # Update metadata
                serialized = {key: self._serialize_value(val) for key, val in metadata.items()}
                for key, value in serialized.items():
                    task_group.attrs[key] = value

                logger.info(
                    "TASK_METADATA_SAVED",
                    session_id=session_id,
                    task_type=task_type,
                )

        except Exception as e:
            logger.error(
                "SAVE_TASK_METADATA_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            raise

    def delete_by_session(self, session_id: str) -> int:
        """Delete all tasks for a session (cascade delete).

        Args:
            session_id: Session identifier

        Returns:
            Number of task types deleted

        Purpose:
            Enables cascade delete when session is removed.
            Prevents orphaned tasks with invalid session_id references.
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                session_tasks_path = f"{self.TASKS_GROUP}/{session_id}"

                if session_tasks_path not in f:
                    logger.debug(
                        "DELETE_BY_SESSION_NO_TASKS",
                        session_id=session_id,
                        message="No tasks found for session (already deleted or never created)",
                    )
                    return 0

                # Count task types before deletion
                session_group = f[session_tasks_path]
                task_types_count = len(session_group.keys())

                # Delete entire session group (all task types)
                del f[session_tasks_path]

                logger.info(
                    "DELETE_BY_SESSION_SUCCESS",
                    session_id=session_id,
                    task_types_deleted=task_types_count,
                )

                return task_types_count

        except Exception as e:
            logger.error(
                "DELETE_BY_SESSION_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def delete_task(self, session_id: str, task_type: str) -> bool:
        """Delete a specific task and all its chunks.

        Args:
            session_id: Session UUID
            task_type: Task type (e.g., "transcription", "soap_generation")

        Returns:
            True if deletion successful, False if task not found

        Raises:
            IOError: If delete operation fails
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                task_path = self._get_task_path(session_id, task_type)

                if task_path not in f:
                    logger.debug(
                        "DELETE_TASK_NOT_FOUND",
                        session_id=session_id,
                        task_type=task_type,
                    )
                    return False

                # Delete the task group (includes all chunks and metadata)
                del f[task_path]

                logger.info(
                    "DELETE_TASK_SUCCESS",
                    session_id=session_id,
                    task_type=task_type,
                )
                return True

        except Exception as e:
            logger.error(
                "DELETE_TASK_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            raise IOError(f"Failed to delete task {task_type} for session {session_id}: {e}") from e

    def get_task_progress(self, session_id: str, task_type: str) -> dict[str, Any]:
        """Get task progress summary (stub implementation).

        Args:
            session_id: Session UUID
            task_type: Task type

        Returns:
            Dict with keys:
                - status: str (pending, in_progress, completed, failed)
                - total_chunks: int
                - processed_chunks: int
                - progress_percent: float (0.0-100.0)
                - estimated_completion: str | None (ISO 8601)

        Raises:
            FileNotFoundError: If task not found
        """
        try:
            metadata = self.get_task_metadata(session_id, task_type)
            status = metadata.get("status", "unknown") if metadata else "not_found"

            return {
                "status": status,
                "total_chunks": 0,
                "processed_chunks": 0,
                "progress_percent": 0.0,
                "estimated_completion": None,
            }
        except Exception as e:
            logger.error(
                "GET_TASK_PROGRESS_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            raise FileNotFoundError(f"Task not found: {session_id}/{task_type}") from e
