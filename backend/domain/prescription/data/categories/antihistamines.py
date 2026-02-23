"""Antihistamines — Mexico Medication Catalog.

Second-generation antihistamines from the Cuadro Básico / COFEPRIS.

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
    """Return antihistamine catalog entries."""
    return [
        _loratadina(),
        _cetirizina(),
    ]


# -- private builders --------------------------------------------------------


def _loratadina() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="loratadina",
        generic_name="Loratadina",
        active_ingredient="Loratadina",
        commercial_names=["Clarityne", "Sensibit", "Alercet"],
        category=DrugCategory.ANTIHISTAMINE,
        presentations=[
            Presentation(form="tableta", strength="10mg", route=MedicationRoute.ORAL),
            Presentation(form="jarabe", strength="5mg/5ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="10mg cada 24 horas",
            pediatric_dose="5mg cada 24 horas (2-5 años), 10mg (>6 años)",
            duration_typical="Según síntomas o uso crónico en rinitis",
        ),
        contraindications=["Hipersensibilidad"],
        warnings=["No sedante pero puede causar somnolencia en algunos pacientes"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    )


def _cetirizina() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="cetirizina",
        generic_name="Cetirizina",
        active_ingredient="Cetirizina diclorhidrato",
        commercial_names=["Zyrtec", "Virlix", "Alerfast"],
        category=DrugCategory.ANTIHISTAMINE,
        presentations=[
            Presentation(form="tableta", strength="10mg", route=MedicationRoute.ORAL),
            Presentation(form="gotas", strength="10mg/ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="10mg cada 24 horas",
            pediatric_dose="2.5mg cada 12h (2-5 años), 5-10mg (>6 años)",
        ),
        contraindications=["Hipersensibilidad", "Insuficiencia renal severa"],
        warnings=["Puede causar somnolencia (más que loratadina)"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    )
