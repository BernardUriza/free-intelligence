"""Patient repository interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.domain.patient import Patient


class IPatientRepository(ABC):
    """Patient repository interface."""

    @abstractmethod
    def create(self, patient: Patient) -> str:
        """Create a new patient."""
        ...

    @abstractmethod
    def get(self, patient_id: str) -> Patient | None:
        """Get patient by ID."""
        ...

    @abstractmethod
    def search(self, query: str) -> list[Patient]:
        """Search patients by name or ID."""
        ...

    @abstractmethod
    def update(self, patient: Patient) -> None:
        """Update existing patient."""
        ...
