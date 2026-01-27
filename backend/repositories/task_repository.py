"""Task Repository - HDF5-based task management.

Handles task lifecycle:
- Task creation and metadata storage
- Task chunks management
- Task status tracking

Clean Architecture:
- Implements ITaskRepository interface
- Isolated from business logic
- HDF5 as implementation detail
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import h5py
from backend.utils.common.interfaces.itask_repository import ITaskRepository
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class HDF5TaskRepository(ITaskRepository):
    """HDF5-based implementation of ITaskRepository.

    Storage structure:
        /tasks/{session_id}/{task_type}/
            metadata (attrs): Task metadata as HDF5 attributes
            chunks/ (group): Optional chunks storage
    """

    TASKS_GROUP = "tasks"

    def __init__(self, h5_file_path: str | Path):
        """Initialize task repository.

        Args:
            h5_file_path: Path to HDF5 database file
        """
        self.h5_file_path = Path(h5_file_path)
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Ensure required HDF5 structure exists."""
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                f.require_group(self.TASKS_GROUP)
            logger.info("TASK_REPOSITORY_STRUCTURE_READY", file_path=str(self.h5_file_path))
        except OSError as e:
            logger.error("TASK_REPOSITORY_STRUCTURE_INIT_FAILED", error=str(e))
            raise

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
                task_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}"
                if task_path not in f:
                    return None

                task_group = f[task_path]
                metadata = dict(task_group.attrs)

                # Deserialize JSON values
                return {
                    key: self._deserialize_value(val) for key, val in metadata.items()
                }

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
                task_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}"
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
        """Ensure task exists, create if not.

        Args:
            session_id: Session identifier
            task_type: Task type
            metadata: Optional initial metadata

        Returns:
            Task identifier (f"{session_id}/{task_type}")
        """
        try:
            with h5py.File(self.h5_file_path, "a") as f:
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)
                task_group = session_group.require_group(task_type)

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

    def get_task_chunks(self, session_id: str, task_type: str) -> list[dict[str, Any]]:
        """Get task chunks.

        Args:
            session_id: Session identifier
            task_type: Task type

        Returns:
            List of chunk dicts (empty list if no chunks)
        """
        try:
            with h5py.File(self.h5_file_path, "r") as f:
                chunks_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}/chunks"
                if chunks_path not in f:
                    return []

                chunks_group = f[chunks_path]
                chunks = []

                for chunk_id in chunks_group.keys():
                    chunk_attrs = dict(chunks_group[chunk_id].attrs)
                    chunk_data = {
                        "id": chunk_id,
                        **{key: self._deserialize_value(val) for key, val in chunk_attrs.items()},
                    }
                    chunks.append(chunk_data)

                return chunks

        except Exception as e:
            logger.error(
                "GET_TASK_CHUNKS_FAILED",
                session_id=session_id,
                task_type=task_type,
                error=str(e),
            )
            return []

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
                task_path = f"{self.TASKS_GROUP}/{session_id}/{task_type}"

                # Ensure task exists
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)
                task_group = session_group.require_group(task_type)

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

    @staticmethod
    def _serialize_value(value: Any) -> str | int | float | bool:
        """Serialize Python value to HDF5-compatible type."""
        if isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, (list, dict)) or value is None:
            return json.dumps(value)
        else:
            return str(value)

    @staticmethod
    def _deserialize_value(value: Any) -> Any:
        """Deserialize HDF5 attr value to Python type."""
        if not isinstance(value, (str, bytes)):
            return value

        if isinstance(value, bytes):
            value = value.decode("utf-8")

        if isinstance(value, str):
            if value.startswith(("{", "[")):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            elif value == "null":
                return None

        return value
