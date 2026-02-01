"""In-Memory Catalog Repository.

Implements ICatalogRepository using the pre-loaded Mexico medication catalog.
This is the default implementation for the medication catalog.

Pattern: Repository Pattern
Card: Backend Refactor Phase 2.3 - Marte (SOLID Medication Catalog)
"""

from __future__ import annotations

from backend.domain.prescription.data.mexico_catalog import MEXICO_MEDICATION_CATALOG
from backend.domain.prescription.interfaces.icatalog_repository import ICatalogRepository
from backend.domain.prescription.models.catalog import (
    DrugCategory,
    MedicationCatalogEntry,
)


class InMemoryCatalogRepository(ICatalogRepository):
    """In-memory implementation of medication catalog repository.

    Uses the pre-loaded MEXICO_MEDICATION_CATALOG as the data source.
    Suitable for read-only operations with static catalog data.
    """

    def __init__(self, catalog: list[MedicationCatalogEntry] | None = None) -> None:
        """Initialize repository with optional custom catalog.

        Args:
            catalog: Optional custom catalog for testing.
                    Defaults to MEXICO_MEDICATION_CATALOG.
        """
        self._catalog = catalog if catalog is not None else MEXICO_MEDICATION_CATALOG

    def get_all(self) -> list[MedicationCatalogEntry]:
        """Get all medication entries from the catalog."""
        return self._catalog

    def get_by_id(self, medication_id: str) -> MedicationCatalogEntry | None:
        """Get a medication by its unique ID."""
        for med in self._catalog:
            if med.id == medication_id:
                return med
        return None

    def get_by_category(
        self, category: DrugCategory, limit: int = 50
    ) -> list[MedicationCatalogEntry]:
        """Get medications by therapeutic category."""
        results = [
            med for med in self._catalog
            if med.is_active and med.category == category
        ]
        return results[:limit]

    def get_active(self) -> list[MedicationCatalogEntry]:
        """Get only active medications."""
        return [med for med in self._catalog if med.is_active]

    def count(self) -> int:
        """Get total count of medications in catalog."""
        return len(self._catalog)
