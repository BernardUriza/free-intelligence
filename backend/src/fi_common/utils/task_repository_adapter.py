"""Adapter that wraps functional task_repository module to implement ITaskRepository interface."""

from typing import Any, Dict, List, Optional

from backend.src.fi_common.interfaces.itask_repository import ITaskRepository
from backend.src.fi_storage.infrastructure.hdf5 import task_repository as tr


class TaskRepositoryAdapter(ITaskRepository):
    """Adapter that delegates to functional task_repository module."""

    def __init__(self, h5_file_path: str | None = None):
        """Initialize adapter.

        Args:
            h5_file_path: Not used (functional module uses global CORPUS_PATH)
        """
        # The functional module uses CORPUS_PATH internally, so we don't need to store h5_file_path
        pass

    def get_task_metadata(self, session_id: str, task_type: str) -> Optional[Dict[str, Any]]:
        """Get task metadata."""
        return tr.get_task_metadata(session_id, task_type)

    def task_exists(self, session_id: str, task_type: str) -> bool:
        """Check if task exists."""
        return tr.task_exists(session_id, task_type)

    def ensure_task_exists(
        self, session_id: str, task_type: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Ensure task exists, create if not."""
        return tr.ensure_task_exists(session_id, task_type, metadata or {})

    def get_task_chunks(self, session_id: str, task_type: str) -> List[Dict[str, Any]]:
        """Get task chunks."""
        return tr.get_task_chunks(session_id, task_type)

    def save_task_metadata(self, session_id: str, task_type: str, metadata: Dict[str, Any]) -> None:
        """Save task metadata."""
        tr.update_task_metadata(session_id, task_type, **metadata)
