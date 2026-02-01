"""Medication Catalog Service.

Provides search, autocomplete, and filtering capabilities
for the medication database.

Author: Bernard Uriza Orozco
Created: 2025-12-28
Updated: 2026-02-01 (Phase 2.3 Marte - SOLID refactor with DI)
Card: FI-RX-004
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.domain.prescription.interfaces.icatalog_repository import ICatalogRepository

from backend.domain.prescription.interfaces.icatalog_service import ICatalogService
from backend.domain.prescription.models.catalog import (
    ControlledSubstanceLevel,
    DrugCategory,
    MedicationCatalogEntry,
)
from pydantic import BaseModel, Field


class CatalogSearchResult(BaseModel):
    """Result from catalog search with relevance score."""

    medication: MedicationCatalogEntry
    score: int = Field(description="Relevance score (higher = more relevant)")
    match_type: str = Field(description="Type of match: exact, starts_with, contains, commercial")


class CatalogSearchRequest(BaseModel):
    """Request parameters for catalog search."""

    query: str = Field(min_length=1, max_length=100, description="Search query")
    category: DrugCategory | None = Field(
        default=None, description="Filter by therapeutic category"
    )
    controlled_only: bool = Field(default=False, description="Only return controlled substances")
    essential_only: bool = Field(
        default=False, description="Only return essential medications (cuadro básico)"
    )
    otc_only: bool = Field(default=False, description="Only return OTC medications")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")


class CatalogSearchResponse(BaseModel):
    """Response from catalog search."""

    results: list[CatalogSearchResult]
    total_matches: int
    query: str


class CatalogService(ICatalogService):
    """Service for medication catalog operations.

    Implements ICatalogService interface for dependency injection.
    Uses ICatalogRepository for data access (SOLID DIP).

    Phase 2.3 Marte: Refactored to receive repository via constructor.
    """

    _instance: "CatalogService | None" = None
    _repository: "ICatalogRepository | None" = None

    def __new__(cls, repository: "ICatalogRepository | None" = None) -> "CatalogService":
        """Singleton pattern for catalog service.

        Args:
            repository: Optional repository for DI. If None on first call,
                       uses InMemoryCatalogRepository (backwards compatible).
        """
        if cls._instance is None:
            instance = super().__new__(cls)
            # Initialize repository on first instantiation
            if repository is not None:
                instance._repository = repository
            else:
                # Backwards compatibility: use default repository
                from backend.domain.prescription.repositories import InMemoryCatalogRepository
                instance._repository = InMemoryCatalogRepository()
            cls._instance = instance
        return cls._instance

    @property
    def catalog(self) -> list[MedicationCatalogEntry]:
        """Get the full catalog (via repository)."""
        if self._repository is None:
            return []
        return self._repository.get_all()

    def search(self, request: CatalogSearchRequest) -> CatalogSearchResponse:
        """Search the catalog with scoring and filtering.

        Args:
            request: Search parameters

        Returns:
            Sorted search results with relevance scores
        """
        query = request.query.lower().strip()
        results: list[CatalogSearchResult] = []

        for med in self.catalog:
            # Skip inactive medications
            if not med.is_active:
                continue

            # Apply filters
            if request.category and med.category != request.category:
                continue
            if request.controlled_only and med.controlled_level == ControlledSubstanceLevel.NONE:
                continue
            if request.essential_only and not med.is_essential:
                continue
            if request.otc_only and med.requires_prescription:
                continue

            # Check if matches
            if not med.matches_search(query):
                continue

            # Calculate score and match type
            score = med.get_search_score(query)
            match_type = self._determine_match_type(med, query)

            results.append(
                CatalogSearchResult(
                    medication=med,
                    score=score,
                    match_type=match_type,
                )
            )

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        # Apply limit
        total_matches = len(results)
        results = results[: request.limit]

        return CatalogSearchResponse(
            results=results,
            total_matches=total_matches,
            query=request.query,
        )

    def _determine_match_type(self, med: MedicationCatalogEntry, query: str) -> str:
        """Determine the type of match for a medication.

        Args:
            med: Medication entry
            query: Lowercase search query

        Returns:
            Match type string
        """
        # Check exact match on generic name
        if query == med.generic_name.lower():
            return "exact"

        # Check starts with on generic name
        if med.generic_name.lower().startswith(query):
            return "starts_with"

        # Check commercial name matches
        for name in med.commercial_names:
            if query == name.lower():
                return "commercial_exact"
            if name.lower().startswith(query):
                return "commercial_starts_with"

        # Default to contains
        return "contains"

    def autocomplete(
        self,
        prefix: str,
        limit: int = 5,
        category: DrugCategory | None = None,
    ) -> list[str]:
        """Get autocomplete suggestions for medication names.

        Args:
            prefix: Text prefix to match
            limit: Maximum suggestions
            category: Optional category filter

        Returns:
            List of medication name suggestions
        """
        if len(prefix) < 2:
            return []

        prefix_lower = prefix.lower()
        suggestions: list[tuple[str, int]] = []  # (name, priority)

        for med in self.catalog:
            if not med.is_active:
                continue

            if category and med.category != category:
                continue

            # Check generic name
            if med.generic_name.lower().startswith(prefix_lower):
                # Priority: 3 for generic name starting with prefix
                suggestions.append((med.generic_name, 3))

            # Check commercial names
            for name in med.commercial_names:
                if name.lower().startswith(prefix_lower):
                    # Priority: 2 for commercial name
                    suggestions.append((name, 2))

        # Sort by priority then alphabetically
        suggestions.sort(key=lambda x: (-x[1], x[0].lower()))

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for name, _ in suggestions:
            name_lower = name.lower()
            if name_lower not in seen:
                seen.add(name_lower)
                unique.append(name)
                if len(unique) >= limit:
                    break

        return unique

    def get_by_id(self, medication_id: str) -> MedicationCatalogEntry | None:
        """Get a medication by its ID.

        Args:
            medication_id: Unique medication identifier

        Returns:
            Medication entry or None if not found
        """
        for med in self.catalog:
            if med.id == medication_id:
                return med
        return None

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
        results = [med for med in self.catalog if med.is_active and med.category == category]
        return results[:limit]

    def get_essential_medications(self, limit: int = 100) -> list[MedicationCatalogEntry]:
        """Get essential medications (cuadro básico).

        Args:
            limit: Maximum results

        Returns:
            List of essential medications
        """
        results = [med for med in self.catalog if med.is_active and med.is_essential]
        return results[:limit]

    def get_otc_medications(self, limit: int = 50) -> list[MedicationCatalogEntry]:
        """Get over-the-counter medications.

        Args:
            limit: Maximum results

        Returns:
            List of OTC medications
        """
        results = [med for med in self.catalog if med.is_active and not med.requires_prescription]
        return results[:limit]

    def get_controlled_medications(self, limit: int = 50) -> list[MedicationCatalogEntry]:
        """Get controlled substance medications.

        Args:
            limit: Maximum results

        Returns:
            List of controlled medications
        """
        results = [
            med
            for med in self.catalog
            if med.is_active and med.controlled_level != ControlledSubstanceLevel.NONE
        ]
        return results[:limit]

    def get_categories(self) -> list[dict[str, str]]:
        """Get all available drug categories.

        Returns:
            List of category info dicts with value and label
        """
        return [
            {"value": cat.value, "label": cat.name.replace("_", " ").title()}
            for cat in DrugCategory
        ]

    def get_catalog_stats(self) -> dict:
        """Get statistics about the medication catalog.

        Returns:
            Dict with catalog statistics
        """
        active = [m for m in self.catalog if m.is_active]
        return {
            "total_medications": len(self.catalog),
            "active_medications": len(active),
            "essential_medications": sum(1 for m in active if m.is_essential),
            "otc_medications": sum(1 for m in active if not m.requires_prescription),
            "controlled_medications": sum(
                1 for m in active if m.controlled_level != ControlledSubstanceLevel.NONE
            ),
            "categories_used": len({m.category for m in active}),
        }


# Singleton instance (DEPRECATED - Phase 2.3 Marte)
# For new code, use DI via get_catalog_service_dep() from dependencies.py
catalog_service = CatalogService()
