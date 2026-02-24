"""Antidiabetics — Mexico Medication Catalog.

Oral hypoglycaemics from the Cuadro Básico / COFEPRIS.

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
    """Return antidiabetic catalog entries."""
    return [
        _metformina(),
        _glibenclamida(),
    ]


# -- private builders --------------------------------------------------------


def _metformina() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="metformina",
        generic_name="Metformina",
        active_ingredient="Metformina clorhidrato",
        commercial_names=["Glucophage", "Dabex", "Dimefor"],
        category=DrugCategory.ANTIDIABETIC,
        presentations=[
            Presentation(form="tableta", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="850mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="1000mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="500-850mg con alimentos, 2-3 veces al día",
            max_daily_dose="2550mg/día",
            duration_typical="Uso crónico",
            notes="Iniciar con dosis baja e incrementar gradualmente",
        ),
        contraindications=[
            "Insuficiencia renal (TFG <30)",
            "Insuficiencia hepática",
            "Alcoholismo",
        ],
        warnings=[
            "Acidosis láctica (rara)",
            "Suspender antes de estudios con contraste",
        ],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _glibenclamida() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="glibenclamida",
        generic_name="Glibenclamida",
        active_ingredient="Glibenclamida",
        commercial_names=["Euglucon", "Daonil"],
        category=DrugCategory.ANTIDIABETIC,
        presentations=[
            Presentation(form="tableta", strength="5mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="2.5-5mg con desayuno, puede dividirse",
            max_daily_dose="20mg/día",
            duration_typical="Uso crónico",
        ),
        contraindications=[
            "DM tipo 1",
            "Cetoacidosis",
            "Insuficiencia renal o hepática severa",
        ],
        warnings=["Riesgo de hipoglucemia", "Precaución en ancianos"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )
