"""Antihypertensives — Mexico Medication Catalog.

Common blood-pressure medications from the Cuadro Básico / COFEPRIS.

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
    """Return antihypertensive catalog entries."""
    return [
        _losartan(),
        _enalapril(),
        _amlodipino(),
        _metoprolol(),
    ]


# -- private builders --------------------------------------------------------


def _losartan() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="losartan",
        generic_name="Losartán",
        active_ingredient="Losartán potásico",
        commercial_names=["Cozaar", "Losaprex", "Angioten"],
        category=DrugCategory.ANTIHYPERTENSIVE,
        presentations=[
            Presentation(form="tableta", strength="50mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="100mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="50mg cada 24 horas (puede aumentar a 100mg)",
            max_daily_dose="100mg/día",
            duration_typical="Uso crónico",
            notes="Puede usarse en diabéticos con nefropatía",
        ),
        contraindications=["Embarazo", "Estenosis bilateral de arterias renales"],
        interactions=["AINEs (reducen efecto)", "Diuréticos ahorradores de potasio"],
        warnings=["Hiperpotasemia", "Hipotensión primera dosis"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _enalapril() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="enalapril",
        generic_name="Enalapril",
        active_ingredient="Enalapril maleato",
        commercial_names=["Renitec", "Glioten", "Vasotec"],
        category=DrugCategory.ANTIHYPERTENSIVE,
        presentations=[
            Presentation(form="tableta", strength="5mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="10mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="20mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="5-20mg cada 12-24 horas",
            max_daily_dose="40mg/día",
            duration_typical="Uso crónico",
        ),
        contraindications=[
            "Embarazo",
            "Angioedema previo por IECA",
            "Estenosis bilateral arterias renales",
        ],
        warnings=["Tos seca (efecto de clase)", "Angioedema", "Hiperpotasemia"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _amlodipino() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="amlodipino",
        generic_name="Amlodipino",
        active_ingredient="Amlodipino besilato",
        commercial_names=["Norvasc", "Amlibon", "Amlor"],
        category=DrugCategory.ANTIHYPERTENSIVE,
        presentations=[
            Presentation(form="tableta", strength="5mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="10mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="5mg cada 24 horas (puede aumentar a 10mg)",
            max_daily_dose="10mg/día",
            duration_typical="Uso crónico",
        ),
        contraindications=["Hipotensión severa", "Shock cardiogénico"],
        warnings=["Edema de tobillos", "Rubor facial"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _metoprolol() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="metoprolol",
        generic_name="Metoprolol",
        active_ingredient="Metoprolol tartrato/succinato",
        commercial_names=["Lopresor", "Seloken", "Betaloc"],
        category=DrugCategory.ANTIHYPERTENSIVE,
        presentations=[
            Presentation(form="tableta", strength="50mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="100mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="50-100mg cada 12 horas (tartrato) o cada 24h (succinato)",
            max_daily_dose="400mg/día",
            duration_typical="Uso crónico",
            notes="No suspender abruptamente",
        ),
        contraindications=[
            "Bradicardia severa",
            "Bloqueo AV 2do-3er grado",
            "EPOC severo",
        ],
        warnings=[
            "Puede enmascarar hipoglucemia en diabéticos",
            "No suspender bruscamente",
        ],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )
