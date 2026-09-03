"""`ClinicalDomain.match` — from what a person wrote to what the classifier scores.

fi-core #458: the vocabularies carry accents, Discord users do not, and a
consumer that greps the frozensets by hand loses 'ideacion suicida' before the
(already folding) classifier ever sees it. `match` is the one official path.
"""

from __future__ import annotations

from fi_core.cognitive import CARDIOLOGY, PSYCHIATRY, PatientContext, UrgencyLevel, VocabularyHits


def test_accentless_message_finds_the_accented_entry():
    hits = PSYCHIATRY.match("ando con ideacion suicida")
    assert "ideación suicida" in hits.symptoms
    assert hits.critical_patterns == ()


def test_the_three_messages_alex_measured_reach_their_band():
    clf = PSYCHIATRY.urgency_classifier()
    expected = {
        "ando con ideacion suicida": UrgencyLevel.HIGH,
        "tengo un ataque de panico": UrgencyLevel.MEDIUM,
        "quiero hacerme dano": UrgencyLevel.CRITICAL,
    }
    for message, level in expected.items():
        hits = PSYCHIATRY.match(message)
        assert hits, message
        assert clf.classify(PatientContext(symptoms=list(hits.symptoms))).level is level, message


def test_critical_patterns_and_conditions_are_reported_separately():
    hits = PSYCHIATRY.match("QUIERO HACERME DAÑO, tengo un intento de suicidio previo")
    assert "hacerme daño" in hits.symptoms
    assert "hacerme daño" in hits.critical_patterns
    assert hits.high_risk_conditions == ("intento de suicidio previo",)


def test_a_symptom_spelled_with_a_negation_cue_is_found():
    hits = PSYCHIATRY.match("la verdad estoy mejor sin mi, ya no quiero estar")
    assert "mejor sin mí" in hits.symptoms
    assert "ya no quiero estar" in hits.symptoms


def test_a_denied_symptom_is_not_found():
    assert not PSYCHIATRY.match("el paciente niega ideación suicida, plan suicida o autolesión activa")
    assert not PSYCHIATRY.match("sin ideacion suicida ni plan")


def test_nothing_in_nothing():
    hits = PSYCHIATRY.match("hoy comí banana con queso")
    assert hits == VocabularyHits()
    assert not hits


def test_entries_come_back_in_vocabulary_spelling_longest_first():
    hits = PSYCHIATRY.match("ideacion suicida activa desde ayer")
    assert hits.symptoms[0] == "ideación suicida activa"
    assert "ideación suicida" in hits.symptoms


def test_every_domain_has_the_matcher():
    hits = CARDIOLOGY.match("Chest pain and DIAPHORESIS, denies syncope")
    assert set(hits.symptoms) == {"chest pain", "diaphoresis"}
