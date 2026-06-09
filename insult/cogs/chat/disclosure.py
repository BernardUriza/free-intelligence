"""Pre-LLM disclosure detection — regex-based scanner for important user disclosures.

Runs BEFORE the LLM call to detect sensitive disclosures (health, crisis,
identity, abuse, grief) so the bot can adjust its behavioral preset and
never miss critical context. Zero LLM cost — pure regex.
"""

import re
from dataclasses import dataclass, field

import structlog

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class DisclosureResult:
    """Result of scanning a user message for important disclosures."""

    detected: bool
    category: str  # "health", "crisis", "identity", "abuse", "grief", "none"
    severity: int  # 0-5 (0=none, 1=mild mention, 3=significant, 5=acute crisis)
    signals: list[str] = field(default_factory=list)
    should_override_preset: bool = False  # True if severity >= 3


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

# Each entry: (compiled regex, description, severity)
_PatternEntry = tuple[re.Pattern[str], str, int]

_HEALTH_PATTERNS: list[_PatternEntry] = [
    # Diagnosis mentions
    (
        re.compile(r"(?i)\bme\s+diagnosticaron\b"),
        "diagnosis_mention_es",
        3,
    ),
    (
        re.compile(r"(?i)\bI\s+was\s+diagnosed\b"),
        "diagnosis_mention_en",
        3,
    ),
    (
        re.compile(r"(?i)\btengo\s+(?:depresion|ansiedad|esquizofrenia|trastorno)\b"),
        "condition_self_report_es",
        2,
    ),
    (
        re.compile(r"(?i)\bI\s+have\s+(?:depression|anxiety|schizophrenia|disorder)\b"),
        "condition_self_report_en",
        2,
    ),
    # Medication
    (
        re.compile(r"(?i)\btomo\s+\w+"),
        "medication_intake_es",
        2,
    ),
    (
        re.compile(
            r"(?i)\b(?:sertralina|quetiapina|fluoxetina|clonazepam|alprazolam|"
            r"escitalopram|venlafaxina|litio|risperidona|olanzapina|paroxetina|"
            r"duloxetina|lamotrigina|aripiprazol|lorazepam|diazepam)\b"
        ),
        "specific_medication",
        2,
    ),
    (
        re.compile(r"(?i)\b(?:antidepresivos?|antipsic[oó]ticos?|ansiol[ií]ticos?)\b"),
        "medication_class_es",
        2,
    ),
    (
        re.compile(r"(?i)\b(?:antidepressants?|antipsychotics?|anxiolytics?)\b"),
        "medication_class_en",
        2,
    ),
    (
        re.compile(r"(?i)\bARVs?\b"),
        "arv_medication",
        2,
    ),
    (
        re.compile(r"(?i)\b(?:medicamento|pastillas|dosis)\b"),
        "medication_generic_es",
        2,
    ),
    # Chronic conditions
    (
        re.compile(r"(?i)\b(?:VIH|HIV)\b"),
        "hiv_mention",
        3,
    ),
    (
        re.compile(r"(?i)\b(?:diabetes|c[aá]ncer|epilepsia|epilepsy)\b"),
        "chronic_condition",
        2,
    ),
    (
        re.compile(r"(?i)\bbipolar\b"),
        "bipolar_mention",
        2,
    ),
    (
        re.compile(r"(?i)\b(?:TDAH|ADHD)\b"),
        "adhd_mention",
        2,
    ),
]

_CRISIS_PATTERNS: list[_PatternEntry] = [
    # Suicidal ideation
    (
        re.compile(r"(?i)\bme\s+quiero\s+morir\b"),
        "suicidal_ideation_es",
        5,
    ),
    (
        re.compile(r"(?i)\bkill\s+myself\b"),
        "suicidal_ideation_en",
        5,
    ),
    (
        re.compile(r"(?i)\bsuicid"),
        "suicide_mention",
        5,
    ),
    (
        re.compile(r"(?i)\bno\s+quiero\s+vivir\b"),
        "suicidal_ideation_es_2",
        5,
    ),
    (
        re.compile(r"(?i)\bya\s+no\s+puedo\s+m[aá]s\b"),
        "acute_despair_es",
        4,
    ),
    # Self-harm
    (
        re.compile(r"(?i)\bme\s+corto\b"),
        "self_harm_cutting_es",
        4,
    ),
    (
        re.compile(r"(?i)\bme\s+hago\s+da[nñ]o\b"),
        "self_harm_es",
        4,
    ),
    (
        re.compile(r"(?i)\bcutting\b"),
        "self_harm_cutting_en",
        4,
    ),
    (
        re.compile(r"(?i)\bautolesi[oó]n\b"),
        "self_harm_autolesion",
        4,
    ),
    # Acute distress
    (
        re.compile(r"(?i)\binternamiento\b"),
        "hospitalization_es",
        4,
    ),
    (
        re.compile(r"(?i)\bhospitalizaci[oó]n\b"),
        "hospitalization_es_2",
        4,
    ),
    (
        re.compile(r"(?i)\bemergencia\b"),
        "emergency_es",
        4,
    ),
    (
        re.compile(r"(?i)\bcrisis\b"),
        "crisis_mention",
        4,
    ),
    (
        re.compile(r"(?i)\bal\s+borde\b"),
        "on_the_edge_es",
        4,
    ),
    # Panic
    (
        re.compile(r"(?i)\bataque\s+de\s+p[aá]nico\b"),
        "panic_attack_es",
        4,
    ),
    (
        re.compile(r"(?i)\bpanic\s+attack\b"),
        "panic_attack_en",
        4,
    ),
    (
        re.compile(r"(?i)\bno\s+puedo\s+respirar\b"),
        "cant_breathe_es",
        4,
    ),
]

