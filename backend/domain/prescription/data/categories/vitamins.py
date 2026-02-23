"""Vitamins / Supplements — Mexico Medication Catalog.

Essential vitamins and mineral supplements from the Cuadro Básico /
COFEPRIS.

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
    """Return vitamin / supplement catalog entries."""
    return [
        _acido_folico(),
        _complejo_b(),
        _hierro(),
    ]


# -- private builders --------------------------------------------------------


def _acido_folico() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="acido_folico",
        generic_name="Ácido fólico",
        active_ingredient="Ácido fólico",
        commercial_names=["Acfol", "Folivit"],
        category=DrugCategory.VITAMIN,
        presentations=[
            Presentation(form="tableta", strength="5mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="400mcg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="400mcg-5mg cada 24 horas",
            notes="Esencial en embarazo para prevención de defectos tubo neural",
        ),
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    )


def _complejo_b() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="complejo_b",
        generic_name="Complejo B",
        active_ingredient="Tiamina + Piridoxina + Cianocobalamina",
        commercial_names=["Bedoyecta", "Neurobion", "Doloneurobion"],
        category=DrugCategory.VITAMIN,
        presentations=[
            Presentation(form="tableta", strength="B1+B6+B12", route=MedicationRoute.ORAL),
            Presentation(
                form="ampolleta",
                strength="B1+B6+B12",
                route=MedicationRoute.INTRAMUSCULAR,
            ),
        ],
        standard_dosing=StandardDosing(
            adult_dose="1 tableta cada 24 horas o 1 ampolleta cada 24-72 horas",
        ),
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=False,
    )


def _hierro() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="hierro",
        generic_name="Sulfato ferroso",
        active_ingredient="Sulfato ferroso",
        commercial_names=["Ferranina", "Fer-In-Sol", "Iberol"],
        category=DrugCategory.VITAMIN,
        presentations=[
            Presentation(
                form="tableta",
                strength="200mg (65mg Fe elemental)",
                route=MedicationRoute.ORAL,
            ),
            Presentation(form="gotas", strength="125mg/ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="200mg cada 8-12 horas",
            pediatric_dose="3-6mg/kg/día de hierro elemental",
            notes="Tomar en ayunas con vitamina C para mejor absorción",
        ),
        contraindications=["Hemocromatosis", "Hemosiderosis"],
        warnings=["Estreñimiento", "Coloración oscura de heces"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    )
