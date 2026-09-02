"""The two ways the PSYCHIATRY vocabulary was blind to its own phrases (0.26.0).

Found by a consumer composing UrgencyClassifier with PSYCHIATRY and feeding it
real phrases: 'mejor sin mí' was IN high_symptoms and still scored 3, because
`sin` is a negation cue and the stripper ate the phrase before matching; and
'ideacion suicida' scored like a banana, because the classifier lowercased but
never folded accents while every vocabulary entry carries them.
"""

from __future__ import annotations

import unicodedata

import pytest

from fi_core.cognitive import PSYCHIATRY, PatientContext, UrgencyClassifier, UrgencyLevel
from fi_core.cognitive.urgency import _strip_negations


def _deaccent(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


@pytest.fixture(scope="module")
def clf() -> UrgencyClassifier:
    return PSYCHIATRY.urgency_classifier()


def _band(clf: UrgencyClassifier, *symptoms: str, history: list[str] | None = None) -> UrgencyLevel:
    return clf.classify(PatientContext(symptoms=list(symptoms), medical_history=history or [])).level


# --- 'sin' inside a symptom is the symptom's grammar, not a denial ----------


def test_mejor_sin_mi_is_seen_by_the_vocabulary_that_lists_it(clf):
    assert "mejor sin mí" in PSYCHIATRY.high_symptoms
    score = clf.classify(PatientContext(symptoms=["mejor sin mí"]))
    assert score.level is UrgencyLevel.HIGH
    assert score.reasons == ("symptom 'mejor sin mi' → gravity 7",)


def test_a_symptom_spelled_with_a_cue_survives_the_stripper_verbatim():
    protected = ("mejor sin mi",)
    assert _strip_negations("mejor sin mi", protected) == "mejor sin mi"
    assert _strip_negations("estoy mejor sin mi", protected) == "estoy mejor sin mi"


def test_sin_is_still_a_denial_cue_outside_a_protected_phrase(clf):
    assert _band(clf, "sin ideación suicida") is UrgencyLevel.LOW
    assert _band(clf, "paciente sin plan suicida ni autolesión activa") is UrgencyLevel.LOW


def test_a_denial_that_contains_a_protected_phrase_is_still_a_denial(clf):
    score = clf.classify(PatientContext(symptoms=["niega sentirse mejor sin mí"]))
    assert score.level is UrgencyLevel.LOW
    assert score.critical_override is False


def test_the_t13_trap_is_still_stripped(clf):
    denial = "el paciente niega ideación suicida, plan suicida o autolesión activa"
    score = clf.classify(PatientContext(symptoms=[denial]))
    assert score.critical_override is False
    assert score.level is UrgencyLevel.LOW


# --- accents: the vocabulary carries them, the user often does not ----------


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("ideacion suicida", UrgencyLevel.HIGH),
        ("autolesion activa", UrgencyLevel.CRITICAL),
        ("hacerme dano", UrgencyLevel.CRITICAL),
        ("ATAQUE DE PANICO", UrgencyLevel.MEDIUM),
        ("Ideación Suicida", UrgencyLevel.HIGH),
    ],
)
def test_accentless_input_scores_like_the_accented_vocabulary(clf, phrase, expected):
    assert _band(clf, phrase) is expected


def test_every_accented_vocabulary_entry_scores_the_same_without_accents(clf):
    vocab = PSYCHIATRY.critical_symptoms | PSYCHIATRY.high_symptoms | PSYCHIATRY.medium_symptoms
    accented = sorted(term for term in vocab if _deaccent(term) != term)
    assert len(accented) >= 16
    drops = [
        (term, _band(clf, term), _band(clf, _deaccent(term)))
        for term in accented
        if _band(clf, term) is not _band(clf, _deaccent(term))
    ]
    assert drops == []


def test_accentless_history_still_adds_the_comorbidity(clf):
    score = clf.classify(PatientContext(symptoms=["duelo"], medical_history=["hospitalizacion psiquiatrica previa"]))
    assert score.modifiers == 0.5
    assert "comorbidity 'hospitalización psiquiátrica previa' (+0.5)" in score.reasons


def test_accentless_critical_pattern_still_overrides(clf):
    score = clf.classify(PatientContext(symptoms=["planea ahorcarse esta noche"]))
    assert score.critical_override is True
    assert score.reasons == ("critical pattern 'ahorcarse' detected → override CRITICAL",)
    score = clf.classify(PatientContext(symptoms=["autolesion activa"]))
    assert score.critical_override is True
    assert score.reasons == ("critical pattern 'autolesión activa' detected → override CRITICAL",)


def test_a_non_low_band_always_carries_a_reason(clf):
    for phrase in ("mejor sin mi", "ideacion suicida", "duelo", "hacerme dano"):
        score = clf.classify(PatientContext(symptoms=[phrase]))
        assert score.level is not UrgencyLevel.LOW
        assert score.reasons
