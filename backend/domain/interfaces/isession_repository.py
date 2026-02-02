"""Session repository interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from backend.domain.session import Session


class ISessionRepository(ABC):
    """Session repository interface."""

    @abstractmethod
    def create(self, session: "Session") -> str:
        """Create a new session."""
        ...

    @abstractmethod
    def get(self, session_id: str) -> Optional["Session"]:
        """Get session by ID."""
        ...

    @abstractmethod
    def list_by_patient(self, patient_id: str) -> list["Session"]:
        """List sessions for a patient."""
        ...

    @abstractmethod
    def update(self, session: "Session") -> None:
        """Update existing session."""
        ...
