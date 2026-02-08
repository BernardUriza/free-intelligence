"""Allergen Catalog - Common Drug Allergens in Mexico.

Database of allergens with their related medications for
cross-reference during prescription safety checks.

Based on:
- Mexican pharmaceutical guidelines
- Common drug allergies in clinical practice
- Cross-reactivity data from pharmacology literature

Author: Bernard Uriza Orozco
Created: 2025-12-28
Card: FI-RX-009
"""

from backend.domain.prescription.models.allergy import AllergenEntry, AllergenType, AllergySeverity

# ============================================================================
# ALLERGEN CATALOG
# ============================================================================
# Organized by allergen type and clinical importance

ALLERGEN_CATALOG: list[AllergenEntry] = [
    # ========================================================================
    # BETA-LACTAM ANTIBIOTICS (Most common drug allergies)
    # ========================================================================
    AllergenEntry(
        id="penicillin",
        name="Penicillin",
        name_es="Penicilina",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Penicilina",
            "Penicilina V",
            "Penicilina G",
            "Amoxicilina",
            "Ampicilina",
            "Dicloxacilina",
            "Oxacilina",
            "Piperacilina",
            "Amoxicilina/Clavulanato",
            "Ampicilina/Sulbactam",
        ],
        cross_reactive=["cefalosporinas", "carbapenems"],
        severity=AllergySeverity.SEVERE,
        notes="Penicillin allergy affects 10% of population. Risk of anaphylaxis.",
        notes_es="Alergia a penicilina afecta 10% de población. Riesgo de anafilaxia.",
    ),
    AllergenEntry(
        id="cephalosporins",
        name="Cephalosporins",
        name_es="Cefalosporinas",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Cefalexina",
            "Cefadroxilo",
            "Cefuroxima",
            "Cefaclor",
            "Ceftriaxona",
            "Cefotaxima",
            "Ceftazidima",
            "Cefepima",
            "Cefixima",
            "Cefalotina",
        ],
        cross_reactive=["penicillin"],
        severity=AllergySeverity.SEVERE,
        notes="10% cross-reactivity with penicillins, especially 1st generation.",
        notes_es="10% reactividad cruzada con penicilinas, especialmente 1ra generación.",
    ),
    AllergenEntry(
        id="carbapenems",
        name="Carbapenems",
        name_es="Carbapenémicos",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Imipenem",
            "Meropenem",
            "Ertapenem",
            "Doripenem",
        ],
        cross_reactive=["penicillin"],
        severity=AllergySeverity.SEVERE,
        notes="Less cross-reactivity than cephalosporins but still significant risk.",
        notes_es="Menor reactividad cruzada que cefalosporinas pero riesgo significativo.",
    ),
    # ========================================================================
    # SULFONAMIDES
    # ========================================================================
    AllergenEntry(
        id="sulfonamides",
        name="Sulfonamides",
        name_es="Sulfonamidas",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Sulfametoxazol",
            "Trimetoprim/Sulfametoxazol",
            "Sulfasalazina",
            "Sulfadiazina",
            "Sulfacetamida",
            # Sulfonamide-related diuretics
            "Furosemida",
            "Hidroclorotiazida",
            "Clortalidona",
            "Indapamida",
            # Sulfonamide-related oral hypoglycemics
            "Glibenclamida",
            "Glipizida",
            "Glimepirida",
        ],
        cross_reactive=[],
        severity=AllergySeverity.SEVERE,
        notes="Stevens-Johnson syndrome risk. Cross-reactivity with sulfonamide diuretics controversial.",
        notes_es="Riesgo de síndrome Stevens-Johnson. Reactividad cruzada con diuréticos sulfonamida controversial.",
    ),
    # ========================================================================
    # NSAIDs
    # ========================================================================
    AllergenEntry(
        id="nsaids",
        name="NSAIDs",
        name_es="AINEs",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Aspirina",
            "Ibuprofeno",
            "Naproxeno",
            "Diclofenaco",
            "Ketorolaco",
            "Piroxicam",
            "Meloxicam",
            "Indometacina",
            "Ketoprofeno",
            "Nimesulida",
            "Celecoxib",
            "Etoricoxib",
        ],
        cross_reactive=["aspirin"],
        severity=AllergySeverity.MODERATE,
        notes="Cross-reactivity common among COX inhibitors. Bronchospasm in asthmatics.",
        notes_es="Reactividad cruzada común entre inhibidores COX. Broncoespasmo en asmáticos.",
    ),
    AllergenEntry(
        id="aspirin",
        name="Aspirin",
        name_es="Aspirina",
        allergen_type=AllergenType.SPECIFIC_DRUG,
        related_medications=[
            "Aspirina",
            "Ácido acetilsalicílico",
        ],
        cross_reactive=["nsaids"],
        severity=AllergySeverity.MODERATE,
        notes="Aspirin-exacerbated respiratory disease (AERD). Avoid all NSAIDs.",
        notes_es="Enfermedad respiratoria exacerbada por aspirina. Evitar todos los AINEs.",
    ),
    # ========================================================================
    # OPIOIDS
    # ========================================================================
    AllergenEntry(
        id="morphine",
        name="Morphine",
        name_es="Morfina",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Morfina",
            "Codeína",
            "Hidrocodona",
            "Oxicodona",
            "Hidromorfona",
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="Often histamine release, not true allergy. Consider synthetic opioids.",
        notes_es="Frecuentemente liberación de histamina, no alergia verdadera. Considerar opioides sintéticos.",
    ),
    AllergenEntry(
        id="codeine",
        name="Codeine",
        name_es="Codeína",
        allergen_type=AllergenType.SPECIFIC_DRUG,
        related_medications=[
            "Codeína",
            "Paracetamol con Codeína",
            "Diclofenaco con Codeína",
        ],
        cross_reactive=["morphine"],
        severity=AllergySeverity.MODERATE,
        notes="Cross-reactivity with morphine derivatives.",
        notes_es="Reactividad cruzada con derivados de morfina.",
    ),
    # ========================================================================
    # LOCAL ANESTHETICS
    # ========================================================================
    AllergenEntry(
        id="local_anesthetics_amide",
        name="Amide Local Anesthetics",
        name_es="Anestésicos Locales Amida",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Lidocaína",
            "Mepivacaína",
            "Bupivacaína",
            "Ropivacaína",
            "Prilocaína",
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="True allergy rare. Usually reaction to epinephrine or preservatives.",
        notes_es="Alergia verdadera rara. Usualmente reacción a epinefrina o conservadores.",
    ),
    AllergenEntry(
        id="local_anesthetics_ester",
        name="Ester Local Anesthetics",
        name_es="Anestésicos Locales Éster",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Procaína",
            "Tetracaína",
            "Benzocaína",
            "Cocaína",
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="Cross-react with PABA. More allergenic than amide class.",
        notes_es="Reactividad cruzada con PABA. Más alergénicos que clase amida.",
    ),
    # ========================================================================
    # CONTRAST AGENTS
    # ========================================================================
    AllergenEntry(
        id="iodine_contrast",
        name="Iodine Contrast",
        name_es="Contraste Yodado",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Iopamidol",
            "Iohexol",
            "Ioversol",
            "Iopromida",
            "Diatrizoato",
        ],
        cross_reactive=[],
        severity=AllergySeverity.SEVERE,
        notes="Not true iodine allergy. Premedication may allow safe use.",
        notes_es="No es alergia verdadera al yodo. Premedicación puede permitir uso seguro.",
    ),
    # ========================================================================
    # ANTIEPILEPTICS
    # ========================================================================
    AllergenEntry(
        id="anticonvulsants",
        name="Aromatic Anticonvulsants",
        name_es="Anticonvulsivantes Aromáticos",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Fenitoína",
            "Carbamazepina",
            "Oxcarbazepina",
            "Fenobarbital",
            "Primidona",
            "Lamotrigina",
        ],
        cross_reactive=[],
        severity=AllergySeverity.SEVERE,
        notes="Risk of Stevens-Johnson/TEN. HLA-B*1502 testing recommended in Asian populations.",
        notes_es="Riesgo de Stevens-Johnson/NET. Prueba HLA-B*1502 recomendada en poblaciones asiáticas.",
    ),
    # ========================================================================
    # ANTIBIOTICS - OTHER
    # ========================================================================
    AllergenEntry(
        id="fluoroquinolones",
        name="Fluoroquinolones",
        name_es="Fluoroquinolonas",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Ciprofloxacino",
            "Levofloxacino",
            "Moxifloxacino",
            "Norfloxacino",
            "Ofloxacino",
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="Phototoxicity and tendinitis common. True allergy less common.",
        notes_es="Fototoxicidad y tendinitis comunes. Alergia verdadera menos común.",
    ),
    AllergenEntry(
        id="macrolides",
        name="Macrolides",
        name_es="Macrólidos",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Azitromicina",
            "Claritromicina",
            "Eritromicina",
            "Roxitromicina",
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="GI side effects common, true allergy uncommon.",
        notes_es="Efectos adversos GI comunes, alergia verdadera poco común.",
    ),
    AllergenEntry(
        id="tetracyclines",
        name="Tetracyclines",
        name_es="Tetraciclinas",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Doxiciclina",
            "Tetraciclina",
            "Minociclina",
            "Tigeciclina",
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="Photosensitivity common. True allergy rare.",
        notes_es="Fotosensibilidad común. Alergia verdadera rara.",
    ),
    AllergenEntry(
        id="aminoglycosides",
        name="Aminoglycosides",
        name_es="Aminoglucósidos",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Gentamicina",
            "Amikacina",
            "Tobramicina",
            "Estreptomicina",
            "Neomicina",
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="Nephrotoxicity and ototoxicity main concerns. Allergy uncommon.",
        notes_es="Nefrotoxicidad y ototoxicidad principales preocupaciones. Alergia poco común.",
    ),
    AllergenEntry(
        id="vancomycin",
        name="Vancomycin",
        name_es="Vancomicina",
        allergen_type=AllergenType.SPECIFIC_DRUG,
        related_medications=[
            "Vancomicina",
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="Red man syndrome is histamine release, not allergy. Slow infusion helps.",
        notes_es="Síndrome del hombre rojo es liberación de histamina, no alergia. Infusión lenta ayuda.",
    ),
    # ========================================================================
    # ACE INHIBITORS
    # ========================================================================
    AllergenEntry(
        id="ace_inhibitors",
        name="ACE Inhibitors",
        name_es="IECAs",
        allergen_type=AllergenType.DRUG_CLASS,
        related_medications=[
            "Enalapril",
            "Lisinopril",
            "Captopril",
            "Ramipril",
            "Perindopril",
            "Quinapril",
            "Benazepril",
            "Fosinopril",
        ],
        cross_reactive=[],
        severity=AllergySeverity.SEVERE,
        notes="Angioedema risk (0.1-0.5%). Can occur years after starting. Contraindicated if history.",
        notes_es="Riesgo de angioedema (0.1-0.5%). Puede ocurrir años después de iniciar. Contraindicado si antecedente.",
    ),
    # ========================================================================
    # EXCIPIENTS AND OTHER
    # ========================================================================
    AllergenEntry(
        id="latex",
        name="Latex",
        name_es="Látex",
        allergen_type=AllergenType.EXCIPIENT,
        related_medications=[
            # Vial stoppers may contain latex
            "Insulina (viales)",
            "Heparina (viales)",
        ],
        cross_reactive=["banana", "avocado", "kiwi", "chestnut"],
        severity=AllergySeverity.SEVERE,
        notes="Cross-reactivity with certain fruits (banana, avocado, kiwi).",
        notes_es="Reactividad cruzada con ciertas frutas (plátano, aguacate, kiwi).",
    ),
    AllergenEntry(
        id="egg",
        name="Egg",
        name_es="Huevo",
        allergen_type=AllergenType.FOOD,
        related_medications=[
            # Vaccines grown in eggs
            "Vacuna Influenza",
            "Vacuna Fiebre Amarilla",
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="Most flu vaccines safe even with egg allergy. Yellow fever vaccine contraindicated.",
        notes_es="Mayoría de vacunas influenza seguras aún con alergia a huevo. Vacuna fiebre amarilla contraindicada.",
    ),
    AllergenEntry(
        id="shellfish",
        name="Shellfish",
        name_es="Mariscos",
        allergen_type=AllergenType.FOOD,
        related_medications=[
            "Glucosamina",  # Often derived from shellfish
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="Glucosamine from shellfish source should be avoided. Synthetic alternatives exist.",
        notes_es="Glucosamina de fuente marina debe evitarse. Existen alternativas sintéticas.",
    ),
    AllergenEntry(
        id="gelatin",
        name="Gelatin",
        name_es="Gelatina",
        allergen_type=AllergenType.EXCIPIENT,
        related_medications=[
            "Cápsulas de gelatina",
            "Vacuna MMR",
            "Vacuna Varicela",
            "Vacuna Zóster",
        ],
        cross_reactive=[],
        severity=AllergySeverity.MODERATE,
        notes="Found in many capsules and vaccines. Vegetarian alternatives available.",
        notes_es="Presente en muchas cápsulas y vacunas. Alternativas vegetarianas disponibles.",
    ),
    AllergenEntry(
        id="peanut",
        name="Peanut",
        name_es="Cacahuate",
        allergen_type=AllergenType.FOOD,
        related_medications=[
            "Progesterona (algunas formulaciones)",
            "Vitamina E (algunas fuentes)",
        ],
        cross_reactive=["soy", "legumes"],
        severity=AllergySeverity.SEVERE,
        notes="Check excipients in formulations. Peanut oil rarely causes reactions.",
        notes_es="Verificar excipientes en formulaciones. Aceite de cacahuate raramente causa reacciones.",
    ),
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_allergen_by_id(allergen_id: str) -> AllergenEntry | None:
    """Get an allergen by ID."""
    for allergen in ALLERGEN_CATALOG:
        if allergen.id == allergen_id:
            return allergen
    return None


def search_allergens(query: str) -> list[AllergenEntry]:
    """Search allergens by name."""
    query_lower = query.lower()
    results = []
    for allergen in ALLERGEN_CATALOG:
        if (
            query_lower in allergen.name.lower()
            or query_lower in allergen.name_es.lower()
            or query_lower in allergen.id.lower()
        ):
            results.append(allergen)
    return results
