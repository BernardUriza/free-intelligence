from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol


class SessionRepository(ABC):
    """Contract for session persistence."""

    @abstractmethod
    def upsert(self, session: Any) -> None:  # narrow types in implementations
        raise NotImplementedError

    @abstractmethod
    def get(self, session_id: str) -> Any | None:
        raise NotImplementedError


class TaskRepository(Protocol):
    """Lightweight protocol for task persistence (HDF5 or SQL)."""

    def append_chunk(self, session_id: str, task_type: str, chunk: Any) -> None: ...

    def update_metadata(self, session_id: str, task_type: str, metadata: dict[str, Any]) -> None: ...


__all__ = ["SessionRepository", "TaskRepository"]
