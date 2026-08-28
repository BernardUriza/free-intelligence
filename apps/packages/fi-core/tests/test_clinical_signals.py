"""Weighted clinical signals — the contract the canary's production corpus proved.

The behavioral pins port from discord-bot's ``test_vulnerability_scoring.py``:
the semantics that ran in production since 2026-04-23 must survive the move
into fi-core byte-for-byte (a cluster crosses, a redundant single signal does
not, weights count once per group). On top ride the pins for what the flat
vocabularies never could: the four ``high_risk_conditions`` categories that
were named but undetectable, and the acute axis with its bilingual phrases.
"""

from __future__ import annotations

import pytest

from fi_core.cognitive import (
    CARDIOLOGY,
    PSYCH_ACUTE_SIGNALS,
    PSYCH_CHRONIC_SIGNALS,
    PSYCHIATRY,
    SignalGroup,
    WeightedSignals,
)

CHRONIC = PSYCHIATRY.chronic_signals
ACUTE = PSYCHIATRY.acute_signals


# --- the engine -------------------------------------------------------------


def test_a_group_scores_its_weight_at_most_once():
    """Fact extractors emit 2-5 redundant facts per event; counting each would
    let one isolated signal cross a threshold built for clusters."""
    r = CHRONIC.score(["toma sertralina", "tomó su primera pastilla de sertralina",
                       "la sertralina le sienta bien"])
    assert r.score == 3 and not r.crosses
    assert r.matched == ("psychiatric_medication",)


def test_one_text_spanning_two_groups_scores_both():
    r = CHRONIC.score(["le diagnosticaron CPTSD y toma quetiapina"])
    assert set(r.matched) == {"named_diagnosis", "psychiatric_medication"}
    assert r.score == 6 and r.crosses


def test_a_cluster_crosses_a_single_signal_does_not():
    assert CHRONIC.crosses(["tiene TDAH", "va con su psiquiatra"])  # 3 + 2
    assert not CHRONIC.crosses(["tiene TDAH"])  # 3 < 4
    assert not CHRONIC.crosses(["hoy comió tacos", "le gusta programar"])


def test_empty_and_falsy_texts_score_zero():
    assert CHRONIC.score([]).score == 0
    assert CHRONIC.score(["", ""]).score == 0
    assert not CHRONIC.score([]).crosses


def test_scored_signals_explains_why():
    r = CHRONIC.score(["internamiento psiquiátrico en 2023", "su terapeuta lo dio de alta"])
    assert r.matched == ("hospitalization", "mental_health_clinician")
    assert r.threshold == 4 and r.score == 4 and r.crosses


def test_make_compiles_case_insensitive():
    g = SignalGroup.make("x", 1, r"\bfoo\b")
    assert g.pattern.search("FOO bar")


# --- the migrated corpus (parity with the canary) ---------------------------


@pytest.mark.parametrize(
    ("text", "group", "weight"),
    [
        ("le diagnosticaron CPTSD", "named_diagnosis", 3),
        ("toma quetiapina en las noches", "psychiatric_medication", 3),
        ("estuvo en internamiento psiquiátrico", "hospitalization", 2),
        ("su psiquiatra le ajustó la dosis", "mental_health_clinician", 2),
        ("tiene artritis desde joven", "chronic_comorbidity", 1),
        ("tuvo un intento de suicidio en 2020", "self_harm_history", 3),
    ],
)
def test_each_migrated_group_fires_with_its_production_weight(text, group, weight):
    r = CHRONIC.score([text])
    assert r.matched == (group,) or group in r.matched
    assert dict.fromkeys(r.matched) and r.score >= weight


def test_metaphorical_trauma_still_scores_its_group_only():
    """'estoy traumado con el código' matches the diagnosis regex (postraum
    stems do not, 'trauma complej' does not) — verify the famous metaphor does
    NOT cross alone, which is the threshold's whole job."""
    r = CHRONIC.score(["estoy traumado con el código"])
    assert not r.crosses


# --- the four categories that were named but undetectable -------------------


@pytest.mark.parametrize(
    ("text", "group"),
    [
        ("sufrió violencia doméstica en su casa", "abuse"),
        ("vive en aislamiento social, no tengo amigos", "social_isolation"),
        ("su padre falleció el mes pasado", "recent_grief"),
        ("está en recuperación del alcoholismo", "substance_use"),
    ],
)
def test_the_orphan_categories_now_detect(text, group):
    assert group in CHRONIC.matched([text])


def test_orphan_category_weights_are_the_proposed_two():
    """Weights proposed in Alex's #52 close-out terms ('con peso propio') —
    pinned so a casual change shows up as a failing test, not a silent drift."""
    by_name = {g.name: g.weight for g in CHRONIC.groups}
    assert {by_name[n] for n in ("abuse", "social_isolation", "recent_grief",
                                 "substance_use")} == {2}


# --- the acute axis ---------------------------------------------------------


@pytest.mark.parametrize(
    "message",
    [
        "ya no puedo más",  # the phrase Valentis first answered with
        "me quiero morir",
        "i can't go on",
        "estoy en crisis",
        "ataque de pánico ahorita",
        "no tengo a nadie",
        "help me for real",
    ],
)
def test_acute_phrases_fire(message):
    assert ACUTE.crosses([message])


@pytest.mark.parametrize(
    "message",
    ["he dormido bien hoy", "el deploy salió bien", "qué opinas del clima"],
)
def test_normal_messages_do_not_fire_acute(message):
    assert not ACUTE.crosses([message])


def test_acute_threshold_preserves_boolean_semantics():
    assert ACUTE.threshold == 1


def test_acute_weights_grade_severity_for_banding():
    """#53's banded classifier needs explicit ideation to outweigh a cry for
    help — the weights must be graded, not flat."""
    ideation = ACUTE.score(["me quiero morir"]).score
    cry = ACUTE.score(["estoy mal de verdad"]).score
    assert ideation > cry


# --- domain wiring ----------------------------------------------------------


def test_psychiatry_ships_both_axes_and_cardiology_neither():
    assert PSYCHIATRY.chronic_signals is PSYCH_CHRONIC_SIGNALS
    assert PSYCHIATRY.acute_signals is PSYCH_ACUTE_SIGNALS
    assert CARDIOLOGY.chronic_signals is None
    assert CARDIOLOGY.acute_signals is None


def test_weighted_signals_is_a_plain_reusable_shape():
    ws = WeightedSignals(threshold=2, groups=(SignalGroup.make("a", 1, "foo"),
                                              SignalGroup.make("b", 1, "bar")))
    assert not ws.crosses(["foo"])
    assert ws.crosses(["foo y bar"])
