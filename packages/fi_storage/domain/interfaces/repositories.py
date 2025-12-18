"""Repository interface definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ITaskRepository(ABC):
    """Interface for task persistence."""

    @abstractmethod
    def save_task(self, session_id: str, task_type: str, data: dict[str, Any]) -> str:
        """Save a task and return its ID."""
        ...

    @abstractmethod
    def get_task(self, session_id: str, task_id: str) -> dict[str, Any] | None:
        """Get a task by ID."""
        ...

    @abstractmethod
    def list_tasks(self, session_id: str, task_type: str | None = None) -> list[dict[str, Any]]:
        """List tasks for a session."""
        ...


class ISessionRepository(ABC):
    """Interface for session persistence."""

    @abstractmethod
    def create_session(self, session_id: str, metadata: dict[str, Any]) -> None:
        """Create a new session."""
        ...

    @abstractmethod
    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session by ID."""
        ...

    @abstractmethod
    def update_session(self, session_id: str, metadata: dict[str, Any]) -> None:
        """Update session metadata."""
        ...


class IAudioRepository(ABC):
    """Interface for audio storage."""

    @abstractmethod
    def save_audio(self, session_id: str, audio_data: bytes, chunk_index: int) -> str:
        """Save audio chunk and return path."""
        ...

    @abstractmethod
    def get_audio(self, session_id: str, chunk_index: int) -> bytes | None:
        """Get audio chunk."""
        ...
