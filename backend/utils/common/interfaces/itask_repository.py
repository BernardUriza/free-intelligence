from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ITaskRepository(ABC):
    """Abstract interface for task repository operations."""

    @abstractmethod
    def get_task_metadata(self, session_id: str, task_type: str) -> Dict[str, Any] | None:
        """Get task metadata."""
        pass

    @abstractmethod
    def task_exists(self, session_id: str, task_type: str) -> bool:
        """Check if task exists."""
        pass

    @abstractmethod
    def ensure_task_exists(
        self, session_id: str, task_type: str, metadata: Dict[str, Any] | None = None
    ) -> str:
        """Ensure task exists, create if not."""
        pass

    @abstractmethod
    def get_task_chunks(self, session_id: str, task_type: str) -> List[Dict[str, Any]]:
        """Get task chunks."""
        pass

    @abstractmethod
    def save_task_metadata(self, session_id: str, task_type: str, metadata: Dict[str, Any]) -> None:
        """Save task metadata."""
        pass

    @abstractmethod
    def delete_by_session(self, session_id: str) -> int:
        """Delete all tasks for a session (Fix #5 - cascade delete).

        Args:
            session_id: Session identifier

        Returns:
            Number of tasks deleted

        Purpose:
            Enables cascade delete when session is removed.
            Prevents orphaned tasks with invalid session_id references.
        """
        pass
