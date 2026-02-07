"""Adapter that wraps HDF5TaskRepository to implement ITaskRepository interface.

NOTE: This adapter now delegates to the real HDF5TaskRepository implementation
instead of the broken infrastructure.storage.infrastructure.hdf5.task_repository
"""

from pathlib import Path
from typing import Any

from backend.repositories.task import HDF5TaskRepository
from backend.repositories.interfaces.itask_repository import ITaskRepository


class TaskRepositoryAdapter(ITaskRepository):
    """Adapter that delegates to HDF5TaskRepository.

    Provides backward compatibility for code expecting TaskRepositoryAdapter.
    """

    def __init__(self, h5_file_path: str | Path | None = None):
        """Initialize adapter with HDF5 file path.

        Args:
            h5_file_path: Path to HDF5 database file (defaults to storage/corpus.h5)
        """
        if h5_file_path is None:
            h5_file_path = Path("storage/corpus.h5")

        self._repository = HDF5TaskRepository(h5_file_path)

    def get_task_metadata(self, session_id: str, task_type: str) -> dict[str, Any] | None:
        """Get task metadata."""
        return self._repository.get_task_metadata(session_id, task_type)

    def task_exists(self, session_id: str, task_type: str) -> bool:
        """Check if task exists."""
        return self._repository.task_exists(session_id, task_type)

    def ensure_task_exists(
        self, session_id: str, task_type: str, metadata: dict[str, Any] | None = None
    ) -> str:
        """Ensure task exists, create if not."""
        return self._repository.ensure_task_exists(session_id, task_type, metadata)

    def get_task_chunks(self, session_id: str, task_type: str) -> list[dict[str, Any]]:
        """Get task chunks."""
        return self._repository.get_task_chunks(session_id, task_type)

    def save_task_metadata(self, session_id: str, task_type: str, metadata: dict[str, Any]) -> None:
        """Save task metadata."""
        self._repository.save_task_metadata(session_id, task_type, metadata)

    def batch_update_chunk_datasets(
        self,
        session_id: str,
        task_type: str,
        chunk_idx: int,
        updates: dict[str, Any],
    ) -> None:
        """Batch update chunk datasets."""
        self._repository.batch_update_chunk_datasets(session_id, task_type, chunk_idx, updates)

    def delete_task(self, session_id: str, task_type: str) -> bool:
        """Delete task and all chunks."""
        return self._repository.delete_task(session_id, task_type)

    def get_task_progress(self, session_id: str, task_type: str) -> dict[str, Any]:
        """Get task progress summary."""
        return self._repository.get_task_progress(session_id, task_type)

    def get_soap_data(self, session_id: str) -> dict[str, Any] | None:
        """Get SOAP note data for session."""
        return self._repository.get_soap_data(session_id)

    def get_diarization_segments(self, session_id: str) -> list[dict[str, Any]]:
        """Get diarization segments for session."""
        return self._repository.get_diarization_segments(session_id)

    def save_soap_data(
        self, session_id: str, soap_data: dict[str, Any], task_type: str = "SOAP_GENERATION"
    ) -> None:
        """Save SOAP note data for session."""
        self._repository.save_soap_data(session_id, soap_data, task_type)
