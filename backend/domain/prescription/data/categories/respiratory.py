"""Respiratory / Bronchodilators — Mexico Medication Catalog.

Bronchodilators and respiratory agents from the Cuadro Básico / COFEPRIS.

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
    """Return respiratory / bronchodilator catalog entries."""
    return [
        _salbutamol(),
    ]


# -- private builders --------------------------------------------------------


def _salbutamol() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="salbutamol",
        generic_name="Salbutamol",
        active_ingredient="Salbutamol sulfato",
        commercial_names=["Ventolin", "Aeroflux", "Assal"],
        category=DrugCategory.BRONCHODILATOR,
        presentations=[
            Presentation(
                form="inhalador",
                strength="100mcg/dosis",
                route=MedicationRoute.INHALATION,
                package_size="200 dosis",
            ),
            Presentation(
                form="solución nebulizar",
                strength="5mg/ml",
                route=MedicationRoute.INHALATION,
            ),
            Presentation(form="jarabe", strength="2mg/5ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="2 inhalaciones cada 4-6 horas PRN",
            pediatric_dose="1-2 inhalaciones cada 4-6 horas PRN",
            notes="Uso de rescate, no preventivo",
        ),
        contraindications=["Hipersensibilidad"],
        warnings=["Taquicardia", "Temblor", "Hipokalemia con uso excesivo"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )
