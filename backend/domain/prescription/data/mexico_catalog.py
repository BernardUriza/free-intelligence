"""Mexico Medication Catalog — Facade module.

Assembles all therapeutic-category sub-modules into the unified
``MEXICO_MEDICATION_CATALOG`` list that the rest of the codebase
imports.

**Extending the catalog:**
    1. Create ``categories/<new_category>.py`` with ``get_entries()``.
    2. Import the module in ``categories/__init__.py``.
    3. Append it to ``CATEGORY_MODULES``.

No changes to this file are required (Open/Closed Principle).

Based on:
    - Cuadro Básico y Catálogo de Medicamentos (IMSS/ISSSTE)
    - COFEPRIS registered medications
    - Common prescriptions in Mexican healthcare

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-004
"""

from __future__ import annotations

from backend.domain.prescription.data._registry import CatalogRegistry
from backend.domain.prescription.data.categories import CATEGORY_MODULES
from backend.domain.prescription.models.catalog import MedicationCatalogEntry

# -- build the catalog exactly once at import time ---------------------------

_registry = CatalogRegistry()
_registry.register_all(*CATEGORY_MODULES)

MEXICO_MEDICATION_CATALOG: list[MedicationCatalogEntry] = _registry.collect()

