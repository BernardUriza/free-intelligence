"""fi_core.cognitive.domains — specialty domains for the cognitive flow.

The urgency/triage algorithm (:mod:`fi_core.cognitive.urgency`) is
specialty-agnostic; the *vocabularies* are what make it cardiology, psychiatry,
etc. A :class:`ClinicalDomain` bundles one specialty's vocabularies so a runner
picks a domain instead of hand-wiring five frozensets. One core, many domains.

    from fi_core.cognitive import PSYCHIATRY, PatientContext
    clf = PSYCHIATRY.urgency_classifier()
    score = clf.classify(PatientContext(symptoms=["ideación suicida", "plan suicida"]))
    print(score.level)  # UrgencyLevel.CRITICAL

Vocabularies are NON-EXHAUSTIVE starting points, tuned to the language the runner
speaks: cardiology terms are English (the original Redux-Claude flow); psychiatry
terms are Spanish, matching ALICE's clinical reflection layer. Substring matching
is case-insensitive, so feed the LLM-extracted clinical indicators (e.g.
"ideación suicida pasiva"), not raw colloquial text. Override per deployment.
"""

from __future__ import annotations

from dataclasses import dataclass

from .urgency import (
    DEFAULT_CRITICAL_PATTERNS,
    DEFAULT_CRITICAL_SYMPTOMS,
    DEFAULT_HIGH_RISK_CONDITIONS,
    DEFAULT_HIGH_SYMPTOMS,
    DEFAULT_MEDIUM_SYMPTOMS,
    UrgencyClassifier,
)

# --- Psychiatry / mental-health vocabularies (Spanish, NON-EXHAUSTIVE) -------
#: Acute risk → gravity 9. Matched against BOTH the LLM-extracted indicators and
#: the patient's own words, so it includes clinical terms AND how people actually
#: phrase a crisis ("hacerme daño", "no quiero seguir viviendo").
PSYCH_CRITICAL_SYMPTOMS: frozenset[str] = frozenset({
    # clinical phrasing (LLM indicators)
    "ideación suicida activa", "plan suicida", "intento de suicidio",
    "intento suicida", "autolesión activa", "ideación homicida",
    "alucinaciones de mando", "psicosis aguda", "riesgo inminente",
    "riesgo agudo", "riesgo suicida", "medios letales",
    # colloquial phrasing (patient's own words)
    "hacerme daño", "quiero morir", "quitarme la vida",
    "matarme", "no quiero seguir viviendo", "no quiero vivir", "lastimarme",
})
#: Serious but not imminent → gravity 7.
PSYCH_HIGH_SYMPTOMS: frozenset[str] = frozenset({
    # clinical phrasing
    "ideación suicida pasiva", "ideación suicida", "ideación de muerte",
    "desesperanza", "autolesión", "psicosis", "ideación paranoide",
    "ideación persecutoria", "disociación", "episodio maníaco",
    "abstinencia", "alucinaciones", "delirio",
    # colloquial passive-ideation markers (patient's own words)
    "mejor sin mí", "no le veo sentido", "para qué seguir", "ya no quiero estar",
})
#: Distress warranting attention → gravity 5.
PSYCH_MEDIUM_SYMPTOMS: frozenset[str] = frozenset({
    "ansiedad severa", "ataque de pánico", "crisis de ansiedad", "insomnio",
    "ánimo deprimido", "anhedonia", "pensamientos intrusivos", "duelo",
    "aislamiento", "irritabilidad",
})
#: Patterns that override urgency to CRITICAL regardless of score — unambiguous
#: crisis markers, clinical and colloquial.
PSYCH_CRITICAL_PATTERNS: frozenset[str] = frozenset({
    "plan suicida", "intento de suicidio", "intento suicida",
    "autolesión activa", "ideación homicida", "alucinaciones de mando",
    "riesgo agudo", "riesgo suicida", "riesgo inminente",
    "hacerme daño", "quitarme la vida", "matarme",
    "no quiero seguir viviendo", "quiero morir",
})
#: Comorbidities / history that add gravity (+0.5 each).
PSYCH_HIGH_RISK_CONDITIONS: frozenset[str] = frozenset({
    "intento de suicidio previo", "trastorno por uso de sustancias",
    "aislamiento social", "duelo reciente", "hospitalización psiquiátrica previa",
    "trauma", "abuso",
})


@dataclass(frozen=True)
class ClinicalDomain:
    """A specialty's urgency vocabularies, ready to build a classifier.

    Adding a domain = one ClinicalDomain instance; the triage algorithm is shared.
    """

    name: str
    critical_symptoms: frozenset[str]
    high_symptoms: frozenset[str]
    medium_symptoms: frozenset[str]
    critical_patterns: frozenset[str]
    high_risk_conditions: frozenset[str]

    def urgency_classifier(self) -> UrgencyClassifier:
        """An :class:`UrgencyClassifier` wired with this domain's vocabularies."""
        return UrgencyClassifier(
            critical_symptoms=self.critical_symptoms,
            high_symptoms=self.high_symptoms,
            medium_symptoms=self.medium_symptoms,
            critical_patterns=self.critical_patterns,
            high_risk_conditions=self.high_risk_conditions,
        )


#: Cardiology — the original Redux-Claude defaults (English).
CARDIOLOGY = ClinicalDomain(
    name="cardiology",
    critical_symptoms=DEFAULT_CRITICAL_SYMPTOMS,
    high_symptoms=DEFAULT_HIGH_SYMPTOMS,
    medium_symptoms=DEFAULT_MEDIUM_SYMPTOMS,
    critical_patterns=DEFAULT_CRITICAL_PATTERNS,
    high_risk_conditions=DEFAULT_HIGH_RISK_CONDITIONS,
)
#: Psychiatry / mental health (Spanish) — ALICE's clinical reflection domain.
PSYCHIATRY = ClinicalDomain(
    name="psychiatry",
    critical_symptoms=PSYCH_CRITICAL_SYMPTOMS,
    high_symptoms=PSYCH_HIGH_SYMPTOMS,
    medium_symptoms=PSYCH_MEDIUM_SYMPTOMS,
    critical_patterns=PSYCH_CRITICAL_PATTERNS,
    high_risk_conditions=PSYCH_HIGH_RISK_CONDITIONS,
)

#: Registry — look a domain up by name.
DOMAINS: dict[str, ClinicalDomain] = {d.name: d for d in (CARDIOLOGY, PSYCHIATRY)}
