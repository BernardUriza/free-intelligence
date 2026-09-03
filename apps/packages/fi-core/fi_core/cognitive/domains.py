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

from .psychiatry_signals import PSYCH_ACUTE_SIGNALS, PSYCH_CHRONIC_SIGNALS
from .signals import WeightedSignals
from .urgency import (
    DEFAULT_CRITICAL_PATTERNS,
    DEFAULT_CRITICAL_SYMPTOMS,
    DEFAULT_HIGH_RISK_CONDITIONS,
    DEFAULT_HIGH_SYMPTOMS,
    DEFAULT_MEDIUM_SYMPTOMS,
    UrgencyClassifier,
    _negation_shaped_terms,
    find_terms,
)

# --- Psychiatry / mental-health vocabularies (Spanish, NON-EXHAUSTIVE) -------
#: Acute risk → gravity 9. Matched against BOTH the LLM-extracted indicators and
#: the patient's own words, so it includes clinical terms AND how people actually
#: phrase a crisis ("hacerme daño", "no quiero seguir viviendo").
#:
#: Both 1st-person ("quitarme la vida", "hacerme daño" — the patient speaks) and
#: infinitive/reflexive/3rd-person variants ("quitarse la vida", "ahorcarse",
#: "se quiere matar" — the clinician describes the patient, or the LLM extracted
#: the indicator in canonical form) belong here. The first eval baseline missed
#: t04 + t07 because only the 1st-person forms were listed.
PSYCH_CRITICAL_SYMPTOMS: frozenset[str] = frozenset({
    # clinical phrasing (LLM indicators)
    "ideación suicida activa", "plan suicida", "intento de suicidio",
    "intento suicida", "autolesión activa", "ideación homicida",
    "alucinaciones de mando", "psicosis aguda", "riesgo inminente",
    "riesgo agudo", "riesgo suicida", "medios letales",
    # 1st-person colloquial phrasing (patient's own words)
    "hacerme daño", "quiero morir", "quitarme la vida",
    "matarme", "no quiero seguir viviendo", "no quiero vivir", "lastimarme",
    # infinitive / reflexive / 3rd-person variants (clinician describing the
    # patient, or LLM extracting a canonical indicator). Substring-matched,
    # so a phrase like "planea ahorcarse esta noche" matches "ahorcarse".
    "quitarse la vida", "ahorcarse", "ahorcamiento", "suicidarse",
    "matarse", "lastimarse", "cortarse las venas", "dispararse",
    "envenenarse", "hacerse daño",
    "quiere morir", "quiere suicidarse", "quiere ahorcarse",
    "quiere matarse", "quiere quitarse la vida",
    "planea suicidarse", "planea ahorcarse", "planea matarse",
    # proclítico reflexive forms — Spanish permits splitting the reflexive
    # pronoun from the verb ("se quiere matar" alongside "quiere matarse").
    # Substring matching only catches the enclítico form, so explicit
    # proclítico variants are needed. Eval case t15 surfaced this gap.
    "se quiere matar", "se quiere ahorcar", "se quiere suicidar",
    "se quiere quitar la vida",
    "se va a matar", "se va a ahorcar", "se va a suicidar",
    "se va a quitar la vida",
    "va a matarse", "va a ahorcarse", "va a suicidarse",
    "intenta matarse", "intenta ahorcarse", "intenta suicidarse",
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
#: crisis markers, clinical and colloquial. Mirrors PSYCH_CRITICAL_SYMPTOMS for
#: the highest-confidence subset (the symptoms-set is matched as substrings to
#: score gravity; this set forces a CRITICAL_OVERRIDE on hit).
PSYCH_CRITICAL_PATTERNS: frozenset[str] = frozenset({
    # clinical phrasing
    "plan suicida", "intento de suicidio", "intento suicida",
    "autolesión activa", "ideación homicida", "alucinaciones de mando",
    "riesgo agudo", "riesgo suicida", "riesgo inminente",
    # 1st-person
    "hacerme daño", "quitarme la vida", "matarme",
    "no quiero seguir viviendo", "quiero morir",
    # infinitive / reflexive / 3rd-person — match equally severe phrasings
    # whether the patient or the clinician produced the text.
    "quitarse la vida", "ahorcarse", "ahorcamiento", "suicidarse",
    "matarse", "cortarse las venas", "dispararse", "envenenarse",
    "hacerse daño",
    "quiere morir", "quiere suicidarse", "quiere ahorcarse",
    "quiere matarse", "quiere quitarse la vida",
    "planea suicidarse", "planea ahorcarse", "planea matarse",
    # proclítico reflexive forms (mirrors PSYCH_CRITICAL_SYMPTOMS).
    "se quiere matar", "se quiere ahorcar", "se quiere suicidar",
    "se quiere quitar la vida",
    "se va a matar", "se va a ahorcar", "se va a suicidar",
    "se va a quitar la vida",
    "va a matarse", "va a ahorcarse", "va a suicidarse",
    "intenta matarse", "intenta ahorcarse", "intenta suicidarse",
})
#: Comorbidities / history that add gravity (+0.5 each).
PSYCH_HIGH_RISK_CONDITIONS: frozenset[str] = frozenset({
    "intento de suicidio previo", "trastorno por uso de sustancias",
    "aislamiento social", "duelo reciente", "hospitalización psiquiátrica previa",
    "trauma", "abuso",
})


@dataclass(frozen=True)
class VocabularyHits:
    """What :meth:`ClinicalDomain.match` found in a text, in vocabulary spelling.

    ``symptoms`` feeds :class:`PatientContext.symptoms` directly; the other two
    are exposed so a consumer can see WHY a message will override or add
    gravity before it ever calls the classifier."""

    symptoms: tuple[str, ...] = ()
    critical_patterns: tuple[str, ...] = ()
    high_risk_conditions: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.symptoms or self.critical_patterns or self.high_risk_conditions)


@dataclass(frozen=True)
class ClinicalDomain:
    """A specialty's urgency vocabularies, ready to build a classifier.

    Adding a domain = one ClinicalDomain instance; the triage algorithm is shared.

    The two optional WEIGHTED axes (see :mod:`.signals`) exist because flat
    sets can only count, never accumulate: ``chronic_signals`` evaluates the
    subject's long-term record (facts) for a vulnerability CLUSTER, and
    ``acute_signals`` evaluates the current message for distress NOW. A domain
    that ships them lets a consumer retire its own parallel corpus — one
    clinical source of truth instead of a union.
    """

    name: str
    critical_symptoms: frozenset[str]
    high_symptoms: frozenset[str]
    medium_symptoms: frozenset[str]
    critical_patterns: frozenset[str]
    high_risk_conditions: frozenset[str]
    chronic_signals: WeightedSignals | None = None
    acute_signals: WeightedSignals | None = None

    def urgency_classifier(self) -> UrgencyClassifier:
        """An :class:`UrgencyClassifier` wired with this domain's vocabularies."""
        return UrgencyClassifier(
            critical_symptoms=self.critical_symptoms,
            high_symptoms=self.high_symptoms,
            medium_symptoms=self.medium_symptoms,
            critical_patterns=self.critical_patterns,
            high_risk_conditions=self.high_risk_conditions,
        )

    def match(self, text: str) -> VocabularyHits:
        """Find this domain's vocabulary inside free text — a person's message, a
        note, a fact — folded and negation-aware exactly like the classifier.

        This is the official way to go from raw text to ``PatientContext``:
        the vocabularies carry accents and a chat user usually does not, so a
        consumer that greps the frozensets by hand loses 'ideacion suicida'
        (fi-core #458). ``match`` folds both sides with the classifier's own
        ``_fold``, strips negated clauses with the same shielded phrases, and
        returns entries in vocabulary spelling::

            hits = PSYCHIATRY.match("ando con ideacion suicida y sin ganas")
            score = PSYCHIATRY.urgency_classifier().classify(
                PatientContext(symptoms=list(hits.symptoms)))
        """
        protected = _negation_shaped_terms(
            self.critical_symptoms
            | self.high_symptoms
            | self.medium_symptoms
            | self.critical_patterns
            | self.high_risk_conditions
        )
        return VocabularyHits(
            symptoms=find_terms(
                text, self.critical_symptoms | self.high_symptoms | self.medium_symptoms, protected
            ),
            critical_patterns=find_terms(text, self.critical_patterns, protected),
            high_risk_conditions=find_terms(text, self.high_risk_conditions, protected),
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
#: Psychiatry / mental health (Spanish flat sets + bilingual weighted axes) —
#: ALICE's clinical reflection domain and, since the weighted axes landed,
#: the single clinical source discord-bot's crisis path consumes.
PSYCHIATRY = ClinicalDomain(
    name="psychiatry",
    critical_symptoms=PSYCH_CRITICAL_SYMPTOMS,
    high_symptoms=PSYCH_HIGH_SYMPTOMS,
    medium_symptoms=PSYCH_MEDIUM_SYMPTOMS,
    critical_patterns=PSYCH_CRITICAL_PATTERNS,
    high_risk_conditions=PSYCH_HIGH_RISK_CONDITIONS,
    chronic_signals=PSYCH_CHRONIC_SIGNALS,
    acute_signals=PSYCH_ACUTE_SIGNALS,
)

#: Registry — look a domain up by name.
DOMAINS: dict[str, ClinicalDomain] = {d.name: d for d in (CARDIOLOGY, PSYCHIATRY)}
