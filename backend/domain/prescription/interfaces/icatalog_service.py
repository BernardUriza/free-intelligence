"""Interface for Medication Catalog Service.

Defines the contract for medication catalog operations.
Enables dependency injection and testability.

Pattern: Dependency Inversion Principle (DIP)
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
    from backend.domain.prescription.services.catalog_service import (
        CatalogSearchRequest,
        CatalogSearchResponse,
    )


class ICatalogService(ABC):
    """Abstract interface for medication catalog service.

    This interface defines the contract for catalog operations.
    Routers and other services depend on this interface.

    Key responsibilities:
    - Search medications with scoring
    - Autocomplete suggestions
    - Filter by various criteria (essential, OTC, controlled)
    - Catalog statistics
    """

    @abstractmethod
    def search(self, request: CatalogSearchRequest) -> CatalogSearchResponse:
        """Search the catalog with scoring and filtering.

        Args:
            request: Search parameters including query, filters, and limit

        Returns:
            Sorted search results with relevance scores
        """
        pass

    @abstractmethod
    def autocomplete(
        self,
        prefix: str,
        limit: int = 5,
        category: DrugCategory | None = None,
    ) -> list[str]:
        """Get autocomplete suggestions for medication names.

        Args:
            prefix: Text prefix to match (min 2 chars)
            limit: Maximum suggestions
            category: Optional category filter

        Returns:
            List of medication name suggestions
        """
        pass

    @abstractmethod
    def get_by_id(self, medication_id: str) -> MedicationCatalogEntry | None:
        """Get a medication by its ID.

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
            category: Drug category
            limit: Maximum results

        Returns:
            List of medications in the category
        """
        pass

    @abstractmethod
    def get_essential_medications(self, limit: int = 100) -> list[MedicationCatalogEntry]:
        """Get essential medications (cuadro básico).

        Args:
            limit: Maximum results

        Returns:
            List of essential medications
        """
        pass

    @abstractmethod
    def get_otc_medications(self, limit: int = 50) -> list[MedicationCatalogEntry]:
        """Get over-the-counter medications.

        Args:
            limit: Maximum results

        Returns:
            List of OTC medications
        """
        pass

    @abstractmethod
    def get_controlled_medications(self, limit: int = 50) -> list[MedicationCatalogEntry]:
        """Get controlled substance medications.

        Args:
            limit: Maximum results

        Returns:
            List of controlled medications
        """
        pass

    @abstractmethod
    def get_categories(self) -> list[dict[str, str]]:
        """Get all available drug categories.

        Returns:
            List of category info dicts with value and label
        """
        pass

    @abstractmethod
    def get_catalog_stats(self) -> dict:
        """Get statistics about the medication catalog.

        Returns:
            Dict with catalog statistics
        """
        pass
