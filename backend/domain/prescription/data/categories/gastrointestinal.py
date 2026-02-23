"""Gastrointestinal agents — Mexico Medication Catalog.

Proton-pump inhibitors, H2 blockers, anti-emetics, and antidiarrheals
from the Cuadro Básico / COFEPRIS.

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
    """Return gastrointestinal catalog entries."""
    return [
        _omeprazol(),
        _ranitidina(),
        _metoclopramida(),
        _loperamida(),
    ]


# -- private builders --------------------------------------------------------


def _omeprazol() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="omeprazol",
        generic_name="Omeprazol",
        active_ingredient="Omeprazol",
        commercial_names=["Losec", "Omepral", "Omeprotec"],
        category=DrugCategory.ANTACID,
        presentations=[
            Presentation(form="cápsula", strength="20mg", route=MedicationRoute.ORAL),
            Presentation(form="cápsula", strength="40mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="20mg cada 24 horas antes del desayuno",
            max_daily_dose="40mg/día (80mg en Zollinger-Ellison)",
            duration_typical="4-8 semanas, o uso crónico según indicación",
            notes="Tomar 30-60 minutos antes del desayuno",
        ),
        contraindications=["Hipersensibilidad a IBP"],
        interactions=["Clopidogrel (reduce eficacia)", "Metotrexato"],
        warnings=["Uso prolongado: deficiencia B12, hipomagnesemia, fracturas"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    )


def _ranitidina() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="ranitidina",
        generic_name="Ranitidina",
        active_ingredient="Ranitidina clorhidrato",
        commercial_names=["Zantac", "Ranisen"],
        category=DrugCategory.ANTACID,
        presentations=[
            Presentation(form="tableta", strength="150mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="300mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="150mg cada 12 horas o 300mg al acostarse",
            duration_typical="4-8 semanas",
        ),
        contraindications=["Hipersensibilidad"],
        warnings=["Retiro del mercado en algunos países por impurezas NDMA"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=False,
    )


def _metoclopramida() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="metoclopramida",
        generic_name="Metoclopramida",
        active_ingredient="Metoclopramida clorhidrato",
        commercial_names=["Primperan", "Plasil"],
        category=DrugCategory.GASTROINTESTINAL,
        presentations=[
            Presentation(form="tableta", strength="10mg", route=MedicationRoute.ORAL),
            Presentation(form="solución", strength="5mg/5ml", route=MedicationRoute.ORAL),
            Presentation(
                form="ampolleta",
                strength="10mg/2ml",
                route=MedicationRoute.INTRAMUSCULAR,
            ),
        ],
        standard_dosing=StandardDosing(
            adult_dose="10mg cada 8 horas, 30 minutos antes de alimentos",
            max_daily_dose="30mg/día",
            duration_typical="Máximo 5 días",
            notes="No usar más de 5 días por riesgo de discinesia tardía",
        ),
        contraindications=["Obstrucción intestinal", "Feocromocitoma", "Parkinson"],
        warnings=["Discinesia tardía", "Síndrome neuroléptico maligno"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _loperamida() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="loperamida",
        generic_name="Loperamida",
        active_ingredient="Loperamida clorhidrato",
        commercial_names=["Imodium", "Lomotil"],
        category=DrugCategory.GASTROINTESTINAL,
        presentations=[
            Presentation(form="tableta", strength="2mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="4mg inicial, luego 2mg después de cada evacuación líquida",
            max_daily_dose="16mg/día",
            duration_typical="Uso por episodio agudo",
        ),
        contraindications=[
            "Diarrea con sangre",
            "Colitis ulcerativa aguda",
            "Menores de 2 años",
        ],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    )
