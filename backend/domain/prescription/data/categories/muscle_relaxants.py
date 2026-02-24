"""Muscle Relaxants — Mexico Medication Catalog.

Skeletal muscle relaxants from the Cuadro Básico / COFEPRIS.

Author: Bernard Uriza Orozco
Card: FI-RX-004
"""

from __future__ import annotations

from backend.domain.prescription.models.catalog import (
    ControlledSubstanceLevel,
    DrugCategory,
    MedicationCatalogEntry,
    Presentation,
    StandardDosing,
)
from backend.domain.prescription.models.medication import MedicationRoute


def get_entries() -> list[MedicationCatalogEntry]:
    """Return muscle relaxant catalog entries."""
    return [
        _ciclobenzaprina(),
    ]


# -- private builders --------------------------------------------------------


def _ciclobenzaprina() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="ciclobenzaprina",
        generic_name="Ciclobenzaprina",
        active_ingredient="Ciclobenzaprina clorhidrato",
        commercial_names=["Yurelax", "Flexeril"],
        category=DrugCategory.MUSCLE_RELAXANT,
        presentations=[
            Presentation(form="tableta", strength="10mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="10mg cada 8 horas",
            max_daily_dose="30mg/día",
            duration_typical="2-3 semanas máximo",
        ),
        contraindications=["Arritmias", "ICC", "Hipertiroidismo", "Uso con IMAO"],
        warnings=["Somnolencia", "Boca seca", "No usar >3 semanas"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=False,
    )
