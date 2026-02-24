"""Base protocol for medication category providers.

Each category module implements ``get_entries`` to supply its
``MedicationCatalogEntry`` instances.  The registry discovers and
aggregates them automatically, satisfying the Open/Closed Principle —
new categories are added by creating a new module without touching
existing files.

Author: Bernard Uriza Orozco
Card: FI-RX-004
"""

from __future__ import annotations

from typing import Protocol

from backend.domain.prescription.models.catalog import MedicationCatalogEntry


class CategoryProvider(Protocol):
    """Contract every category module must satisfy."""

    @staticmethod
    def get_entries() -> list[MedicationCatalogEntry]:
        """Return all catalog entries for this therapeutic category."""
        ...
