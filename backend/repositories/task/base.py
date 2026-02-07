"""HDF5 Task Repository - Base class with serialization helpers.

Provides common HDF5 file operations and serialization methods.
All mixins inherit from this base.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor from monolithic task_repository.py)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import h5py

from backend.utils.common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.domain.session import ISessionRepository

logger = get_logger(__name__)


class HDF5Base:
    """Base class for HDF5 task repository mixins.

    Provides:
    - HDF5 file path management
    - Structure initialization
    - Value serialization/deserialization for HDF5 attrs
    - Session repository reference for referential integrity
    """

    TASKS_GROUP = "tasks"

    def __init__(
        self,
        h5_file_path: str | Path,
        session_repository: "ISessionRepository | None" = None,
    ):
        """Initialize base repository.

        Args:
            h5_file_path: Path to HDF5 database file
            session_repository: Optional session repository for referential integrity
        """
        self.h5_file_path = Path(h5_file_path)
        self.session_repository = session_repository
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

    @staticmethod
    def _serialize_value(value: Any) -> str | int | float | bool:
        """Serialize Python value to HDF5-compatible type.

        Args:
            value: Any Python value

        Returns:
            HDF5-compatible type (str, int, float, bool)
        """
        if isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, (list, dict)) or value is None:
            return json.dumps(value)
        else:
            return str(value)

    @staticmethod
    def _deserialize_value(value: Any) -> Any:
        """Deserialize HDF5 attr value to Python type.

        Args:
            value: HDF5 attribute value

        Returns:
            Deserialized Python value
        """
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

    def _get_task_path(self, session_id: str, task_type: str) -> str:
        """Build HDF5 path for a task.

        Args:
            session_id: Session identifier
            task_type: Task type

        Returns:
            HDF5 group path string
        """
        return f"{self.TASKS_GROUP}/{session_id}/{task_type}"

    def _ensure_task_group(self, f: h5py.File, session_id: str, task_type: str) -> h5py.Group:
        """Ensure task group exists and return it.

        Args:
            f: Open HDF5 file
            session_id: Session identifier
            task_type: Task type

        Returns:
            HDF5 group for the task
        """
        tasks_group = f.require_group(self.TASKS_GROUP)
        session_group = tasks_group.require_group(session_id)
        return session_group.require_group(task_type)

    def _save_json_dataset(
        self,
        f: h5py.File,
        group: h5py.Group,
        dataset_name: str,
        data: Any,
    ) -> None:
        """Save data as JSON-encoded HDF5 dataset.

        Args:
            f: Open HDF5 file
            group: HDF5 group to save to
            dataset_name: Name of the dataset
            data: Data to JSON-encode and save
        """
        # Delete existing dataset if present
        if dataset_name in group:
            del group[dataset_name]

        # Create new dataset
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        group.create_dataset(
            dataset_name,
            data=json_data.encode("utf-8"),
            dtype=h5py.special_dtype(vlen=bytes),
        )

    def _load_json_dataset(self, f: h5py.File, path: str) -> Any | None:
        """Load JSON-encoded HDF5 dataset.

        Args:
            f: Open HDF5 file
            path: Full path to dataset

        Returns:
            Decoded JSON data or None if not found
        """
        if path not in f:
            return None

        data = f[path][()]
        json_str = bytes(data).decode("utf-8")
        return json.loads(json_str)
