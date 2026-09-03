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

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache


def _fold(text: str) -> str:
    """Lowercase and drop diacritics so 'ideación' and 'ideacion' are one word.

    Vocabularies are written with accents; a chat user, an ASR transcript or a
    hurried clinician often are not. Both sides of every match go through this,
    so the vocab entry 'autolesión activa' still fires on 'autolesion activa'."""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(ch)
    )


@lru_cache(maxsize=64)
def _fold_vocab(vocab: frozenset[str]) -> frozenset[str]:
    return frozenset(_fold(term) for term in vocab)


# --- Negation handling ------------------------------------------------------
# Substring matching alone over-counts symptoms in negated phrasing — the t13
# eval trap ("el paciente niega ideación suicida, plan suicida o autolesión
# activa") fires CRITICAL because "plan suicida" matches verbatim, even though
# the patient EXPLICITLY DENIES it. Before matching, we strip clauses scoped
# to a negation cue so the denied items don't reach the vocabularies.
#
# Scope rule: cue → next sentence terminator (.;!?) OR opposing conjunction
# (pero, sin embargo, mas, aunque). Comma is intentionally NOT a clause break,
# so a single cue covering a comma-separated list of denied items
# ("niega A, B o C") strips all three. Tradeoff: phrasings like "no refiere
# mejoría, presenta X" lose the un-negated tail unless the writer separates
# with a period or `pero`. Acceptable for clinical notes — perfect coverage
# needs a real negation parser (NegEx / spaCy negspaCy), out of scope for
# fi-core's zero-dep promise.

_NEGATION_CUES: tuple[str, ...] = (
    # Spanish — clinical phrasing
    r"niega", r"niegan", r"neg[oó]",
    r"no\s+presenta", r"no\s+tiene", r"no\s+refiere", r"no\s+manifiesta",
    r"descarta", r"descartan", r"descart[oó]",
    r"ausencia\s+de", r"sin\s+(?!embargo)",
    # English
    r"denies", r"no\s+history\s+of", r"no\s+signs?\s+of",
    r"no\s+evidence\s+of", r"rules?\s+out", r"without",
    r"absence\s+of",
)

_NEGATION_RE = re.compile(
    r"\b(?:" + "|".join(_NEGATION_CUES) + r")\b"
    r"[^.;!?]*?"  # everything up to next strong boundary (lazy)
    r"(?=[.;!?]|\s+(?:pero|sin\s+embargo|mas|aunque)\b|$)",
    re.IGNORECASE,
)


@lru_cache(maxsize=64)
def _negation_shaped_terms(vocab: frozenset[str]) -> tuple[str, ...]:
    """Vocabulary phrases that carry a negation cue INSIDE them.

    'mejor sin mí' and 'sin esperanza' are symptoms, not denials — the 'sin' is
    the symptom's own grammar. Left unprotected, the cue stripper ate exactly
    the phrases the vocabulary existed to catch (0.26.0 regression, found by a
    consumer measuring PSYCHIATRY). Longest first, so a longer phrase is shielded
    before any shorter phrase it contains."""
    folded = _fold_vocab(vocab)
    return tuple(sorted((t for t in folded if _NEGATION_RE.search(t)), key=len, reverse=True))


def _strip_negations(text: str, protected: tuple[str, ...] = ()) -> str:
    """Remove clauses falling under a negation cue's scope.

    ``protected`` phrases (already folded) are shielded from the stripper so a
    symptom spelled with a cue survives, while a real denial that CONTAINS such
    a phrase ("niega sentirse mejor sin mí") is still removed whole — the shield
    only hides the phrase's own cue, not the cue that governs it.

    Returns the text with negated runs replaced by a single space. Idempotent:
    a re-run finds no more cues. See module-level comment for the scope rules
    and the deliberate edge cases."""
    shields: dict[str, str] = {}
    for i, term in enumerate(protected):
        if term in text:
            token = f"\x00{i}\x00"
            shields[token] = term
            text = text.replace(term, token)
    text = _NEGATION_RE.sub(" ", text)
    for token, term in shields.items():
        text = text.replace(token, term)
    return text


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


def _normalize(items: list[str], protected: tuple[str, ...] = ()) -> list[str]:
    # Fold accents and strip negation BEFORE returning so every downstream
    # substring matcher (base_gravity, critical_pattern, modifiers) sees only
    # un-negated, diacritic-free text. Centralizing the pass here avoids missing
    # a site that handles its own normalization in the future.
    return [_strip_negations(_fold(str(i).strip()), protected) for i in items if str(i).strip()]


def _matches(item: str, vocab: frozenset[str]) -> bool:
    folded = _fold_vocab(vocab)
    return item in folded or any(term in item for term in folded)


def find_terms(text: str, vocab: frozenset[str], protected: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Vocabulary entries present in free text, in their ORIGINAL spelling.

    The consumer-side twin of :func:`_matches`: the classifier scores symptoms
    someone already identified, this finds them in what a person actually wrote.
    Same folding (so 'ideacion suicida' finds 'ideación suicida'), same negation
    stripping with the same shielded phrases (so 'niega ideación suicida' finds
    nothing and 'mejor sin mi' finds 'mejor sin mí'). Longest entries first,
    sorted, so the result is stable."""
    haystack = _strip_negations(_fold(text), protected)
    hits = [term for term in vocab if _fold(term) in haystack]
    return tuple(sorted(hits, key=lambda t: (-len(t), t)))


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

    @property
    def _protected(self) -> tuple[str, ...]:
        return _negation_shaped_terms(
            self.critical_symptoms
            | self.high_symptoms
            | self.medium_symptoms
            | self.critical_patterns
            | self.high_risk_conditions
        )

    def base_gravity(self, symptoms: list[str]) -> tuple[int, list[str]]:
        score = 0
        reasons: list[str] = []
        for s in _normalize(symptoms, self._protected):
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
        history = _normalize(patient.medical_history, self._protected)
        for cond in sorted(self.high_risk_conditions):
            if any(_fold(cond) in h for h in history):
                mod += 0.5
                reasons.append(f"comorbidity '{cond}' (+0.5)")
        if (patient.gender or "").lower() == "female" and any(
            "pregnant" in s for s in _normalize(patient.symptoms, self._protected)
        ):
            mod += 1.0
            reasons.append("pregnancy (+1.0)")
        return mod, reasons

    def critical_pattern(self, patient: PatientContext) -> str | None:
        text = " ".join(_normalize(patient.symptoms + patient.medical_history, self._protected))
        for pattern in sorted(self.critical_patterns):
            if _fold(pattern) in text:
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
