"""SOAP Note repository interface - domain contract.

Author: Claude Code
Created: 2026-01-28
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from backend.domain.soap.entity import SOAPNote, SOAPStatus


class ISOAPRepository(ABC):
    """Interface for SOAP note persistence operations."""

    @abstractmethod
    def save(self, soap: SOAPNote) -> str:
        """Persist SOAP note entity."""
        pass

    @abstractmethod
    def find_by_id(self, soap_id: str) -> SOAPNote | None:
        """Find SOAP note by ID."""
        pass

    @abstractmethod
    def find_by_session(self, session_id: str) -> List[SOAPNote]:
        """Find all SOAP notes for a session."""
        pass

    @abstractmethod
    def find_by_status(self, status: SOAPStatus) -> List[SOAPNote]:
        """Find SOAP notes by status."""
        pass

    @abstractmethod
    def update(self, soap: SOAPNote) -> bool:
        """Update existing SOAP note."""
        pass

    @abstractmethod
    def delete(self, soap_id: str) -> bool:
        """Delete SOAP note by ID."""
        pass

    @abstractmethod
    def exists(self, soap_id: str) -> bool:
        """Check if SOAP note exists."""
        pass
