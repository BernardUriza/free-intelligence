"""Mexico Medication Catalog - Common medications.

Based on:
- Cuadro Básico y Catálogo de Medicamentos (IMSS/ISSSTE)
- COFEPRIS registered medications
- Common prescriptions in Mexican healthcare

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-004
"""

from backend.domain.prescription.models.catalog import (
    ControlledSubstanceLevel,
    DrugCategory,
    MedicationCatalogEntry,
    Presentation,
    StandardDosing,
)
from backend.domain.prescription.models.medication import MedicationRoute

# =============================================================================
# MEDICATION CATALOG - MEXICO
# =============================================================================

MEXICO_MEDICATION_CATALOG: list[MedicationCatalogEntry] = [
    # =========================================================================
    # ANALGESICS / ANTIPYRETICS
    # =========================================================================
    MedicationCatalogEntry(
        id="paracetamol",
        generic_name="Paracetamol",
        active_ingredient="Paracetamol (Acetaminofén)",
        commercial_names=["Tempra", "Tylenol", "Mejoral", "Dalay", "Sedalmerck"],
        category=DrugCategory.ANALGESIC,
        presentations=[
            Presentation(form="tableta", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="750mg", route=MedicationRoute.ORAL),
            Presentation(form="jarabe", strength="120mg/5ml", route=MedicationRoute.ORAL, package_size="120ml"),
            Presentation(form="gotas", strength="100mg/ml", route=MedicationRoute.ORAL, package_size="15ml"),
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
    ),
    MedicationCatalogEntry(
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
        contraindications=["Úlcera péptica activa", "Insuficiencia renal severa", "Tercer trimestre embarazo"],
        interactions=["Anticoagulantes", "Litio", "Metotrexato", "IECA"],
        warnings=["Riesgo cardiovascular con uso prolongado", "Sangrado GI"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    ),
    MedicationCatalogEntry(
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
    ),
    MedicationCatalogEntry(
        id="ketorolaco",
        generic_name="Ketorolaco",
        active_ingredient="Ketorolaco trometamina",
        commercial_names=["Dolac", "Supradol", "Toradol"],
        category=DrugCategory.ANTIINFLAMMATORY,
        presentations=[
            Presentation(form="tableta", strength="10mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta sublingual", strength="30mg", route=MedicationRoute.SUBLINGUAL),
            Presentation(form="ampolleta", strength="30mg/ml", route=MedicationRoute.INTRAMUSCULAR),
        ],
        standard_dosing=StandardDosing(
            adult_dose="10mg cada 6 horas VO, 30mg IM dosis única",
            max_daily_dose="40mg/día VO, 120mg/día parenteral",
            duration_typical="Máximo 5 días",
            notes="NO usar más de 5 días por riesgo de sangrado GI",
        ),
        contraindications=["Úlcera péptica", "Insuficiencia renal", "Cirugía con riesgo de sangrado"],
        warnings=["Alto riesgo de sangrado GI", "Uso corto plazo únicamente"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),
    MedicationCatalogEntry(
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
    ),

    # =========================================================================
    # ANTIBIOTICS
    # =========================================================================
    MedicationCatalogEntry(
        id="amoxicilina",
        generic_name="Amoxicilina",
        active_ingredient="Amoxicilina trihidrato",
        commercial_names=["Amoxil", "Trimox", "Grunamox", "Pentrexyl"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="cápsula", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="875mg", route=MedicationRoute.ORAL),
            Presentation(form="suspensión", strength="250mg/5ml", route=MedicationRoute.ORAL, package_size="75ml"),
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
    ),
    MedicationCatalogEntry(
        id="amoxicilina_clavulanato",
        generic_name="Amoxicilina/Ácido clavulánico",
        active_ingredient="Amoxicilina + Ácido clavulánico",
        commercial_names=["Augmentin", "Clavulin", "Optamox Duo"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="tableta", strength="500/125mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="875/125mg", route=MedicationRoute.ORAL),
            Presentation(form="suspensión", strength="250/62.5mg/5ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="500/125mg cada 8 horas o 875/125mg cada 12 horas",
            pediatric_dose="25-45mg/kg/día (componente amoxicilina)",
            duration_typical="7-14 días",
        ),
        contraindications=["Alergia a penicilinas", "Ictericia colestásica previa por este medicamento"],
        warnings=["Mayor incidencia de diarrea que amoxicilina sola"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),
    MedicationCatalogEntry(
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
    ),
    MedicationCatalogEntry(
        id="ciprofloxacino",
        generic_name="Ciprofloxacino",
        active_ingredient="Ciprofloxacino clorhidrato",
        commercial_names=["Cipro", "Ciproxina", "Baycip"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="tableta", strength="250mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="500mg", route=MedicationRoute.ORAL),
            Presentation(form="solución oftálmica", strength="0.3%", route=MedicationRoute.OPHTHALMIC),
        ],
        standard_dosing=StandardDosing(
            adult_dose="250-500mg cada 12 horas",
            max_daily_dose="1500mg/día",
            duration_typical="7-14 días",
            notes="NO usar en menores de 18 años (afecta cartílago)",
        ),
        contraindications=["Menores de 18 años", "Embarazo", "Lactancia", "Miastenia gravis"],
        interactions=["Teofilina", "Warfarina", "Antiácidos (separar 2h)"],
        warnings=["Tendinitis/ruptura de tendón", "Fotosensibilidad"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),
    MedicationCatalogEntry(
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
    ),
    MedicationCatalogEntry(
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
        contraindications=["Alergia a cefalosporinas", "Precaución en alergia a penicilinas"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),
    MedicationCatalogEntry(
        id="trimetoprim_sulfametoxazol",
        generic_name="Trimetoprim/Sulfametoxazol",
        active_ingredient="Trimetoprim + Sulfametoxazol",
        commercial_names=["Bactrim", "Bactiver", "Ectaprim"],
        category=DrugCategory.ANTIBIOTIC,
        presentations=[
            Presentation(form="tableta", strength="80/400mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta forte", strength="160/800mg", route=MedicationRoute.ORAL),
            Presentation(form="suspensión", strength="40/200mg/5ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="160/800mg cada 12 horas",
            pediatric_dose="4/20mg/kg/día dividido cada 12 horas",
            duration_typical="10-14 días para IVU",
        ),
        contraindications=["Alergia a sulfonamidas", "Deficiencia G6PD", "Embarazo primer trimestre"],
        warnings=["Fotosensibilidad", "Reacciones cutáneas graves (Stevens-Johnson)"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),

    # =========================================================================
    # ANTIHYPERTENSIVES
    # =========================================================================
    MedicationCatalogEntry(
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
    ),
    MedicationCatalogEntry(
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
        contraindications=["Embarazo", "Angioedema previo por IECA", "Estenosis bilateral arterias renales"],
        warnings=["Tos seca (efecto de clase)", "Angioedema", "Hiperpotasemia"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),
    MedicationCatalogEntry(
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
    ),
    MedicationCatalogEntry(
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
        contraindications=["Bradicardia severa", "Bloqueo AV 2do-3er grado", "EPOC severo"],
        warnings=["Puede enmascarar hipoglucemia en diabéticos", "No suspender bruscamente"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),

    # =========================================================================
    # ANTIDIABETICS
    # =========================================================================
    MedicationCatalogEntry(
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
        contraindications=["Insuficiencia renal (TFG <30)", "Insuficiencia hepática", "Alcoholismo"],
        warnings=["Acidosis láctica (rara)", "Suspender antes de estudios con contraste"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),
    MedicationCatalogEntry(
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
        contraindications=["DM tipo 1", "Cetoacidosis", "Insuficiencia renal o hepática severa"],
        warnings=["Riesgo de hipoglucemia", "Precaución en ancianos"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),

    # =========================================================================
    # GASTROINTESTINAL
    # =========================================================================
    MedicationCatalogEntry(
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
    ),
    MedicationCatalogEntry(
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
    ),
    MedicationCatalogEntry(
        id="metoclopramida",
        generic_name="Metoclopramida",
        active_ingredient="Metoclopramida clorhidrato",
        commercial_names=["Primperan", "Plasil"],
        category=DrugCategory.GASTROINTESTINAL,
        presentations=[
            Presentation(form="tableta", strength="10mg", route=MedicationRoute.ORAL),
            Presentation(form="solución", strength="5mg/5ml", route=MedicationRoute.ORAL),
            Presentation(form="ampolleta", strength="10mg/2ml", route=MedicationRoute.INTRAMUSCULAR),
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
    ),
    MedicationCatalogEntry(
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
        contraindications=["Diarrea con sangre", "Colitis ulcerativa aguda", "Menores de 2 años"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=True,
    ),

    # =========================================================================
    # ANTIHISTAMINES
    # =========================================================================
    MedicationCatalogEntry(
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
    ),
    MedicationCatalogEntry(
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
    ),

    # =========================================================================
    # CORTICOSTEROIDS
    # =========================================================================
    MedicationCatalogEntry(
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
        warnings=["Supresión adrenal", "Hiperglucemia", "Osteoporosis", "Retención de líquidos"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),
    MedicationCatalogEntry(
        id="dexametasona",
        generic_name="Dexametasona",
        active_ingredient="Dexametasona fosfato sódico",
        commercial_names=["Decadron", "Alin"],
        category=DrugCategory.CORTICOSTEROID,
        presentations=[
            Presentation(form="tableta", strength="0.5mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="4mg", route=MedicationRoute.ORAL),
            Presentation(form="ampolleta", strength="8mg/2ml", route=MedicationRoute.INTRAMUSCULAR),
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
    ),

    # =========================================================================
    # BRONCHODILATORS / RESPIRATORY
    # =========================================================================
    MedicationCatalogEntry(
        id="salbutamol",
        generic_name="Salbutamol",
        active_ingredient="Salbutamol sulfato",
        commercial_names=["Ventolin", "Aeroflux", "Assal"],
        category=DrugCategory.BRONCHODILATOR,
        presentations=[
            Presentation(form="inhalador", strength="100mcg/dosis", route=MedicationRoute.INHALATION, package_size="200 dosis"),
            Presentation(form="solución nebulizar", strength="5mg/ml", route=MedicationRoute.INHALATION),
            Presentation(form="jarabe", strength="2mg/5ml", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="2 inhalaciones cada 4-6 horas PRN",
            pediatric_dose="1-2 inhalaciones cada 4-6 horas PRN",
            notes="Uso de rescate, no preventivo",
        ),
        contraindications=["Hipersensibilidad"],
        warnings=["Taquicardia", "Temblor", "Hipokalemia con uso excesivo"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),

    # =========================================================================
    # MUSCLE RELAXANTS
    # =========================================================================
    MedicationCatalogEntry(
        id="ciclobenzaprina",
        generic_name="Ciclobenzaprina",
        active_ingredient="Ciclobenzaprina clorhidrato",
        commercial_names=["Yurelax", "Flexeril"],
        category=DrugCategory.MUSCLE_RELAXANT,
        presentations=[
            Presentation(form="tableta", strength="10mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="10mg cada 8 horas",
            max_daily_dose="30mg/día",
            duration_typical="2-3 semanas máximo",
        ),
        contraindications=["Arritmias", "ICC", "Hipertiroidismo", "Uso con IMAO"],
        warnings=["Somnolencia", "Boca seca", "No usar >3 semanas"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=False,
    ),

    # =========================================================================
    # ANXIOLYTICS / SEDATIVES (CONTROLLED)
    # =========================================================================
    MedicationCatalogEntry(
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
            adult_dose="0.25-0.5mg cada 12 horas (ansiedad), hasta 20mg/día (epilepsia)",
            notes="Iniciar con dosis bajas, titular lentamente",
        ),
        contraindications=["Miastenia gravis", "Insuficiencia respiratoria severa", "Apnea del sueño"],
        warnings=["Dependencia física y psicológica", "Depresión respiratoria", "Síndrome de abstinencia"],
        controlled_level=ControlledSubstanceLevel.FRACTION_IV,
        requires_prescription=True,
        is_essential=True,
    ),
    MedicationCatalogEntry(
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
        warnings=["Dependencia", "No mezclar con alcohol", "Síndrome de abstinencia severo"],
        controlled_level=ControlledSubstanceLevel.FRACTION_IV,
        requires_prescription=True,
        is_essential=False,
    ),

    # =========================================================================
    # ANTIDEPRESSANTS
    # =========================================================================
    MedicationCatalogEntry(
        id="sertralina",
        generic_name="Sertralina",
        active_ingredient="Sertralina clorhidrato",
        commercial_names=["Zoloft", "Altruline", "Serolux"],
        category=DrugCategory.ANTIDEPRESSANT,
        presentations=[
            Presentation(form="tableta", strength="50mg", route=MedicationRoute.ORAL),
            Presentation(form="tableta", strength="100mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="50mg cada 24 horas, puede aumentar a 200mg",
            max_daily_dose="200mg/día",
            duration_typical="Mínimo 6-12 meses",
            notes="Efecto terapéutico completo en 4-6 semanas",
        ),
        contraindications=["Uso con IMAO (esperar 14 días)", "Pimozida"],
        interactions=["IMAO", "Tramadol", "Triptanos (síndrome serotoninérgico)"],
        warnings=["Ideación suicida inicial en jóvenes", "No suspender abruptamente"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),
    MedicationCatalogEntry(
        id="fluoxetina",
        generic_name="Fluoxetina",
        active_ingredient="Fluoxetina clorhidrato",
        commercial_names=["Prozac", "Fluoxac"],
        category=DrugCategory.ANTIDEPRESSANT,
        presentations=[
            Presentation(form="cápsula", strength="20mg", route=MedicationRoute.ORAL),
        ],
        standard_dosing=StandardDosing(
            adult_dose="20mg cada 24 horas por la mañana",
            max_daily_dose="80mg/día",
            duration_typical="Mínimo 6-12 meses",
        ),
        contraindications=["Uso con IMAO"],
        warnings=["Larga vida media (interacciones prolongadas)", "Ideación suicida en jóvenes"],
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=True,
        is_essential=True,
    ),

    # =========================================================================
    # VITAMINS / SUPPLEMENTS
    # =========================================================================
    MedicationCatalogEntry(
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
    ),
    MedicationCatalogEntry(
        id="complejo_b",
        generic_name="Complejo B",
        active_ingredient="Tiamina + Piridoxina + Cianocobalamina",
        commercial_names=["Bedoyecta", "Neurobion", "Doloneurobion"],
        category=DrugCategory.VITAMIN,
        presentations=[
            Presentation(form="tableta", strength="B1+B6+B12", route=MedicationRoute.ORAL),
            Presentation(form="ampolleta", strength="B1+B6+B12", route=MedicationRoute.INTRAMUSCULAR),
        ],
        standard_dosing=StandardDosing(
            adult_dose="1 tableta cada 24 horas o 1 ampolleta cada 24-72 horas",
        ),
        controlled_level=ControlledSubstanceLevel.NONE,
        requires_prescription=False,
        is_essential=False,
    ),
    MedicationCatalogEntry(
        id="hierro",
        generic_name="Sulfato ferroso",
        active_ingredient="Sulfato ferroso",
        commercial_names=["Ferranina", "Fer-In-Sol", "Iberol"],
        category=DrugCategory.VITAMIN,
        presentations=[
            Presentation(form="tableta", strength="200mg (65mg Fe elemental)", route=MedicationRoute.ORAL),
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
    ),
]

