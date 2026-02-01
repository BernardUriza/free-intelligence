"""SOAP Note repository interface."""

from abc import ABC, abstractmethod
from typing import Optional

# Forward reference to avoid circular imports
if False:
    from backend.domain.soap import SOAPNote


class ISOAPRepository(ABC):
    """SOAP Note repository interface."""

    @abstractmethod
    def create(self, soap_note: "SOAPNote") -> str:
        """Create a new SOAP note."""
        ...

    @abstractmethod
    def get(self, note_id: str) -> Optional["SOAPNote"]:
        """Get SOAP note by ID."""
        ...

    @abstractmethod
    def list_by_session(self, session_id: str) -> list["SOAPNote"]:
        """List SOAP notes for a session."""
        ...

    @abstractmethod
    def update(self, soap_note: "SOAPNote") -> None:
        """Update existing SOAP note."""
        ...
