"""Patient repository interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from backend.domain.patient import Patient


class IPatientRepository(ABC):
    """Patient repository interface."""

    @abstractmethod
    def create(self, patient: "Patient") -> str:
        """Create a new patient."""
        ...

    @abstractmethod
    def get(self, patient_id: str) -> Optional["Patient"]:
        """Get patient by ID."""
        ...

    @abstractmethod
    def search(self, query: str) -> list["Patient"]:
        """Search patients by name or ID."""
        ...

    @abstractmethod
    def update(self, patient: "Patient") -> None:
        """Update existing patient."""
        ...
