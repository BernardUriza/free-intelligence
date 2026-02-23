"""Medication catalog data for Mexico.

Public API
----------
``MEXICO_MEDICATION_CATALOG``
    Flat list of all ``MedicationCatalogEntry`` items (backward-compatible).
``CatalogRegistry``
    Registry class for programmatic category management.

Extending the catalog
---------------------
1. Create ``categories/<new_category>.py`` with ``get_entries()``.
2. Import in ``categories/__init__.py`` and add to ``CATEGORY_MODULES``.
"""

from __future__ import annotations

from backend.domain.prescription.data._registry import CatalogRegistry
from backend.domain.prescription.data.mexico_catalog import MEXICO_MEDICATION_CATALOG

__all__ = [
    "CatalogRegistry",
    "MEXICO_MEDICATION_CATALOG",
]
