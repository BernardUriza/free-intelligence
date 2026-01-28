"""Patient Repository Interface - Domain Layer.

Pure domain interface with ZERO infrastructure dependencies.
Defines contract for patient persistence without specifying implementation.

Author: Claude Code
Created: 2026-01-28
Card: Backend Refactor Phase 2.4 - Domain Layer (Interfaces)
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List


class IPatientRepository(ABC):
    """Patient repository interface.

    Defines contract for patient persistence operations.
    Implementations can use PostgreSQL, HDF5, or any other storage.

    Note: Current implementation uses SQLAlchemy ORM models.
    Future: Extract pure Patient entity and map in repository implementation.
    """

    @abstractmethod
    def create(
        self,
        nombre: str,
        apellido: str,
        fecha_nacimiento: datetime,
        genero: str | None = None,
        curp: str | None = None,
    ) -> str:
        """Create a new patient.

        Args:
            nombre: First name(s)
            apellido: Last name(s)
            fecha_nacimiento: Date of birth
            genero: Gender (optional)
            curp: CURP Mexican ID (optional)

        Returns:
            patient_id: UUID of created patient

        Raises:
            ValueError: If CURP already exists
        """
        pass

    @abstractmethod
    def get_by_id(self, patient_id: str) -> dict | None:
        """Get patient by ID.

        Args:
            patient_id: Patient UUID

        Returns:
            Patient data dict or None if not found
        """
        pass

    @abstractmethod
    def get_by_curp(self, curp: str) -> dict | None:
        """Get patient by CURP.

        Args:
            curp: CURP (18 characters)

        Returns:
            Patient data dict or None if not found
        """
        pass

    @abstractmethod
    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> List[dict]:
        """List patients with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            search: Optional search term (nombre/apellido/CURP)

        Returns:
            List of patient data dicts
        """
        pass

    @abstractmethod
    def update(
        self,
        patient_id: str,
        nombre: str | None = None,
        apellido: str | None = None,
        fecha_nacimiento: datetime | None = None,
        genero: str | None = None,
        curp: str | None = None,
    ) -> bool:
        """Update patient data.

        Args:
            patient_id: Patient UUID
            nombre: New first name (optional)
            apellido: New last name (optional)
            fecha_nacimiento: New birth date (optional)
            genero: New gender (optional)
            curp: New CURP (optional)

        Returns:
            True if updated, False if patient not found

        Raises:
            ValueError: If CURP already exists for another patient
        """
        pass

    @abstractmethod
    def delete(self, patient_id: str) -> bool:
        """Delete patient (soft or hard delete depending on implementation).

        Args:
            patient_id: Patient UUID

        Returns:
            True if deleted, False if patient not found
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
    def curp_exists(self, curp: str, exclude_patient_id: str | None = None) -> bool:
        """Check if CURP already exists.

        Args:
            curp: CURP to check
            exclude_patient_id: Optional patient ID to exclude (for updates)

        Returns:
            True if CURP exists for another patient
        """
        pass
