"""Analgesics / Antipyretics — Mexico Medication Catalog.

Covers non-opioid analgesics and antipyretics commonly prescribed in
Mexican healthcare (Cuadro Básico / COFEPRIS).

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
    """Return analgesic / antipyretic catalog entries."""
    return [
        _paracetamol(),
        _metamizol(),
    ]


# -- private builders --------------------------------------------------------


def _paracetamol() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="paracetamol",
        generic_name="Paracetamol",
        active_ingredient="Paracetamol (Acetaminofén)",
        commercial_names=["Tempra", "Tylenol", "Mejoral", "Dalay", "Sedalmerck"],
        category=DrugCategory.ANALGESIC,
        presentations=[
            Presentation(form="tableta", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="750mg", route=MedicationRoute.ORAL),
            Presentation(
                form="jarabe",
                strength="120mg/5ml",
                route=MedicationRoute.ORAL,
                package_size="120ml",
            ),
            Presentation(
                form="gotas",
                strength="100mg/ml",
                route=MedicationRoute.ORAL,
                package_size="15ml",
            ),
            Presentation(form="supositorio", strength="300mg", route=MedicationRoute.RECTAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="500-1000mg cada 6-8 horas",
            pediatric_dose="10-15mg/kg cada 6 horas",
            max_daily_dose="4g/día (adultos), 75mg/kg/día (niños)",
            duration_typical="Según dolor/fiebre",
            notes="No exceder dosis máxima por riesgo de hepatotoxicidad",
        ),
        contraindications=["Hipersensibilidad", "Insuficiencia hepática severa"],
        warnings=["Hepatotoxicidad en sobredosis", "Precaución en alcoholismo crónico"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    )


def _metamizol() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="metamizol",
        generic_name="Metamizol",
        active_ingredient="Metamizol sódico (Dipirona)",
        commercial_names=["Neo-Melubrina", "Prodolina", "Magnopyrol"],
        category=DrugCategory.ANALGESIC,
        presentations=[
            Presentation(form="tableta", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="ampolleta", strength="1g/2ml", route=MedicationRoute.INTRAMUSCULAR),
            Presentation(form="gotas", strength="500mg/ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="500mg-1g cada 6-8 horas",
            pediatric_dose="10mg/kg cada 6-8 horas",
            max_daily_dose="4g/día",
        ),
        contraindications=["Porfiria", "Deficiencia G6PD", "Agranulocitosis previa"],
        warnings=["Riesgo de agranulocitosis", "Hipotensión con administración IV rápida"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )
