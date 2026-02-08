"""Drug Interactions Catalog - Mexico.

Database of clinically significant drug-drug interactions
for medications commonly used in Mexico.

Based on:
- COFEPRIS pharmacovigilance data
- Mexican pharmaceutical guidelines
- International drug interaction databases (Lexicomp, Micromedex)

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-008
"""

from backend.domain.prescription.models.interaction import (
    DrugInteraction,
    InteractionMechanism,
    InteractionSeverity,
)

# =============================================================================
# DRUG INTERACTIONS DATABASE - MEXICO
# =============================================================================

DRUG_INTERACTIONS_CATALOG: list[DrugInteraction] = [
    # =========================================================================
    # ANTICOAGULANTS / ANTIPLATELETS
    # =========================================================================
    DrugInteraction(
        id="warfarina_aines",
        drug_a="Warfarina",
        drug_b="AINEs",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Increased risk of bleeding due to antiplatelet effect of NSAIDs",
        effect_es="Riesgo aumentado de sangrado por efecto antiplaquetario de AINEs",
        recommendation="Avoid NSAIDs if possible; use paracetamol instead",
        recommendation_es="Evitar AINEs si es posible; usar paracetamol como alternativa",
        monitoring="INR, signos de sangrado",
        evidence_level="high",
    ),
    DrugInteraction(
        id="warfarina_ibuprofeno",
        drug_a="Warfarina",
        drug_b="Ibuprofeno",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Increased bleeding risk; NSAIDs inhibit platelet function",
        effect_es="Riesgo de sangrado aumentado; AINEs inhiben función plaquetaria",
        recommendation="Avoid combination; use paracetamol for pain",
        recommendation_es="Evitar combinación; usar paracetamol para el dolor",
        monitoring="INR cada 3-5 días, signos de sangrado GI",
        evidence_level="high",
    ),
    DrugInteraction(
        id="warfarina_naproxeno",
        drug_a="Warfarina",
        drug_b="Naproxeno",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Increased bleeding risk",
        effect_es="Riesgo aumentado de hemorragia",
        recommendation="Avoid; use paracetamol instead",
        recommendation_es="Evitar; usar paracetamol como alternativa",
        monitoring="INR, signos de sangrado",
        evidence_level="high",
    ),
    DrugInteraction(
        id="warfarina_ketorolaco",
        drug_a="Warfarina",
        drug_b="Ketorolaco",
        severity=InteractionSeverity.CONTRAINDICATED,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="High risk of serious bleeding; ketorolac strongly inhibits platelets",
        effect_es="Alto riesgo de sangrado grave; ketorolaco inhibe fuertemente plaquetas",
        recommendation="CONTRAINDICATED - Never use together",
        recommendation_es="CONTRAINDICADO - Nunca usar juntos",
        evidence_level="high",
    ),
    DrugInteraction(
        id="warfarina_omeprazol",
        drug_a="Warfarina",
        drug_b="Omeprazol",
        severity=InteractionSeverity.MODERATE,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Omeprazole may increase warfarin effect via CYP2C19 inhibition",
        effect_es="Omeprazol puede aumentar efecto de warfarina por inhibición CYP2C19",
        recommendation="Monitor INR closely; may need dose reduction",
        recommendation_es="Monitorear INR de cerca; puede requerir reducción de dosis",
        monitoring="INR semanal las primeras 2 semanas",
        evidence_level="moderate",
    ),
    DrugInteraction(
        id="warfarina_azitromicina",
        drug_a="Warfarina",
        drug_b="Azitromicina",
        severity=InteractionSeverity.MODERATE,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Azithromycin may increase warfarin effect",
        effect_es="Azitromicina puede aumentar efecto anticoagulante",
        recommendation="Monitor INR during and after antibiotic course",
        recommendation_es="Monitorear INR durante y después del antibiótico",
        monitoring="INR a los 3-5 días de iniciar antibiótico",
        evidence_level="moderate",
    ),
    DrugInteraction(
        id="warfarina_ciprofloxacino",
        drug_a="Warfarina",
        drug_b="Ciprofloxacino",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Ciprofloxacin significantly increases warfarin effect",
        effect_es="Ciprofloxacino aumenta significativamente efecto de warfarina",
        recommendation="Reduce warfarin dose by 25-30%; monitor INR closely",
        recommendation_es="Reducir dosis de warfarina 25-30%; monitorear INR",
        monitoring="INR cada 2-3 días",
        evidence_level="high",
    ),

    # =========================================================================
    # ANTIHYPERTENSIVES
    # =========================================================================
    DrugInteraction(
        id="ieca_aines",
        drug_a="IECA",
        drug_b="AINEs",
        severity=InteractionSeverity.MODERATE,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="NSAIDs reduce antihypertensive effect and may worsen renal function",
        effect_es="AINEs reducen efecto antihipertensivo y pueden empeorar función renal",
        recommendation="Monitor BP and renal function; use lowest NSAID dose",
        recommendation_es="Monitorear TA y función renal; usar dosis mínima de AINE",
        monitoring="Tensión arterial, creatinina sérica",
        evidence_level="high",
    ),
    DrugInteraction(
        id="enalapril_ibuprofeno",
        drug_a="Enalapril",
        drug_b="Ibuprofeno",
        severity=InteractionSeverity.MODERATE,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Ibuprofen reduces antihypertensive effect of ACE inhibitors",
        effect_es="Ibuprofeno reduce efecto antihipertensivo del IECA",
        recommendation="Monitor blood pressure; consider paracetamol instead",
        recommendation_es="Monitorear presión arterial; considerar paracetamol",
        monitoring="Tensión arterial diaria",
        evidence_level="high",
    ),
    DrugInteraction(
        id="losartan_ibuprofeno",
        drug_a="Losartán",
        drug_b="Ibuprofeno",
        severity=InteractionSeverity.MODERATE,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="NSAIDs reduce antihypertensive effect of ARBs",
        effect_es="AINEs reducen efecto antihipertensivo de ARA-II",
        recommendation="Monitor BP; use paracetamol when possible",
        recommendation_es="Monitorear TA; usar paracetamol cuando sea posible",
        monitoring="Tensión arterial, potasio sérico",
        evidence_level="high",
    ),
    DrugInteraction(
        id="enalapril_espironolactona",
        drug_a="Enalapril",
        drug_b="Espironolactona",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="High risk of hyperkalemia",
        effect_es="Alto riesgo de hiperpotasemia",
        recommendation="Monitor potassium closely; avoid in renal impairment",
        recommendation_es="Monitorear potasio de cerca; evitar en insuficiencia renal",
        monitoring="Potasio sérico semanal al inicio",
        evidence_level="high",
    ),
    DrugInteraction(
        id="losartan_potasio",
        drug_a="Losartán",
        drug_b="Suplementos de potasio",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Risk of hyperkalemia",
        effect_es="Riesgo de hiperpotasemia",
        recommendation="Avoid potassium supplements unless hypokalemic",
        recommendation_es="Evitar suplementos de potasio excepto si hay hipopotasemia",
        monitoring="Potasio sérico",
        evidence_level="high",
    ),
    DrugInteraction(
        id="metoprolol_verapamilo",
        drug_a="Metoprolol",
        drug_b="Verapamilo",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Severe bradycardia and heart block risk",
        effect_es="Riesgo de bradicardia severa y bloqueo cardíaco",
        recommendation="Avoid combination; monitor HR and ECG if used",
        recommendation_es="Evitar combinación; monitorear FC y ECG si se usa",
        monitoring="ECG, frecuencia cardíaca",
        evidence_level="high",
    ),

    # =========================================================================
    # ANTIDIABETICS
    # =========================================================================
    DrugInteraction(
        id="metformina_contraste",
        drug_a="Metformina",
        drug_b="Medios de contraste yodados",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Risk of lactic acidosis due to contrast-induced nephropathy",
        effect_es="Riesgo de acidosis láctica por nefropatía por contraste",
        recommendation="Stop metformin 48h before and after contrast",
        recommendation_es="Suspender metformina 48h antes y después del contraste",
        monitoring="Función renal antes de reiniciar",
        evidence_level="high",
    ),
    DrugInteraction(
        id="glibenclamida_fluconazol",
        drug_a="Glibenclamida",
        drug_b="Fluconazol",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Fluconazole inhibits sulfonylurea metabolism; hypoglycemia risk",
        effect_es="Fluconazol inhibe metabolismo de sulfonilurea; riesgo de hipoglucemia",
        recommendation="Reduce sulfonylurea dose by 50%; monitor glucose",
        recommendation_es="Reducir dosis de sulfonilurea 50%; monitorear glucosa",
        monitoring="Glucosa capilar cada 6-8 horas",
        evidence_level="high",
    ),
    DrugInteraction(
        id="metformina_alcohol",
        drug_a="Metformina",
        drug_b="Alcohol",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Increased risk of lactic acidosis",
        effect_es="Riesgo aumentado de acidosis láctica",
        recommendation="Limit alcohol intake; avoid binge drinking",
        recommendation_es="Limitar consumo de alcohol; evitar consumo excesivo",
        evidence_level="high",
    ),
    DrugInteraction(
        id="glibenclamida_betabloqueador",
        drug_a="Glibenclamida",
        drug_b="Metoprolol",
        severity=InteractionSeverity.MODERATE,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Beta-blockers may mask hypoglycemia symptoms",
        effect_es="Betabloqueadores pueden enmascarar síntomas de hipoglucemia",
        recommendation="Monitor glucose more frequently; educate patient",
        recommendation_es="Monitorear glucosa más frecuente; educar al paciente",
        monitoring="Glucosa capilar",
        evidence_level="moderate",
    ),

    # =========================================================================
    # ANTIBIOTICS
    # =========================================================================
    DrugInteraction(
        id="ciprofloxacino_antiacidos",
        drug_a="Ciprofloxacino",
        drug_b="Antiácidos (Al/Mg)",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Antacids reduce ciprofloxacin absorption by 90%",
        effect_es="Antiácidos reducen absorción de ciprofloxacino en 90%",
        recommendation="Take ciprofloxacin 2h before or 6h after antacids",
        recommendation_es="Tomar ciprofloxacino 2h antes o 6h después de antiácidos",
        evidence_level="high",
    ),
    DrugInteraction(
        id="ciprofloxacino_hierro",
        drug_a="Ciprofloxacino",
        drug_b="Sulfato ferroso",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Iron significantly reduces fluoroquinolone absorption",
        effect_es="Hierro reduce significativamente absorción de fluoroquinolona",
        recommendation="Separate doses by at least 2 hours",
        recommendation_es="Separar dosis por al menos 2 horas",
        evidence_level="high",
    ),
    DrugInteraction(
        id="azitromicina_antiacidos",
        drug_a="Azitromicina",
        drug_b="Antiácidos (Al/Mg)",
        severity=InteractionSeverity.MODERATE,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Antacids reduce azithromycin peak levels",
        effect_es="Antiácidos reducen niveles pico de azitromicina",
        recommendation="Take azithromycin 1h before or 2h after antacids",
        recommendation_es="Tomar azitromicina 1h antes o 2h después de antiácidos",
        evidence_level="moderate",
    ),
    DrugInteraction(
        id="metronidazol_alcohol",
        drug_a="Metronidazol",
        drug_b="Alcohol",
        severity=InteractionSeverity.CONTRAINDICATED,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Disulfiram-like reaction: nausea, vomiting, flushing, tachycardia",
        effect_es="Reacción tipo disulfiram: náusea, vómito, rubor, taquicardia",
        recommendation="AVOID alcohol during and 48h after treatment",
        recommendation_es="EVITAR alcohol durante y 48h después del tratamiento",
        evidence_level="high",
    ),
    DrugInteraction(
        id="amoxicilina_anticonceptivos",
        drug_a="Amoxicilina",
        drug_b="Anticonceptivos orales",
        severity=InteractionSeverity.MINOR,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Theoretical reduction in contraceptive efficacy",
        effect_es="Reducción teórica de eficacia anticonceptiva",
        recommendation="Use backup contraception during antibiotic course",
        recommendation_es="Usar método anticonceptivo adicional durante antibiótico",
        evidence_level="low",
    ),

    # =========================================================================
    # GASTROINTESTINAL
    # =========================================================================
    DrugInteraction(
        id="omeprazol_clopidogrel",
        drug_a="Omeprazol",
        drug_b="Clopidogrel",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Omeprazole reduces clopidogrel antiplatelet effect via CYP2C19",
        effect_es="Omeprazol reduce efecto antiplaquetario de clopidogrel por CYP2C19",
        recommendation="Use pantoprazole instead; it has less interaction",
        recommendation_es="Usar pantoprazol en su lugar; tiene menos interacción",
        evidence_level="high",
    ),
    DrugInteraction(
        id="metoclopramida_levodopa",
        drug_a="Metoclopramida",
        drug_b="Levodopa",
        severity=InteractionSeverity.CONTRAINDICATED,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Metoclopramide blocks dopamine; worsens Parkinson symptoms",
        effect_es="Metoclopramida bloquea dopamina; empeora síntomas de Parkinson",
        recommendation="CONTRAINDICATED in Parkinson's disease",
        recommendation_es="CONTRAINDICADO en enfermedad de Parkinson",
        evidence_level="high",
    ),
    DrugInteraction(
        id="omeprazol_metotrexato",
        drug_a="Omeprazol",
        drug_b="Metotrexato",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="PPIs may increase methotrexate levels and toxicity",
        effect_es="IBPs pueden aumentar niveles y toxicidad de metotrexato",
        recommendation="Avoid PPIs with high-dose methotrexate",
        recommendation_es="Evitar IBPs con metotrexato en dosis altas",
        monitoring="Niveles de metotrexato, función renal",
        evidence_level="moderate",
    ),

    # =========================================================================
    # PSYCHOTROPICS
    # =========================================================================
    DrugInteraction(
        id="sertralina_tramadol",
        drug_a="Sertralina",
        drug_b="Tramadol",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Risk of serotonin syndrome",
        effect_es="Riesgo de síndrome serotoninérgico",
        recommendation="Avoid combination; if necessary, monitor for serotonin syndrome",
        recommendation_es="Evitar combinación; si es necesario, vigilar síndrome serotoninérgico",
        monitoring="Signos de agitación, hipertermia, rigidez",
        evidence_level="high",
    ),
    DrugInteraction(
        id="fluoxetina_tramadol",
        drug_a="Fluoxetina",
        drug_b="Tramadol",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Risk of serotonin syndrome and seizures",
        effect_es="Riesgo de síndrome serotoninérgico y convulsiones",
        recommendation="Avoid combination; use alternative analgesics",
        recommendation_es="Evitar combinación; usar analgésicos alternativos",
        evidence_level="high",
    ),
    DrugInteraction(
        id="sertralina_imao",
        drug_a="Sertralina",
        drug_b="IMAO",
        severity=InteractionSeverity.CONTRAINDICATED,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Severe serotonin syndrome risk; potentially fatal",
        effect_es="Riesgo grave de síndrome serotoninérgico; potencialmente fatal",
        recommendation="CONTRAINDICATED - wait 14 days between drugs",
        recommendation_es="CONTRAINDICADO - esperar 14 días entre medicamentos",
        evidence_level="high",
    ),
    DrugInteraction(
        id="clonazepam_alcohol",
        drug_a="Clonazepam",
        drug_b="Alcohol",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Additive CNS depression; respiratory depression risk",
        effect_es="Depresión aditiva del SNC; riesgo de depresión respiratoria",
        recommendation="Avoid alcohol completely while taking benzodiazepines",
        recommendation_es="Evitar alcohol completamente mientras tome benzodiacepinas",
        evidence_level="high",
    ),
    DrugInteraction(
        id="alprazolam_alcohol",
        drug_a="Alprazolam",
        drug_b="Alcohol",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Severe CNS and respiratory depression",
        effect_es="Depresión severa del SNC y respiratoria",
        recommendation="AVOID alcohol with benzodiazepines",
        recommendation_es="EVITAR alcohol con benzodiacepinas",
        evidence_level="high",
    ),
    DrugInteraction(
        id="clonazepam_opioides",
        drug_a="Clonazepam",
        drug_b="Opioides",
        severity=InteractionSeverity.CONTRAINDICATED,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="High risk of fatal respiratory depression",
        effect_es="Alto riesgo de depresión respiratoria fatal",
        recommendation="AVOID combination; if necessary, use lowest doses",
        recommendation_es="EVITAR combinación; si es necesario, usar dosis mínimas",
        monitoring="Saturación de oxígeno, frecuencia respiratoria",
        evidence_level="high",
    ),

    # =========================================================================
    # CORTICOSTEROIDS
    # =========================================================================
    DrugInteraction(
        id="prednisona_aines",
        drug_a="Prednisona",
        drug_b="AINEs",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Increased risk of GI bleeding and ulcers",
        effect_es="Riesgo aumentado de sangrado GI y úlceras",
        recommendation="Add PPI gastroprotection if combination necessary",
        recommendation_es="Agregar gastroprotección con IBP si es necesaria combinación",
        monitoring="Signos de sangrado GI",
        evidence_level="high",
    ),
    DrugInteraction(
        id="dexametasona_warfarina",
        drug_a="Dexametasona",
        drug_b="Warfarina",
        severity=InteractionSeverity.MODERATE,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Corticosteroids may reduce warfarin effect",
        effect_es="Corticosteroides pueden reducir efecto de warfarina",
        recommendation="Monitor INR when starting or stopping steroids",
        recommendation_es="Monitorear INR al iniciar o suspender esteroides",
        monitoring="INR",
        evidence_level="moderate",
    ),
    DrugInteraction(
        id="prednisona_antidiabeticos",
        drug_a="Prednisona",
        drug_b="Antidiabéticos",
        severity=InteractionSeverity.MODERATE,
        mechanism=InteractionMechanism.PHARMACODYNAMIC,
        effect="Corticosteroids increase blood glucose",
        effect_es="Corticosteroides aumentan glucosa en sangre",
        recommendation="Monitor glucose; may need to increase antidiabetic dose",
        recommendation_es="Monitorear glucosa; puede requerir aumentar dosis de antidiabético",
        monitoring="Glucosa capilar frecuente",
        evidence_level="high",
    ),

    # =========================================================================
    # ANALGESICS
    # =========================================================================
    DrugInteraction(
        id="paracetamol_alcohol_cronico",
        drug_a="Paracetamol",
        drug_b="Alcohol (uso crónico)",
        severity=InteractionSeverity.MAJOR,
        mechanism=InteractionMechanism.PHARMACOKINETIC,
        effect="Chronic alcohol use increases risk of paracetamol hepatotoxicity",
        effect_es="Uso crónico de alcohol aumenta riesgo de hepatotoxicidad por paracetamol",
        recommendation="Max 2g/day paracetamol in chronic alcoholics",
        recommendation_es="Máximo 2g/día de paracetamol en alcohólicos crónicos",
        monitoring="Función hepática",
        evidence_level="high",
    ),
    DrugInteraction(
        id="ketorolaco_otros_aines",
        drug_a="Ketorolaco",
        drug_b="Otros AINEs",
        severity=InteractionSeverity.CONTRAINDICATED,
        mechanism=InteractionMechanism.ADDITIVE,
        effect="Additive GI and renal toxicity; no additional benefit",
        effect_es="Toxicidad GI y renal aditiva; sin beneficio adicional",
        recommendation="NEVER use two NSAIDs together",
        recommendation_es="NUNCA usar dos AINEs juntos",
        evidence_level="high",
    ),
    DrugInteraction(
        id="metamizol_otros_aines",
        drug_a="Metamizol",
        drug_b="Otros AINEs",
        severity=InteractionSeverity.MODERATE,
        mechanism=InteractionMechanism.ADDITIVE,
        effect="Additive GI toxicity risk",
        effect_es="Riesgo de toxicidad GI aditiva",
        recommendation="Avoid combining; alternate instead",
        recommendation_es="Evitar combinar; alternar en su lugar",
        evidence_level="moderate",
    ),
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_interactions_for_drug(drug_name: str) -> list[DrugInteraction]:
    """Get all interactions involving a specific drug.

    Args:
        drug_name: Drug name to search for

    Returns:
        List of interactions involving this drug
    """
    drug_lower = drug_name.lower()
    return [
        interaction
        for interaction in DRUG_INTERACTIONS_CATALOG
        if interaction.is_active
        and (
            drug_lower in interaction.drug_a.lower()
            or drug_lower in interaction.drug_b.lower()
        )
    ]


def get_interaction_between(drug_a: str, drug_b: str) -> DrugInteraction | None:
    """Check for interaction between two specific drugs.

    Args:
        drug_a: First drug name
        drug_b: Second drug name

    Returns:
        Interaction if found, None otherwise
    """
    a_lower = drug_a.lower()
    b_lower = drug_b.lower()

    for interaction in DRUG_INTERACTIONS_CATALOG:
        if not interaction.is_active:
            continue

        # Check both directions
        if (
            (a_lower in interaction.drug_a.lower() or interaction.drug_a.lower() in a_lower)
            and (b_lower in interaction.drug_b.lower() or interaction.drug_b.lower() in b_lower)
        ) or (
            (b_lower in interaction.drug_a.lower() or interaction.drug_a.lower() in b_lower)
            and (a_lower in interaction.drug_b.lower() or interaction.drug_b.lower() in a_lower)
        ):
            return interaction

    return None


def get_contraindicated_interactions() -> list[DrugInteraction]:
    """Get all contraindicated interactions.

    Returns:
        List of contraindicated interactions
    """
    return [
        interaction
        for interaction in DRUG_INTERACTIONS_CATALOG
        if interaction.is_active
        and interaction.severity == InteractionSeverity.CONTRAINDICATED
    ]


def get_major_interactions() -> list[DrugInteraction]:
    """Get all major interactions.

    Returns:
        List of major interactions
    """
    return [
        interaction
        for interaction in DRUG_INTERACTIONS_CATALOG
        if interaction.is_active
        and interaction.severity == InteractionSeverity.MAJOR
    ]
