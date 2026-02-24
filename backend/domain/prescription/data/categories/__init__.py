"""Therapeutic-category modules for the Mexico medication catalog.

Each sub-module defines medications for one therapeutic category and
exposes a ``get_entries() -> list[MedicationCatalogEntry]`` function.

To add a new category:
    1. Create ``categories/<category_name>.py``
    2. Implement ``get_entries()``
    3. Import the module here and add it to ``CATEGORY_MODULES``

Author: Bernard Uriza Orozco
Card: FI-RX-004
"""

from __future__ import annotations

from backend.domain.prescription.data.categories import (
    analgesics,
    antibiotics,
    antidepressants,
    antidiabetics,
    antihistamines,
    antihypertensives,
    antiinflammatories,
    anxiolytics,
    corticosteroids,
    gastrointestinal,
    muscle_relaxants,
    respiratory,
    vitamins,
)

# Ordered list of all category provider modules.
# Adding a new module here is the *only* change needed to extend the
# catalog with a new therapeutic category (Open/Closed Principle).
CATEGORY_MODULES = [
    analgesics,
    antiinflammatories,
    antibiotics,
    antihypertensives,
    antidiabetics,
    gastrointestinal,
    antihistamines,
    corticosteroids,
    respiratory,
    muscle_relaxants,
    anxiolytics,
    antidepressants,
    vitamins,
]

__all__ = [
    "CATEGORY_MODULES",
    "analgesics",
    "antibiotics",
    "antidepressants",
    "antidiabetics",
    "antihistamines",
    "antihypertensives",
    "antiinflammatories",
    "anxiolytics",
    "corticosteroids",
    "gastrointestinal",
    "muscle_relaxants",
    "respiratory",
    "vitamins",
]
