"""`GravityScore.reasons` are typed (0.30.0) — a log keeps `kind`/`key`/`weight`
and never a person's words; `render()` keeps the prose a clinician reads.

Founding case (discord-bot #54, persona-gateway rev 201, 2026-09-09 00:11 UTC):
the first real `crisis_band_classified` event in Log Analytics carried
`"reasons": ["comorbidity 'abuso' (+0.5)", "comorbidity 'duelo reciente' (+0.5)", …]`
— prose the consumer could not strip without parsing it, and on a grave turn
it would have carried the vocabulary phrase (`critical pattern 'quiero morir'`).
"""

from __future__ import annotations

import dataclasses

from fi_core.cognitive import (
    CARDIOLOGY,
    PSYCHIATRY,
    GravityScore,
    PatientContext,
    UrgencyLevel,
    UrgencyReason,
)

clf = PSYCHIATRY.urgency_classifier()


def test_symptom_reasons_name_the_vocabulary_tier_and_keep_the_term_for_render():
    score = clf.classify(PatientContext(symptoms=["mejor sin mí", "insomnio", "dolor de rodilla"]))
    assert score.reasons == (
        UrgencyReason("symptom", "high_symptoms", 7, term="mejor sin mi"),
        UrgencyReason("symptom", "medium_symptoms", 5, term="insomnio"),
        UrgencyReason("symptom", "unlisted", 3, term="dolor de rodilla"),
    )
    assert score.explain() == (
        "symptom 'mejor sin mi' → gravity 7",
        "symptom 'insomnio' → gravity 5",
        "symptom 'dolor de rodilla' → gravity 3",
    )


def test_critical_pattern_reason_is_the_override_with_the_pattern_as_term_only():
    score = clf.classify(PatientContext(symptoms=["planea ahorcarse esta noche"]))
    (reason,) = score.reasons
    assert reason.kind == "critical_pattern"
    assert reason.key == "critical_patterns"
    assert reason.weight == 10
    assert reason.term == "ahorcarse"
    assert reason.render() == "critical pattern 'ahorcarse' detected → override CRITICAL"


def test_comorbidity_reason_key_is_the_condition_entry_with_no_term():
    score = clf.classify(PatientContext(symptoms=["insomnio"], medical_history=["intento de suicidio previo"]))
    assert UrgencyReason("comorbidity", "intento de suicidio previo", 0.5) in score.reasons
    assert "comorbidity 'intento de suicidio previo' (+0.5)" in score.explain()


def test_age_and_pregnancy_reasons_render_the_flow_md_prose():
    score = CARDIOLOGY.urgency_classifier().classify(
        PatientContext(age=70, gender="female", symptoms=["pregnant, chest pain"], medical_history=["diabetes"])
    )
    assert score.reasons == (
        UrgencyReason("symptom", "high_symptoms", 7, term="pregnant, chest pain"),
        UrgencyReason("age", "over_65", 1.0),
        UrgencyReason("comorbidity", "diabetes", 0.5),
        UrgencyReason("pregnancy", "pregnant", 1.0),
    )
    assert score.explain()[1:] == ("age > 65 (+1.0)", "comorbidity 'diabetes' (+0.5)", "pregnancy (+1.0)")
    infant = CARDIOLOGY.urgency_classifier().classify(PatientContext(age=0, symptoms=["fever"]))
    assert UrgencyReason("age", "under_1", 1.5) in infant.reasons
    assert "age < 1 (+1.5)" in infant.explain()


def test_the_term_never_leaves_through_repr():
    """A serializer that falls back to repr (structlog's JSON renderer) must not
    leak the person's words: the log-safe fields are the only ones repr shows."""
    score = clf.classify(PatientContext(symptoms=["me quiero morir"]))
    (reason,) = score.reasons
    assert reason.term == "quiero morir"
    assert "quiero morir" not in repr(reason)
    assert "quiero morir" not in repr(score)
    assert repr(reason) == "UrgencyReason(kind='critical_pattern', key='critical_patterns', weight=10)"


def test_the_log_safe_triplet_is_the_stable_surface():
    """What a consumer writes to a log: kind + key + weight, all plain scalars."""
    score = clf.classify(
        PatientContext(symptoms=["me quiero morir"], medical_history=["abuso", "duelo reciente"])
    )
    rows = [(r.kind, r.key, r.weight) for r in score.reasons]
    assert rows == [("critical_pattern", "critical_patterns", 10)]
    calm = clf.classify(PatientContext(symptoms=["insomnio"], medical_history=["abuso", "duelo reciente"]))
    assert [(r.kind, r.key, r.weight) for r in calm.reasons] == [
        ("symptom", "medium_symptoms", 5),
        ("comorbidity", "abuso", 0.5),
        ("comorbidity", "duelo reciente", 0.5),
    ]
    for r in calm.reasons:
        assert r.key in PSYCHIATRY.high_risk_conditions or r.key.endswith("_symptoms")


def test_reasons_are_frozen_and_hashable():
    r = UrgencyReason("comorbidity", "abuso", 0.5)
    assert hash(r) == hash(UrgencyReason("comorbidity", "abuso", 0.5))
    assert dataclasses.is_dataclass(r)
    assert isinstance(clf.classify(PatientContext(symptoms=["duelo"])), GravityScore)
    assert clf.classify(PatientContext(symptoms=["duelo"])).level is UrgencyLevel.MEDIUM
