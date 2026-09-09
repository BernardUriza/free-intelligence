"""Negation is two-tier, by REGISTER — pinned (discord-bot #64).

A consumer measured that `"sin"` negated while `"no"` did not, and asked whether
that was policy or accident. It was an accident of a cue list written for
clinical notes: "sin" had clause scope (to the end of the sentence), so in a chat
"estoy sin dormir y me quiero matar" lost its crisis phrase to a preposition three
words earlier, while a first-person "no" never negated at all. This file declares
the model that replaced it, in executable form:

1. CLAUSE cues are the clinician's register ("niega", "no presenta", "no tiene",
   "descarta", "ausencia de"): they announce a denied list and strip to the end
   of the sentence.
2. LOCAL cues are what a person writes ("sin", "no", "no me", "nunca", "ni"):
   they negate only the vocabulary term right after them, never across a comma,
   and the negated term comes back in `VocabularyHits.denied` — a weak signal,
   not nothing.

Also pins the vocabulary half of #64: "sin esperanza" and "no tengo esperanza"
are the colloquial forms of "desesperanza" and score the same tier.
"""

from __future__ import annotations

import pytest
from fi_core.cognitive import PSYCHIATRY, PatientContext

clf = PSYCHIATRY.urgency_classifier()


def band(text: str) -> str:
    return clf.classify(PatientContext(symptoms=[text])).level.value


# --- Vocabulary: the colloquial forms of "desesperanza" ----------------------


@pytest.mark.parametrize(
    "text",
    [
        "me siento sin esperanza",
        "me siento sin esperanza.",
        "SIN ESPERANZA",
        "no tengo esperanza",
        "ya no tengo esperanza de nada",
    ],
)
def test_sin_esperanza_scores_like_desesperanza(text: str):
    assert band("siento desesperanza") == "HIGH"
    assert band(text) == "HIGH", f"{text!r} must score the HIGH tier, like 'desesperanza'"


def test_sin_esperanza_is_found_in_free_text_in_vocabulary_spelling():
    assert "sin esperanza" in PSYCHIATRY.match("la neta me siento sin esperanza").symptoms
    assert "no tengo esperanza" in PSYCHIATRY.match("no tengo esperanza, todo sigue igual").symptoms


def test_a_governing_clinical_denial_still_removes_sin_esperanza():
    """The shield hides the phrase's OWN cue, not the cue that governs it."""
    assert not PSYCHIATRY.match("niega sentirse sin esperanza")
    assert band("el paciente niega sentirse sin esperanza") == "LOW"


def test_sin_esperanza_is_matched_whole_and_ni_continues_the_negation():
    """The term's own "sin" never negates it; the "ni" after it negates what follows."""
    hits = PSYCHIATRY.match("sin esperanza ni ideación suicida")
    assert hits.symptoms == ("sin esperanza",)
    assert hits.denied == ("ideación suicida",)


# --- Tier 1: the clinician's register strips the whole clause ------------------


@pytest.mark.parametrize(
    "text",
    [
        "el paciente no tiene ideación suicida",
        "no presenta ideación suicida",
        "no refiere ideación suicida",
        "niega ideación suicida",
        "descarta ideación suicida",
        "ausencia de ideación suicida",
        "el paciente niega ideación suicida, plan suicida o autolesión activa",
    ],
)
def test_clause_cue_strips_the_denied_list(text: str):
    hits = PSYCHIATRY.match(text)
    assert not hits.symptoms and not hits.denied
    assert band(text) == "LOW"


# --- Tier 2: a person's "sin" / "no" negate ONLY the term right after them ------


@pytest.mark.parametrize(
    ("text", "denied"),
    [
        ("no tengo ideación suicida", "ideación suicida"),
        ("no tengo ideacion suicida", "ideación suicida"),
        ("no siento ideación suicida", "ideación suicida"),
        ("no me quiero morir, solo estoy muy cansado", "quiero morir"),
        ("no quiero morir", "quiero morir"),
        ("nunca me he querido matar y no me quiero matar", "me quiero matar"),
        ("sin ideación suicida ni plan", "ideación suicida"),
        ("me siento sin desesperanza", "desesperanza"),
    ],
)
def test_local_cue_denies_the_term_and_reports_it(text: str, denied: str):
    hits = PSYCHIATRY.match(text)
    assert not hits.symptoms and not hits.critical_patterns
    assert denied in hits.denied
    assert not hits, "denied entries must not make VocabularyHits truthy"
    assert band(text) == "LOW"


def test_clinical_sin_list_with_ni_is_fully_denied():
    hits = PSYCHIATRY.match("paciente sin plan suicida ni autolesión activa")
    assert not hits
    assert {"plan suicida", "autolesión activa"} <= set(hits.denied)


