"""Anxiolytics / Sedatives (Controlled) — Mexico Medication Catalog.

Benzodiazepines and related controlled substances from the Cuadro
Básico / COFEPRIS.  These are Fracción IV under the
*Ley General de Salud*.

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
    """Return anxiolytic / sedative catalog entries."""
    return [
        _clonazepam(),
        _alprazolam(),
    ]


# -- private builders --------------------------------------------------------


def _clonazepam() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="clonazepam",
        generic_name="Clonazepam",
        active_ingredient="Clonazepam",
        commercial_names=["Rivotril", "Klonopin"],
        category=DrugCategory.ANXIOLYTIC,
        presentations=[
            Presentation(form="tableta", strength="0.5mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="2mg", route=MedicationRoute.ORAL),
            Presentation(form="gotas", strength="2.5mg/ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose=(
                "0.25-0.5mg cada 12 horas (ansiedad), "
                "hasta 20mg/día (epilepsia)"
            ),
            notes="Iniciar con dosis bajas, titular lentamente",
        ),
        contraindications=[
            "Miastenia gravis",
            "Insuficiencia respiratoria severa",
            "Apnea del sueño",
        ],
        warnings=[
            "Dependencia física y psicológica",
            "Depresión respiratoria",
            "Síndrome de abstinencia",
        ],
        controlled_level=ControlledSubstanceLevel.FRACTION_IV,
        requires_prescription=True,
        is_essential=True,
    )


def _alprazolam() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="alprazolam",
        generic_name="Alprazolam",
        active_ingredient="Alprazolam",
        commercial_names=["Tafil", "Xanax", "Farmapram"],
        category=DrugCategory.ANXIOLYTIC,
        presentations=[
            Presentation(form="tableta", strength="0.25mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="0.5mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="1mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="0.25-0.5mg cada 8 horas",
            max_daily_dose="4mg/día",
            notes="Alto potencial de dependencia",
        ),
        contraindications=["Glaucoma de ángulo cerrado", "Miastenia gravis"],
        warnings=[
            "Dependencia",
            "No mezclar con alcohol",
            "Síndrome de abstinencia severo",
        ],
        controlled_level=ControlledSubstanceLevel.FRACTION_IV,
        requires_prescription=True,
        is_essential=False,
    )