_IDENTITY_PATTERNS: list[_PatternEntry] = [
    # Coming out
    (
        re.compile(r"(?i)\bsoy\s+(?:gay|trans|bisexual|no\s+binari[oa]|lesbian[oa]|queer|pansexual)\b"),
        "coming_out_es",
        2,
    ),
    (
        re.compile(r"(?i)\bI'?m\s+(?:gay|trans|bisexual|nonbinary|non-binary|lesbian|queer|pansexual)\b"),
        "coming_out_en",
        2,
    ),
    (
        re.compile(r"(?i)\bsal[ií]\s+del\s+cl[oó]set\b"),
        "came_out_closet_es",
        2,
    ),
    # Gender identity
    (
        re.compile(r"(?i)\bmi\s+identidad\s+de\s+g[eé]nero\b"),
        "gender_identity_es",
        2,
    ),
    (
        re.compile(r"(?i)\btransici[oó]n\b"),
        "transition_mention",
        2,
    ),
    (
        re.compile(r"(?i)\bpronombres\b"),
        "pronouns_es",
        2,
    ),
]

_ABUSE_PATTERNS: list[_PatternEntry] = [
    # Violence
    (
        re.compile(r"(?i)\bme\s+golpea\b"),
        "physical_violence_es",
        4,
    ),
    (
        re.compile(r"(?i)\bme\s+pega\b"),
        "physical_violence_es_2",
        3,
    ),
    (
        re.compile(r"(?i)\babuso\b"),
        "abuse_mention_es",
        3,
    ),
    (
        re.compile(r"(?i)\bviolencia\b"),
        "violence_mention_es",
        3,
    ),
    (
        re.compile(r"(?i)\bacoso\b"),
        "harassment_es",
        3,
    ),
    (
        re.compile(r"(?i)\bme\s+violan?\b"),
        "sexual_violence_es",
        4,
    ),
    # Domestic
    (
        re.compile(r"(?i)\bmi\s+pareja\s+me\b"),
        "domestic_partner_es",
        3,
    ),
    (
        re.compile(r"(?i)\bviolencia\s+dom[eé]stica\b"),
        "domestic_violence_es",
        4,
    ),
    (
        re.compile(r"(?i)\bme\s+amenaza\b"),
        "threat_es",
        3,
    ),
]

_GRIEF_PATTERNS: list[_PatternEntry] = [
    # Loss
    (
        re.compile(r"(?i)\bse\s+muri[oó]\b"),
        "death_es",
        3,
    ),
    (
        re.compile(r"(?i)\bfalleci[oó]\b"),
        "death_formal_es",
        3,
    ),
    (
        re.compile(r"(?i)\bdied\b"),
        "death_en",
        2,
    ),
    (
        re.compile(r"(?i)\bperd[ií]\s+a\b"),
        "loss_es",
        2,
    ),
    (
        re.compile(r"(?i)\bduelo\b"),
        "grief_es",
        2,
    ),
    (
        re.compile(r"(?i)\bluto\b"),
        "mourning_es",
        2,
    ),
    # Recent loss (higher severity)
    (
        re.compile(r"(?i)\bayer\s+(?:se\s+)?muri[oó]\b"),
        "recent_death_es",
        3,
    ),
    (
        re.compile(r"(?i)\bacaba\s+de\s+morir\b"),
        "just_died_es",
        3,
    ),
]

# All categories mapped for iteration
_ALL_CATEGORIES: dict[str, list[_PatternEntry]] = {
    "crisis": _CRISIS_PATTERNS,
    "abuse": _ABUSE_PATTERNS,
    "health": _HEALTH_PATTERNS,
    "grief": _GRIEF_PATTERNS,
    "identity": _IDENTITY_PATTERNS,
}


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


def scan_disclosure(text: str) -> DisclosureResult:
    """Scan user message for important disclosures before LLM generation.

    Checks all pattern categories against the text. Returns the category
    with the highest severity match. If severity >= 3, flags that the
    behavioral preset should be overridden to RESPECTFUL_SERIOUS.
    """
    best_category = "none"
    best_severity = 0
    all_signals: list[str] = []

    for category, patterns in _ALL_CATEGORIES.items():
        for regex, description, severity in patterns:
            if regex.search(text):
                all_signals.append(description)
                if severity > best_severity:
                    best_severity = severity
                    best_category = category

    if not all_signals:
        return DisclosureResult(
            detected=False,
            category="none",
            severity=0,
            signals=[],
            should_override_preset=False,
        )

    should_override = best_severity >= 3

    log.info(
        "disclosure_detected",
        category=best_category,
        severity=best_severity,
        signal_count=len(all_signals),
        should_override_preset=should_override,
    )

    return DisclosureResult(
        detected=True,
        category=best_category,
        severity=best_severity,
        signals=all_signals,
        should_override_preset=should_override,
    )