@pytest.mark.parametrize(
    "text",
    [
        "estoy sin dormir y me quiero matar",
        "llevo días sin comer y quiero quitarme la vida",
        "sin ganas de nada, tengo un plan suicida",
        "no sé, me quiero morir",
        "no sé si me quiero morir",
        "no, me quiero morir",
        "nunca me he querido matar, pero hoy me quiero matar",
    ],
)
def test_local_cue_does_not_reach_past_its_term(text: str):
    """The lethal class this model exists for: a chat "sin"/"no" a few words
    before a crisis phrase used to eat it (0.26.0–0.27.0, measured by the
    discord-bot session). Sentence-scope "sin" is gone; comma and distance break
    the local scope."""
    hits = PSYCHIATRY.match(text)
    assert hits.critical_patterns, f"{text!r} must keep its crisis phrase"
    assert clf.classify(PatientContext(symptoms=list(hits.symptoms))).level.value == "CRITICAL"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("no quiero vivir", "CRITICAL"),
        ("no quiero seguir viviendo", "CRITICAL"),
        ("no le veo sentido", "HIGH"),
        ("no tengo esperanza", "HIGH"),
        ("mejor sin mí", "HIGH"),
        ("sin esperanza", "HIGH"),
    ],
)
def test_a_term_spelled_with_a_cue_is_matched_whole(text: str, expected: str):
    """These ARE the vocabulary: their own "no"/"sin" never negates them."""
    assert band(text) == expected
    assert not PSYCHIATRY.match(text).denied


def test_classifier_path_applies_the_same_local_negation():
    """A symptom string handed straight to the classifier is read the same way."""
    assert band("no tengo ideación suicida") == "LOW"
    assert band("estoy sin dormir y me quiero matar") == "CRITICAL"
    score = clf.classify(PatientContext(symptoms=["ansiedad"], medical_history=["sin trauma previo"]))
    assert "comorbidity 'trauma' (+0.5)" not in score.explain()


# --- First-person proclítico crisis phrasing (found while closing #64) -------


@pytest.mark.parametrize(
    "text",
    [
        "me quiero matar",
        "me voy a matar",
        "me quiero ahorcar",
        "me quiero suicidar",
        "me voy a suicidar",
        "me voy a quitar la vida",
        "ya me quiero morir",
        "la neta me quiero matar",
    ],
)
def test_first_person_proclitico_is_critical_like_third_person(text: str):
    """"se quiere matar" was CRITICAL and "me quiero matar" was LOW: only the
    3rd-person proclítico had been listed. The patient's own voice is the most
    common one in a chat, so it must score the same tier."""
    hits = PSYCHIATRY.match(text)
    assert hits.critical_patterns, f"{text!r} must hit a critical pattern"
    assert clf.classify(PatientContext(symptoms=list(hits.symptoms))).level.value == "CRITICAL"
    assert band("se quiere matar") == "CRITICAL"


def test_first_person_proclitico_denied_by_a_clinician_still_strips():
    assert not PSYCHIATRY.match("niega que se quiera matar; no refiere que me quiero matar")


# --- 0.29.1: the two layers read one sentence the same way; history never overrides


def test_vocabulary_and_acute_axis_agree_on_a_local_negation():
    """discord-bot found match() denying "me quiero suicidar" while the acute
    regex, matching "suicidar" clitic + verb after the "no", still fired."""
    text = "no me quiero suicidar, es broma"
    hits = PSYCHIATRY.match(text)
    scored = PSYCHIATRY.acute_signals.score([text])
    assert not hits and "me quiero suicidar" in hits.denied
    assert not scored.matched and scored.denied == ("explicit_ideation",)


@pytest.mark.parametrize(
    "text", ["no me quiero suicidar", "no me voy a matar", "nunca me he querido matar"]
)
def test_clitic_then_verb_after_the_cue_is_negated(text: str):
    assert not PSYCHIATRY.match(text)
    assert not PSYCHIATRY.acute_signals.score([text]).crosses


@pytest.mark.parametrize(
    ("history", "message", "expected"),
    [
        (["intento de suicidio previo"], "hoy comí rico y salí a caminar", "LOW"),
        (["tuvo un intento de suicidio el año pasado"], "", "LOW"),
        (["exposición a intento de suicidio"], "hoy comí rico", "LOW"),
        (["intento de suicidio previo"], "tengo un plan suicida", "CRITICAL"),
    ],
)
def test_history_never_fires_the_critical_override(history: list[str], message: str, expected: str):
    """The override reads what is happening NOW. A past attempt is history: it
    adds +0.5 via modifiers and never makes a quiet message CRITICAL."""
    hits = PSYCHIATRY.match(message)
    score = clf.classify(PatientContext(symptoms=list(hits.symptoms), medical_history=history))
    assert score.level.value == expected
    assert score.critical_override == (expected == "CRITICAL")


def test_history_still_adds_its_comorbidity_modifier():
    score = clf.classify(PatientContext(symptoms=["insomnio"], medical_history=["intento de suicidio previo"]))
    assert score.modifiers == 0.5
    assert "comorbidity 'intento de suicidio previo' (+0.5)" in score.explain()


def test_cardiology_history_is_not_a_present_pattern_either():
    from fi_core.cognitive import CARDIOLOGY

    score = CARDIOLOGY.urgency_classifier().classify(
        PatientContext(symptoms=["fever"], medical_history=["myocardial infarction 2019"])
    )
    assert score.level.value == "MEDIUM" and not score.critical_override
