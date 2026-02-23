"""Antidepressants — Mexico Medication Catalog.

SSRIs and related antidepressants from the Cuadro Básico / COFEPRIS.

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
    """Return antidepressant catalog entries."""
    return [
        _sertralina(),
        _fluoxetina(),
    ]


# -- private builders --------------------------------------------------------


def _sertralina() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="sertralina",
        generic_name="Sertralina",
        active_ingredient="Sertralina clorhidrato",
        commercial_names=["Zoloft", "Altruline", "Serolux"],
        category=DrugCategory.ANTIDEPRESSANT,
        presentations=[
            Presentation(form="tableta", strength="50mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="100mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="50mg cada 24 horas, puede aumentar a 200mg",
            max_daily_dose="200mg/día",
            duration_typical="Mínimo 6-12 meses",
            notes="Efecto terapéutico completo en 4-6 semanas",
        ),
        contraindications=["Uso con IMAO (esperar 14 días)", "Pimozida"],
        interactions=[
            "IMAO",
            "Tramadol",
            "Triptanos (síndrome serotoninérgico)",
        ],
        warnings=[
            "Ideación suicida inicial en jóvenes",
            "No suspender abruptamente",
        ],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _fluoxetina() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="fluoxetina",
        generic_name="Fluoxetina",
        active_ingredient="Fluoxetina clorhidrato",
        commercial_names=["Prozac", "Fluoxac"],
        category=DrugCategory.ANTIDEPRESSANT,
        presentations=[
            Presentation(form="cápsula", strength="20mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="20mg cada 24 horas por la mañana",
            max_daily_dose="80mg/día",
            duration_typical="Mínimo 6-12 meses",
        ),
        contraindications=["Uso con IMAO"],
        warnings=[
            "Larga vida media (interacciones prolongadas)",
            "Ideación suicida en jóvenes",
        ],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )
