"""Anti-inflammatories (NSAIDs) — Mexico Medication Catalog.

Non-steroidal anti-inflammatory drugs commonly prescribed in
Mexican healthcare.

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
    """Return NSAID catalog entries."""
    return [
        _ibuprofeno(),
        _naproxeno(),
        _ketorolaco(),
    ]


# -- private builders --------------------------------------------------------


def _ibuprofeno() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="ibuprofeno",
        generic_name="Ibuprofeno",
        active_ingredient="Ibuprofeno",
        commercial_names=["Advil", "Motrin", "Tabcin", "Actron"],
        category=DrugCategory.ANTIINFLAMMATORY,
        presentations=[
            Presentation(form="tableta", strength="200mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="400mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="600mg", route=MedicationRoute.ORAL),
            Presentation(form="suspensión", strength="100mg/5ml", route=MedicationRoute.ORAL),
            Presentation(form="gel", strength="5%", route=MedicationRoute.TOPICAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="400mg cada 6-8 horas",
            pediatric_dose="5-10mg/kg cada 6-8 horas",
            max_daily_dose="2400mg/día (adultos)",
            duration_typical="5-7 días máximo sin supervisión",
            notes="Tomar con alimentos para reducir irritación gástrica",
        ),
        contraindications=[
            "Úlcera péptica activa",
            "Insuficiencia renal severa",
            "Tercer trimestre embarazo",
        ],
        interactions=["Anticoagulantes", "Litio", "Metotrexato", "IECA"],
        warnings=["Riesgo cardiovascular con uso prolongado", "Sangrado GI"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    )


def _naproxeno() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="naproxeno",
        generic_name="Naproxeno",
        active_ingredient="Naproxeno sódico",
        commercial_names=["Flanax", "Naxen", "Aleve"],
        category=DrugCategory.ANTIINFLAMMATORY,
        presentations=[
            Presentation(form="tableta", strength="250mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="suspensión", strength="125mg/5ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="250-500mg cada 12 horas",
            pediatric_dose="5mg/kg cada 12 horas",
            max_daily_dose="1250mg/día",
        ),
        contraindications=["Úlcera péptica", "Alergia a AINEs", "Embarazo tercer trimestre"],
        warnings=["Riesgo GI y cardiovascular"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    )


def _ketorolaco() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="ketorolaco",
        generic_name="Ketorolaco",
        active_ingredient="Ketorolaco trometamina",
        commercial_names=["Dolac", "Supradol", "Toradol"],
        category=DrugCategory.ANTIINFLAMMATORY,
        presentations=[
            Presentation(form="tableta", strength="10mg", route=MedicationRoute.ORAL),
            Presentation(
                form="tableta sublingual",
                strength="30mg",
                route=MedicationRoute.SUBLINGUAL,
            ),
            Presentation(
                form="ampolleta",
                strength="30mg/ml",
                route=MedicationRoute.INTRAMUSCULAR,
            ),
        ],
        standard_dosing=StandardDosing(
            adult_dose="10mg cada 6 horas VO, 30mg IM dosis única",
            max_daily_dose="40mg/día VO, 120mg/día parenteral",
            duration_typical="Máximo 5 días",
            notes="NO usar más de 5 días por riesgo de sangrado GI",
        ),
        contraindications=[
            "Úlcera péptica",
            "Insuficiencia renal",
            "Cirugía con riesgo de sangrado",
        ],
        warnings=["Alto riesgo de sangrado GI", "Uso corto plazo únicamente"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )
