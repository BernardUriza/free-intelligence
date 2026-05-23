"""Urgency / gravity scoring — the triage sub-machine.

Ported faithfully from FLOW.md §4 (Urgency Classification Workflow) of the
Redux-Claude medical flow. Pure, zero-dep, and **explainable**: given a
patient's symptoms + context, it computes a 1-10 gravity score and an
:class:`UrgencyLevel` (LOW/MEDIUM/HIGH/CRITICAL) with the time-to-action band,
and returns the reasons behind the score.

This is decision SUPPORT, not diagnosis. The default symptom/pattern
vocabularies lean cardiology and are a NON-EXHAUSTIVE starting point — pass
your own frozensets to :class:`UrgencyClassifier` to tune for a specialty.

In the consultation state machine this is what the ``TRIAGE`` state runs
(see :mod:`fi_core.cognitive.state_machine`).

    clf = UrgencyClassifier()
    score = clf.classify(PatientContext(
        age=70, gender="male",
        symptoms=["chest pain", "dyspnea"],
        medical_history=["hypertension", "diabetes"],
    ))
    print(score.level, score.final_gravity, score.time_to_action)
    for r in score.reasons:
        print(" -", r)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class UrgencyLevel(str, Enum):
    """Triage urgency tiers (FLOW.md §4 "Urgency Levels")."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class UrgencyBand:
    """A gravity range mapped to a level and a time-to-action."""

    level: UrgencyLevel
    min_gravity: int
    max_gravity: int
    time_to_action: str


#: FLOW.md §4 "Urgency Levels" table.
URGENCY_BANDS: tuple[UrgencyBand, ...] = (
    UrgencyBand(UrgencyLevel.CRITICAL, 9, 10, "immediate (<5 min)"),
    UrgencyBand(UrgencyLevel.HIGH, 7, 8, "urgent (<30 min)"),
    UrgencyBand(UrgencyLevel.MEDIUM, 4, 6, "priority (<2 hours)"),
    UrgencyBand(UrgencyLevel.LOW, 1, 3, "routine (<24 hours)"),
)

# --- Default vocabularies (cardiology-leaning, NON-EXHAUSTIVE) -------------
# Override per specialty via UrgencyClassifier(...). Matching is
# case-insensitive substring, so "acute chest pain" matches "chest pain".

DEFAULT_CRITICAL_SYMPTOMS: frozenset[str] = frozenset({
    "cardiac arrest", "respiratory failure", "severe bleeding",
    "unresponsive", "unconscious", "anaphylaxis", "stroke",
})
DEFAULT_HIGH_SYMPTOMS: frozenset[str] = frozenset({
    "chest pain", "dyspnea", "shortness of breath", "syncope",
    "palpitations", "altered mental status", "severe headache",
    "diaphoresis", "tachycardia",
})
DEFAULT_MEDIUM_SYMPTOMS: frozenset[str] = frozenset({
    "fever", "moderate pain", "persistent vomiting", "dizziness",
    "edema", "fatigue", "nausea",
})
#: "Widow-maker" / critical patterns that override urgency to CRITICAL
#: regardless of the computed score (FLOW.md PATTERN_MATCH -> WIDOW_MAKER).
DEFAULT_CRITICAL_PATTERNS: frozenset[str] = frozenset({
    "acute mi", "myocardial infarction", "stemi", "nstemi",
    "aortic dissection", "pulmonary embolism", "widow maker",
    "cardiac arrest", "ventricular fibrillation",
})
#: Comorbidities that add gravity (FLOW.md high_risk_conditions, +0.5 each).
DEFAULT_HIGH_RISK_CONDITIONS: frozenset[str] = frozenset({
    "diabetes", "hypertension", "copd", "heart disease",
    "immunosuppression",
})


@dataclass
class PatientContext:
    """Inputs to triage. Lists hold free-text terms (any language/casing)."""

    age: int | None = None
    gender: str | None = None  # "male" | "female" | ...
    symptoms: list[str] = field(default_factory=list)
    medical_history: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GravityScore:
    """Result of triage — the score, the tier, and *why*."""

    base_gravity: int
    modifiers: float
    final_gravity: float
    level: UrgencyLevel
    time_to_action: str
    critical_override: bool = False
    reasons: tuple[str, ...] = ()


