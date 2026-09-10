"""fi_core.cognitive.domains — specialty domains for the cognitive flow.

The urgency/triage algorithm (:mod:`fi_core.cognitive.urgency`) is
specialty-agnostic; the *vocabularies* are what make it cardiology, psychiatry,
etc. A :class:`ClinicalDomain` bundles one specialty's vocabularies so a runner
picks a domain instead of hand-wiring five frozensets. One core, many domains.

    from fi_core.cognitive import PSYCHIATRY
    verdict = PSYCHIATRY.assess("ideación suicida, tengo un plan", history=["toma sertralina"])
    print(verdict.level)          # UrgencyLevel.CRITICAL
    print(verdict.acute.matched)  # ('explicit_ideation',) — the groups that explain it
    print(verdict.chronic.matched)  # ('psychiatric_medication',)

One call, one verdict, one explanation: :meth:`ClinicalDomain.assess` runs the
vocabulary match, the two weighted axes and the classifier over the SAME text,
so the group names a consumer logs are, by construction, the ones behind the
band — not a parallel reading that happens to agree (discord-bot #54; the two
readings diverged once, 0.29.1). The pieces stay public for a consumer that
only needs one of them.

Vocabularies are NON-EXHAUSTIVE starting points, tuned to the language the runner
speaks: cardiology terms are English (the original Redux-Claude flow); psychiatry
terms are Spanish, matching ALICE's clinical reflection layer. Substring matching
is case-insensitive and accent-insensitive. Feed the classifier LLM-extracted
indicators, or go from raw text with :meth:`ClinicalDomain.match`. Override per
deployment.

Negation is two-tier, by register (declared in :mod:`.urgency`): a clinician's
denial ("niega X", "no presenta X", "ausencia de X") strips its whole clause; a
person's "sin X" / "no X" / "no me X" / "nunca X" negates only the term right
after it, and that term comes back in :attr:`VocabularyHits.denied` instead of
vanishing. So "no tengo ideación suicida" is denied, "no sé, me quiero morir"
is positive, and "estoy sin dormir y me quiero matar" is CRITICAL.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .psychiatry_signals import (
    PSYCH_ACUTE_SIGNALS,
    PSYCH_CHRONIC_SIGNALS,
    PSYCH_EXCLUSIONS,
    PSYCH_RECOVERY_SIGNALS,
)
from .signals import ScoredSignals, SignalGroup, WeightedSignals
from .urgency import (
    DEFAULT_CRITICAL_PATTERNS,
    DEFAULT_CRITICAL_SYMPTOMS,
    DEFAULT_HIGH_RISK_CONDITIONS,
    DEFAULT_HIGH_SYMPTOMS,
    DEFAULT_MEDIUM_SYMPTOMS,
    GravityScore,
    PatientContext,
    UrgencyClassifier,
    UrgencyLevel,
    _fold,
    _negation_shaped_terms,
    scan_terms,
    strip_exclusions,
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
    # first-person proclítico — the patient's most common crisis phrasing in a
    # chat ("me quiero matar"). Only the 3rd-person proclítico was listed, so
    # these scored LOW while "se quiere matar" scored CRITICAL (measured while
    # closing discord-bot #64). "me quiero morir" already fires via "quiero morir".
    "me quiero matar", "me quiero ahorcar", "me quiero suicidar",
    "me quiero quitar la vida",
    "me voy a matar", "me voy a ahorcar", "me voy a suicidar",
    "me voy a quitar la vida",
    # preparatory acts (Alex, discord-bot #55 H1) — tight substrings so the
    # band goes CRITICAL; the looser regex lives in PSYCH_ACUTE_SIGNALS.
    "pastillas listas", "guardando pastillas", "juntando pastillas",
    "carta de despedida", "nota de despedida",
    "ya decidí cómo lo voy a hacer", "ya decidí cómo hacerlo",
    "estoy en el puente", "estoy en la azotea", "estoy en las vías",
    "compré una cuerda", "compré una soga", "compré una pistola",
    "regalé mis cosas", "ya me despedí de todos",
    "dar mi perro a", "dar mi gato a", "dar mi mascota a",
    "ya no te preocupes por mí",
    "the pills ready", "pills ready",
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
    # how a person says "desesperanza" in a chat — the clinical noun above only
    # fires on itself, so "me siento sin esperanza" scored LOW (discord-bot #64).
    # "sin esperanza" carries a negation cue and is shielded by
    # _negation_shaped_terms; "no tengo esperanza" carries none (first-person
    # "no" is never a cue — see the register rule in .urgency).
    "sin esperanza", "no tengo esperanza",
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
    # first-person proclítico (mirrors PSYCH_CRITICAL_SYMPTOMS).
    "me quiero matar", "me quiero ahorcar", "me quiero suicidar",
    "me quiero quitar la vida",
    "me voy a matar", "me voy a ahorcar", "me voy a suicidar",
    "me voy a quitar la vida",
    # preparatory acts (mirrors PSYCH_CRITICAL_SYMPTOMS).
    "pastillas listas", "guardando pastillas", "juntando pastillas",
    "carta de despedida", "nota de despedida",
    "ya decidí cómo lo voy a hacer", "ya decidí cómo hacerlo",
    "estoy en el puente", "estoy en la azotea", "estoy en las vías",
    "compré una cuerda", "compré una soga", "compré una pistola",
    "regalé mis cosas", "ya me despedí de todos",
    "dar mi perro a", "dar mi gato a", "dar mi mascota a",
    "ya no te preocupes por mí",
    "the pills ready", "pills ready",
})
#: Comorbidities / history that add gravity (+0.5 each).
PSYCH_HIGH_RISK_CONDITIONS: frozenset[str] = frozenset({
    "intento de suicidio previo", "trastorno por uso de sustancias",
    "aislamiento social", "duelo reciente", "hospitalización psiquiátrica previa",
    "trauma", "abuso",
    # exposure to a relative's suicide attempt / death (Alex, #55 H2) — the
    # chronic groups exposicion_intento / exposicion_consumado map here.
    "exposición a intento de suicidio", "exposición a suicidio consumado",
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
    #: Entries that appeared ONLY under a local negation ("no me quiero morir",
    #: "sin ideación suicida"). Not a hit — the person is denying it — but not
    #: nothing either: a consumer can log it as a weak signal ("sigue hablando
    #: de morirse"). Excluded from ``__bool__``.
    denied: tuple[str, ...] = ()
    #: Exclusion groups that cut a span before matching — an idiom, a media
    #: topic, someone else's act ("mi hermana intentó suicidarse"). Explains
    #: why a message that looks like a crisis produced no hit.
    excluded: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.symptoms or self.critical_patterns or self.high_risk_conditions)


@dataclass(frozen=True)
class ClinicalVerdict:
    """What :meth:`ClinicalDomain.assess` decided about one message, and every
    reading that decision was built from.

    ``score`` is the band; ``acute`` and ``chronic`` are the weighted axes over
    the message and over the history (``None`` on a domain without that axis —
    cardiology has neither); ``hits`` is the vocabulary match that fed the
    classifier; ``conditions`` are the ``high_risk_conditions`` the history
    contributed, i.e. what ``score.reasons`` of kind ``comorbidity`` came from.

    For a log: ``score.level``, ``score.final_gravity``, the ``kind``/``key``/
    ``weight`` of each reason, and the group NAMES in ``acute.matched`` /
    ``chronic.matched`` / ``denied`` / ``excluded``. ``hits`` and each reason's
    ``term`` carry vocabulary spelling — for a screen, not a log."""

    score: GravityScore
    hits: VocabularyHits
    acute: ScoredSignals | None = None
    chronic: ScoredSignals | None = None
    conditions: tuple[str, ...] = ()

    @property
    def level(self) -> UrgencyLevel:
        return self.score.level


@dataclass(frozen=True)
class ClinicalDomain:
    """A specialty's urgency vocabularies, ready to build a classifier.

    Adding a domain = one ClinicalDomain instance; the triage algorithm is shared.

    The optional WEIGHTED axes (see :mod:`.signals`) exist because flat sets can
    only count, never accumulate: ``chronic_signals`` evaluates the subject's
    long-term record (facts) for a vulnerability CLUSTER, ``acute_signals``
    evaluates the current message for distress NOW, and ``recovery_signals``
    reads the SAME message for the way back. A domain that ships them lets a
    consumer retire its own parallel corpus — one clinical source of truth
    instead of a union.

    The recovery axis is not the acute one inverted. It landed last (Álex,
    discord-bot #55 H4) because the corpus only knew how to climb the ladder:
    145 turns sat in `stability` without a single recovery signal, which is not
    stability but nobody watching the other side.
    """

    name: str
    critical_symptoms: frozenset[str]
    high_symptoms: frozenset[str]
    medium_symptoms: frozenset[str]
    critical_patterns: frozenset[str]
    high_risk_conditions: frozenset[str]
    chronic_signals: WeightedSignals | None = None
    acute_signals: WeightedSignals | None = None
    #: The way BACK, read off the current message. Optional like the others: a
    #: domain without one simply has nothing to say about improvement.
    recovery_signals: WeightedSignals | None = None
    #: Spans that are not about the writer (idiom, topic, someone else's act),
    #: cut before the vocabularies read the text. Declared once as signal
    #: groups; the classifier, ``match`` and the axes all honor them.
    exclusions: tuple[SignalGroup, ...] = ()

    @property
    def chronic_conditions(self) -> dict[str, str]:
        """Chronic group name → the ``high_risk_conditions`` entry it stands for.

        Read off each group's ``category``: a chronic group whose category IS
        one of this domain's conditions is that condition's detector. The
        groups with no counterpart (a named diagnosis, a medication, a
        clinician, a somatic comorbidity) score the chronic axis but never
        reach the band — which is why the map belongs here and not in a
        consumer's dict (discord-bot's ``_GROUP_TO_CONDITION`` until 0.30)."""
        if self.chronic_signals is None:
            return {}
        return {
            g.name: g.category
            for g in self.chronic_signals.groups
            if g.category in self.high_risk_conditions
        }

    def conditions_for(self, groups: Iterable[str]) -> tuple[str, ...]:
        """The ``high_risk_conditions`` a set of chronic group names stands for, sorted."""
        mapping = self.chronic_conditions
        return tuple(sorted({mapping[g] for g in groups if g in mapping}))

    def assess(self, message: str, history: Iterable[str] = ()) -> ClinicalVerdict:
        """One call: the band for ``message`` given ``history``, with every
        reading that produced it.

        ``message`` feeds the vocabulary match (→ ``PatientContext.symptoms``)
        and the acute axis; ``history`` — the subject's accumulated facts, as
        plain texts — feeds the chronic axis, whose matched groups become the
        ``medical_history`` conditions through :attr:`chronic_conditions`.
        Conditions the message itself names are reported in
        ``hits.high_risk_conditions`` and do not add gravity: the message is
        what is happening now, the history is the record (parity with the
        canary's ``crisis_band``; a condition becomes history once it is a
        fact)."""
        texts = [t for t in history if t]
        hits = self.match(message)
        acute = self.acute_signals.score([message]) if self.acute_signals is not None else None
        chronic = self.chronic_signals.score(texts) if self.chronic_signals is not None else None
        conditions = self.conditions_for(chronic.matched) if chronic is not None else ()
        score = self.urgency_classifier().classify(
            PatientContext(symptoms=list(hits.symptoms), medical_history=list(conditions))
        )
        return ClinicalVerdict(score=score, hits=hits, acute=acute, chronic=chronic, conditions=conditions)

    def urgency_classifier(self) -> UrgencyClassifier:
        """An :class:`UrgencyClassifier` wired with this domain's vocabularies."""
        return UrgencyClassifier(
            critical_symptoms=self.critical_symptoms,
            high_symptoms=self.high_symptoms,
            medium_symptoms=self.medium_symptoms,
            critical_patterns=self.critical_patterns,
            high_risk_conditions=self.high_risk_conditions,
            exclusions=self.exclusions,
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
        text, excluded = strip_exclusions(_fold(text), self.exclusions)
        symptoms, denied_symptoms = scan_terms(
            text, self.critical_symptoms | self.high_symptoms | self.medium_symptoms, protected
        )
        patterns, denied_patterns = scan_terms(text, self.critical_patterns, protected)
        conditions, denied_conditions = scan_terms(text, self.high_risk_conditions, protected)
        return VocabularyHits(
            symptoms=symptoms,
            critical_patterns=patterns,
            high_risk_conditions=conditions,
            denied=tuple(sorted(set(denied_symptoms + denied_patterns + denied_conditions))),
            excluded=excluded,
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
    recovery_signals=PSYCH_RECOVERY_SIGNALS,
    exclusions=PSYCH_EXCLUSIONS,
)

#: Registry — look a domain up by name.
DOMAINS: dict[str, ClinicalDomain] = {d.name: d for d in (CARDIOLOGY, PSYCHIATRY)}
