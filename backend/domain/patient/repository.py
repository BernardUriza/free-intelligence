"""Patient repository interface - domain contract.

Defines the contract for patient persistence operations.
Implementations can use PostgreSQL, MongoDB, HDF5, etc.

This interface is FRAMEWORK-AGNOSTIC - it belongs to the domain layer
and has ZERO dependencies on infrastructure (SQLAlchemy, FastAPI, etc).

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 3B Part 2 - Pure Domain Entities
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from backend.domain.patient.entity import Patient


class IPatientRepository(ABC):
    """Interface for patient persistence operations.

    Implementations:
    - PostgreSQLPatientRepository (current: SQLAlchemy)
    - InMemoryPatientRepository (for testing)
    - HDF5PatientRepository (future: if needed)
    """

    @abstractmethod
    def save(self, patient: Patient) -> str:
        """Persist patient entity.

        Args:
            patient: Patient entity to save

        Returns:
            patient_id of saved entity

        Raises:
            DuplicatePatientError: If CURP already exists
            RepositoryError: If persistence fails
        """
        pass

    @abstractmethod
    def find_by_id(self, patient_id: str) -> Patient | None:
        """Find patient by ID.

        Args:
            patient_id: Patient UUID

        Returns:
            Patient entity if found, None otherwise
        """
        pass

    @abstractmethod
    def find_by_curp(self, curp: str) -> Patient | None:
        """Find patient by CURP (Mexican national ID).

        Args:
            curp: 18-character CURP

        Returns:
            Patient entity if found, None otherwise
        """
        pass

    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> List[Patient]:
        """List all patients with pagination.

        Args:
            limit: Maximum number of patients to return
            offset: Number of patients to skip

        Returns:
            List of Patient entities
        """
        pass

    @abstractmethod
    def update(self, patient: Patient) -> bool:
        """Update existing patient.

        Args:
            patient: Patient entity with updated data

        Returns:
            True if update successful

        Raises:
            PatientNotFoundError: If patient_id doesn't exist
            RepositoryError: If update fails
        """
        pass

    @abstractmethod
    def delete(self, patient_id: str) -> bool:
        """Delete patient by ID.

        Args:
            patient_id: Patient UUID

        Returns:
            True if deletion successful

        Note:
            Actual behavior (soft delete vs hard delete) depends on implementation
        """
        pass

    @abstractmethod
    def exists(self, patient_id: str) -> bool:
        """Check if patient exists.

        Args:
            patient_id: Patient UUID

        Returns:
            True if patient exists
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Count total number of patients.

        Returns:
            Total patient count
        """
        pass