def _normalize(items: list[str]) -> list[str]:
    return [str(i).strip().lower() for i in items if str(i).strip()]


def _matches(item: str, vocab: frozenset[str]) -> bool:
    return item in vocab or any(term in item for term in vocab)


def band_for_gravity(gravity: float) -> UrgencyBand:
    """Map a (possibly fractional) gravity to a band.

    Uses round-half-up so a high-risk patient sitting on a .5 boundary
    escalates rather than under-triages (defensive, fits clinical intent).
    """
    g = min(10, max(1, int(gravity + 0.5)))
    for band in URGENCY_BANDS:
        if band.min_gravity <= g <= band.max_gravity:
            return band
    return URGENCY_BANDS[-1]


@dataclass
class UrgencyClassifier:
    """Computes a gravity score from a :class:`PatientContext` (FLOW.md §4).

    All vocabularies are injectable so a specialty can tune them without
    forking the algorithm.
    """

    critical_symptoms: frozenset[str] = DEFAULT_CRITICAL_SYMPTOMS
    high_symptoms: frozenset[str] = DEFAULT_HIGH_SYMPTOMS
    medium_symptoms: frozenset[str] = DEFAULT_MEDIUM_SYMPTOMS
    critical_patterns: frozenset[str] = DEFAULT_CRITICAL_PATTERNS
    high_risk_conditions: frozenset[str] = DEFAULT_HIGH_RISK_CONDITIONS

    def base_gravity(self, symptoms: list[str]) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []
        for s in _normalize(symptoms):
            if _matches(s, self.critical_symptoms):
                sev = 9
            elif _matches(s, self.high_symptoms):
                sev = 7
            elif _matches(s, self.medium_symptoms):
                sev = 5
            else:
                sev = 3
            if sev > score:
                score = sev
            reasons.append(f"symptom '{s}' → gravity {sev}")
        return score, reasons

    def modifiers(self, patient: PatientContext) -> tuple[float, list[str]]:
        mod = 0.0
        reasons: list[str] = []
        if patient.age is not None:
            if patient.age > 65:
                mod += 1.0
                reasons.append("age > 65 (+1.0)")
            if patient.age < 1:
                mod += 1.5
                reasons.append("age < 1 (+1.5)")
        history = _normalize(patient.medical_history)
        for cond in sorted(self.high_risk_conditions):
            if any(cond in h for h in history):
                mod += 0.5
                reasons.append(f"comorbidity '{cond}' (+0.5)")
        if (patient.gender or "").lower() == "female" and any(
            "pregnant" in s for s in _normalize(patient.symptoms)
        ):
            mod += 1.0
            reasons.append("pregnancy (+1.0)")
        return mod, reasons

    def critical_pattern(self, patient: PatientContext) -> str | None:
        text = " ".join(_normalize(patient.symptoms + patient.medical_history))
        for pattern in sorted(self.critical_patterns):
            if pattern in text:
                return pattern
        return None

    def classify(self, patient: PatientContext) -> GravityScore:
        """Run triage: critical-pattern override first, else gravity + modifiers."""
        pattern = self.critical_pattern(patient)
        if pattern is not None:
            band = URGENCY_BANDS[0]  # CRITICAL
            return GravityScore(
                base_gravity=10,
                modifiers=0.0,
                final_gravity=10.0,
                level=band.level,
                time_to_action=band.time_to_action,
                critical_override=True,
                reasons=(f"critical pattern '{pattern}' detected → override CRITICAL",),
            )
        base, base_reasons = self.base_gravity(patient.symptoms)
        mod, mod_reasons = self.modifiers(patient)
        final = min(10.0, base + mod)
        band = band_for_gravity(final)
        return GravityScore(
            base_gravity=base,
            modifiers=mod,
            final_gravity=final,
            level=band.level,
            time_to_action=band.time_to_action,
            critical_override=False,
            reasons=tuple(base_reasons + mod_reasons),
        )
