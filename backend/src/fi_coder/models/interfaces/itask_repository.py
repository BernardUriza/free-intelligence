"""Task repository interface for dependency injection."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ITaskRepository(ABC):
    """Abstract interface for task repository operations."""

    @abstractmethod
    def get_task_metadata(self, session_id: str, task_type: str) -> Optional[Dict[str, Any]]:
        """Get task metadata."""
        pass

    @abstractmethod
    def task_exists(self, session_id: str, task_type: str) -> bool:
        """Check if task exists."""
        pass