"""Interface for Medication Catalog Repository.

Abstracts the data source for medication catalog entries.
Enables swapping between different data sources (memory, database, API).

Pattern: Repository Pattern + Dependency Inversion Principle (DIP)
Card: Backend Refactor Phase 2.3 - Marte (SOLID Medication Catalog)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.domain.prescription.models.catalog import (
        DrugCategory,
        MedicationCatalogEntry,
    )


class ICatalogRepository(ABC):
    """Abstract interface for medication catalog data access.

    This interface defines the contract for accessing medication data.
    The service layer depends on this interface, not concrete implementations.

    Key responsibilities:
    - Provide access to medication catalog entries
    - Filter by category, controlled status, etc.
    - Get individual medications by ID

    Implementations:
    - InMemoryCatalogRepository: Uses MEXICO_MEDICATION_CATALOG
    - Future: DatabaseCatalogRepository, APICatalogRepository
    """

    @abstractmethod
    def get_all(self) -> list[MedicationCatalogEntry]:
        """Get all medication entries from the catalog.

        Returns:
            List of all medication catalog entries
        """
        pass

    @abstractmethod
    def get_by_id(self, medication_id: str) -> MedicationCatalogEntry | None:
        """Get a medication by its unique ID.

        Args:
            medication_id: Unique medication identifier

        Returns:
            Medication entry or None if not found
        """
        pass

    @abstractmethod
    def get_by_category(
        self, category: DrugCategory, limit: int = 50
    ) -> list[MedicationCatalogEntry]:
        """Get medications by therapeutic category.

        Args:
            category: Drug category to filter by
            limit: Maximum results

        Returns:
            List of medications in the category
        """
        pass

    @abstractmethod
    def get_active(self) -> list[MedicationCatalogEntry]:
        """Get only active medications.

        Returns:
            List of active medication entries
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Get total count of medications in catalog.

        Returns:
            Total number of medication entries
        """
        pass
