"""`ClinicalDomain.assess()` (0.30.0) — one call, one verdict, one explanation.

Before it, a consumer that wanted the band AND the reason made two readings of
the same message with two engines (`urgency_classifier().classify(...)` and
`acute_signals.matched(...)`) and stapled the results together hoping they
agreed. They diverged once (0.29.1). discord-bot's `_GROUP_TO_CONDITION` — the
bridge from chronic group names to `high_risk_conditions` — lived in the
consumer; here it is read off `SignalGroup.category`, where fi-core already
declared it.
"""

from __future__ import annotations

from fi_core.cognitive import CARDIOLOGY, PSYCHIATRY, ClinicalVerdict, UrgencyLevel, UrgencyReason

# discord-bot khimeras_shared/behavior/vulnerability.py (v4.38.15), verbatim.
# The map rises to the domain; this pins that nothing was lost on the way up.
_DISCORD_BOT_GROUP_TO_CONDITION = {
    "self_harm_history": "intento de suicidio previo",
    "recent_grief": "duelo reciente",
    "abuse": "abuso",
    "hospitalization": "hospitalización psiquiátrica previa",
    "social_isolation": "aislamiento social",
    "substance_use": "trastorno por uso de sustancias",
    "exposicion_intento": "exposición a intento de suicidio",
    "exposicion_consumado": "exposición a suicidio consumado",
}


def test_chronic_conditions_is_the_consumers_map_read_off_the_groups():
    assert PSYCHIATRY.chronic_conditions == _DISCORD_BOT_GROUP_TO_CONDITION
    # The four groups with no counterpart score the axis but never reach the band.
    unmapped = {g.name for g in PSYCHIATRY.chronic_signals.groups} - set(PSYCHIATRY.chronic_conditions)
    assert unmapped == {"named_diagnosis", "psychiatric_medication", "mental_health_clinician", "chronic_comorbidity"}
    assert CARDIOLOGY.chronic_conditions == {}


def test_conditions_for_translates_and_sorts_and_ignores_unmapped():
    assert PSYCHIATRY.conditions_for(["self_harm_history", "named_diagnosis", "abuse"]) == (
        "abuso",
        "intento de suicidio previo",
    )
    assert PSYCHIATRY.conditions_for([]) == ()


def test_one_call_carries_band_axes_and_conditions_from_the_same_reading():
    v = PSYCHIATRY.assess(
        "me quiero morir, no puedo más",
        history=["toma sertralina", "tuvo un intento de suicidio en 2020", "sufrió abuso de niño"],
    )
    assert isinstance(v, ClinicalVerdict)
    assert v.level is UrgencyLevel.CRITICAL and v.score.critical_override
    assert v.acute.matched == ("at_the_limit", "explicit_ideation")
    assert v.chronic.matched == ("abuse", "psychiatric_medication", "self_harm_history")
    assert v.chronic.crosses
    assert v.conditions == ("abuso", "intento de suicidio previo")
    assert v.hits.critical_patterns and "quiero morir" in v.hits.critical_patterns


def test_history_reaches_the_band_as_comorbidity_reasons_through_the_map():
    v = PSYCHIATRY.assess("no duermo bien, insomnio", history=["duelo reciente por su madre", "vive aislado"])
    assert v.level is UrgencyLevel.MEDIUM
    assert v.chronic.matched == ("recent_grief", "social_isolation")
    assert v.conditions == ("aislamiento social", "duelo reciente")
    assert UrgencyReason("comorbidity", "aislamiento social", 0.5) in v.score.reasons
    assert UrgencyReason("comorbidity", "duelo reciente", 0.5) in v.score.reasons
    assert v.score.modifiers == 1.0


def test_a_condition_the_message_names_is_reported_not_scored():
    """Parity with the canary: the message is now, the history is the record."""
    v = PSYCHIATRY.assess("sufrí abuso de niño y hoy tengo insomnio")
    assert v.hits.high_risk_conditions == ("abuso",)
    assert v.conditions == ()
    assert v.score.modifiers == 0.0
    assert v.chronic is not None and v.chronic.matched == ()


def test_denied_and_excluded_travel_on_both_layers():
    v = PSYCHIATRY.assess("no me quiero morir, es broma", history=["mi hermana intentó suicidarse"])
    assert v.level is UrgencyLevel.LOW
    assert "quiero morir" in v.hits.denied
    assert v.acute.matched == () and v.acute.denied == ("explicit_ideation",)
    assert v.chronic.matched == ("exposicion_intento",)
    assert v.chronic.excluded == ("exposicion_intento",)
    assert v.conditions == ("exposición a intento de suicidio",)
    assert UrgencyReason("comorbidity", "exposición a intento de suicidio", 0.5) in v.score.reasons


def test_empty_inputs_yield_a_low_verdict_with_empty_axes():
    v = PSYCHIATRY.assess("", history=[""])
    assert v.level is UrgencyLevel.LOW
    assert v.acute.matched == () and not v.acute.crosses
    assert v.chronic.matched == () and not v.chronic.crosses
    assert v.conditions == () and v.score.reasons == ()


def test_a_domain_without_axes_assesses_with_none_axes():
    v = CARDIOLOGY.assess("acute chest pain and dyspnea", history=["hypertension"])
    assert v.level is UrgencyLevel.HIGH
    assert v.acute is None and v.chronic is None
    assert v.conditions == ()
    assert v.hits.symptoms == ("chest pain", "dyspnea")


def test_assess_matches_the_two_reading_path_it_replaces():
    """The verdict is the classifier's verdict — assess() adds no second engine."""
    message, history = "estoy sin dormir y me quiero matar", ["tuvo un intento de suicidio"]
    v = PSYCHIATRY.assess(message, history)
    from fi_core.cognitive import PatientContext

    by_hand = PSYCHIATRY.urgency_classifier().classify(
        PatientContext(
            symptoms=list(PSYCHIATRY.match(message).symptoms),
            medical_history=list(PSYCHIATRY.conditions_for(PSYCHIATRY.chronic_signals.matched(history))),
        )
    )
    assert v.score == by_hand
    assert v.acute.matched == PSYCHIATRY.acute_signals.matched([message])
