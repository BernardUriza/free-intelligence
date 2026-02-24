"""Corticosteroids — Mexico Medication Catalog.

Systemic corticosteroids from the Cuadro Básico / COFEPRIS.

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
    """Return corticosteroid catalog entries."""
    return [
        _prednisona(),
        _dexametasona(),
    ]


# -- private builders --------------------------------------------------------


def _prednisona() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="prednisona",
        generic_name="Prednisona",
        active_ingredient="Prednisona",
        commercial_names=["Meticorten", "Sterapred"],
        category=DrugCategory.CORTICOSTEROID,
        presentations=[
            Presentation(form="tableta", strength="5mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="50mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="5-60mg/día según indicación",
            pediatric_dose="0.5-2mg/kg/día",
            duration_typical="Variable, reducir gradualmente",
            notes="NO suspender abruptamente si uso >7 días",
        ),
        contraindications=["Infecciones sistémicas sin tratamiento", "Vacunas vivas"],
        warnings=[
            "Supresión adrenal",
            "Hiperglucemia",
            "Osteoporosis",
            "Retención de líquidos",
        ],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _dexametasona() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="dexametasona",
        generic_name="Dexametasona",
        active_ingredient="Dexametasona fosfato sódico",
        commercial_names=["Decadron", "Alin"],
        category=DrugCategory.CORTICOSTEROID,
        presentations=[
            Presentation(form="tableta", strength="0.5mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="4mg", route=MedicationRoute.ORAL),
            Presentation(
                form="ampolleta",
                strength="8mg/2ml",
                route=MedicationRoute.INTRAMUSCULAR,
            ),
        ],
        standard_dosing=StandardDosing(
            adult_dose="0.5-9mg/día según indicación",
            notes="Potencia ~7 veces mayor que prednisona",
        ),
        contraindications=["Infecciones fúngicas sistémicas"],
        warnings=["Mayor supresión adrenal que prednisona", "Hiperglucemia"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )
