"""Antibiotics — Mexico Medication Catalog.

Common antibiotics from the Cuadro Básico / COFEPRIS registry.

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
    """Return antibiotic catalog entries."""
    return [
        _amoxicilina(),
        _amoxicilina_clavulanato(),
        _azitromicina(),
        _ciprofloxacino(),
        _levofloxacino(),
        _cefalexina(),
        _trimetoprim_sulfametoxazol(),
    ]


# -- private builders --------------------------------------------------------


def _amoxicilina() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="amoxicilina",
        generic_name="Amoxicilina",
        active_ingredient="Amoxicilina trihidrato",
        commercial_names=["Amoxil", "Trimox", "Grunamox", "Pentrexyl"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="cápsula", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="875mg", route=MedicationRoute.ORAL),
            Presentation(
                form="suspensión",
                strength="250mg/5ml",
                route=MedicationRoute.ORAL,
                package_size="75ml",
            ),
        ],
        standard_dosing=StandardDosing(
            adult_dose="500mg cada 8 horas o 875mg cada 12 horas",
            pediatric_dose="25-50mg/kg/día dividido cada 8 horas",
            max_daily_dose="3g/día",
            duration_typical="7-10 días",
        ),
        contraindications=["Alergia a penicilinas", "Mononucleosis infecciosa"],
        interactions=["Anticonceptivos orales (reduce eficacia)", "Alopurinol (rash)"],
        warnings=["Verificar alergia a penicilinas", "Puede causar diarrea"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _amoxicilina_clavulanato() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="amoxicilina_clavulanato",
        generic_name="Amoxicilina/Ácido clavulánico",
        active_ingredient="Amoxicilina + Ácido clavulánico",
        commercial_names=["Augmentin", "Clavulin", "Optamox Duo"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="tableta", strength="500/125mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="875/125mg", route=MedicationRoute.ORAL),
            Presentation(
                form="suspensión",
                strength="250/62.5mg/5ml",
                route=MedicationRoute.ORAL,
            ),
        ],
        standard_dosing=StandardDosing(
            adult_dose="500/125mg cada 8 horas o 875/125mg cada 12 horas",
            pediatric_dose="25-45mg/kg/día (componente amoxicilina)",
            duration_typical="7-14 días",
        ),
        contraindications=[
            "Alergia a penicilinas",
            "Ictericia colestásica previa por este medicamento",
        ],
        warnings=["Mayor incidencia de diarrea que amoxicilina sola"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _azitromicina() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="azitromicina",
        generic_name="Azitromicina",
        active_ingredient="Azitromicina dihidrato",
        commercial_names=["Zithromax", "Azitrocin", "Macrozit"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="tableta", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="suspensión", strength="200mg/5ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="500mg día 1, luego 250mg días 2-5 (o 500mg por 3 días)",
            pediatric_dose="10mg/kg día 1, luego 5mg/kg días 2-5",
            duration_typical="3-5 días",
            notes="Tomar 1 hora antes o 2 horas después de alimentos",
        ),
        contraindications=["Hipersensibilidad a macrólidos", "QT prolongado"],
        interactions=["Warfarina", "Digoxina", "Ergotamina"],
        warnings=["Puede prolongar QT", "Hepatotoxicidad rara"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _ciprofloxacino() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="ciprofloxacino",
        generic_name="Ciprofloxacino",
        active_ingredient="Ciprofloxacino clorhidrato",
        commercial_names=["Cipro", "Ciproxina", "Baycip"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="tableta", strength="250mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(
                form="solución oftálmica",
                strength="0.3%",
                route=MedicationRoute.OPHTHALMIC,
            ),
        ],
        standard_dosing=StandardDosing(
            adult_dose="250-500mg cada 12 horas",
            max_daily_dose="1500mg/día",
            duration_typical="7-14 días",
            notes="NO usar en menores de 18 años (afecta cartílago)",
        ),
        contraindications=[
            "Menores de 18 años",
            "Embarazo",
            "Lactancia",
            "Miastenia gravis",
        ],
        interactions=["Teofilina", "Warfarina", "Antiácidos (separar 2h)"],
        warnings=["Tendinitis/ruptura de tendón", "Fotosensibilidad"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _levofloxacino() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="levofloxacino",
        generic_name="Levofloxacino",
        active_ingredient="Levofloxacino hemihidrato",
        commercial_names=["Tavanic", "Levaquin", "Elequine"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="tableta", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="750mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="500mg cada 24 horas o 750mg cada 24 horas",
            duration_typical="5-14 días según indicación",
        ),
        contraindications=["Menores de 18 años", "Epilepsia", "Miastenia gravis"],
        warnings=["Ruptura de tendón de Aquiles", "Neuropatía periférica"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _cefalexina() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="cefalexina",
        generic_name="Cefalexina",
        active_ingredient="Cefalexina monohidrato",
        commercial_names=["Keflex", "Ceporex"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="cápsula", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="suspensión", strength="250mg/5ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="500mg cada 6 horas",
            pediatric_dose="25-50mg/kg/día dividido cada 6-8 horas",
            max_daily_dose="4g/día",
            duration_typical="7-14 días",
        ),
        contraindications=[
            "Alergia a cefalosporinas",
            "Precaución en alergia a penicilinas",
        ],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )


def _trimetoprim_sulfametoxazol() -> MedicationCatalogEntry:
    return MedicationCatalogEntry(
        id="trimetoprim_sulfametoxazol",
        generic_name="Trimetoprim/Sulfametoxazol",
        active_ingredient="Trimetoprim + Sulfametoxazol",
        commercial_names=["Bactrim", "Bactiver", "Ectaprim"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="tableta", strength="80/400mg", route=MedicationRoute.ORAL),
            Presentation(
                form="tableta forte",
                strength="160/800mg",
                route=MedicationRoute.ORAL,
            ),
            Presentation(
                form="suspensión",
                strength="40/200mg/5ml",
                route=MedicationRoute.ORAL,
            ),
        ],
        standard_dosing=StandardDosing(
            adult_dose="160/800mg cada 12 horas",
            pediatric_dose="4/20mg/kg/día dividido cada 12 horas",
            duration_typical="10-14 días para IVU",
        ),
        contraindications=[
            "Alergia a sulfonamidas",
            "Deficiencia G6PD",
            "Embarazo primer trimestre",
        ],
        warnings=["Fotosensibilidad", "Reacciones cutáneas graves (Stevens-Johnson)"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    )
