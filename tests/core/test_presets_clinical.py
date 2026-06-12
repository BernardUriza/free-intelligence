"""Regression tests for RESPECTFUL_SERIOUS classification of clinical speech.

Context: on 2026-04-23 a user (kh1_maera, hereafter "Alex", user_id
1431300030823927999) reported that the bot responded curtly to them despite
them writing about their ongoing psychiatric treatment and complex trauma.
A dump of their last 15 messages from production confirmed every single
message fell through to DEFAULT_ABRASIVE because _SERIOUS_PATTERNS only
matched lay-person crisis phrases ("suicid", "depres", "me siento solo")
and had zero coverage for the clinical vocabulary patients actually use.

These tests fix that: each quote below is VERBATIM from Alex's real
messages (trimmed for length), and each MUST classify as
RESPECTFUL_SERIOUS. If any of these regress to a different mode, a real
person describing their trauma will be roasted by the bot."""

import pytest

from personas.insult.core.presets import PresetMode, classify_preset


@pytest.mark.parametrize(
    "message",
    [
        # Direct diagnosis disclosure — the core leak before the fix
        "Lo que tengo es Estrés Postraumático Complejo, entre otras cosas jeje",
        # Medication timing question — clinically loaded
        "Ah ok, es que había leído que tanto la sertralina como la quetiapina empiezan a hacer efecto a las semanas o algo así",
        # Direct question about psychiatric drug mechanism
        "Jejeje me podrías explicar a qué se debe este efecto de bienestar de la quetiapina en particular",
        # Dosage + adaptation report
        "He dormido bastante bien, y cada día me siento un poquito mejor, mi cuerpx se sigue adaptando a las nuevas dosis",
        # Treatment plan + clinician relationship
        "Lo que haré es seguir una comunicación muy cercana con la neuropsiquiatra respecto a mis síntomas",
        # Refusing involuntary hospitalization — a high-stakes boundary
        "Yo no quisiera internarme la verdad, no creo que respeten mis ajustes razonables como tener conmigo mis audífonos con cancelación",
        # Medication adjustment disclosure
        "Me aumentó dosis de quetiapina y sertralina",
        # Artritis / chronic-illness disclosure
        "Tengo artritis en proceso de diagnóstico y otras cosas",
    ],
)
def test_alex_real_messages_classify_as_respectful_serious(message: str):
    """Each verbatim production quote must route to the respectful mode.

    Before the fix each of these matched ZERO patterns and hit the abrasive
    fallback. The test failing means the bot is back to roasting people
    disclosing psychiatric treatment — an ethics regression, not a style one."""
    result = classify_preset(message)
    assert result.mode == PresetMode.RESPECTFUL_SERIOUS, (
        f"Expected RESPECTFUL_SERIOUS for clinical message, got {result.mode.value}. "
        f"Reason: {result.reason!r}. Message: {message!r}"
    )


def test_clinical_vocabulary_beats_abrasive_default():
    """Spot-check: a message containing psychiatric terms but no classic
    crisis phrases must still route to RESPECTFUL_SERIOUS."""
    result = classify_preset("estoy tomando mi dosis de quetiapina hoy")
    assert result.mode == PresetMode.RESPECTFUL_SERIOUS


def test_plain_chit_chat_is_not_accidentally_serious():
    """Inverse regression: ensure the expanded patterns didn't over-trigger.
    Neutral small talk must NOT classify as serious."""
    result = classify_preset("hola qué tal, cómo va tu día")
    assert result.mode != PresetMode.RESPECTFUL_SERIOUS


# ---- Vulnerable user overlay (F1 — split chronic from acute) ----
#
# F1 (2026-05-11) changed how chronic-vulnerable users are routed when the
# current message is NOT an acute crisis. Before F1: chronic facts forced
# RESPECTFUL_SERIOUS every turn, producing flat "presence, not performance"
# replies that left the DIF turn (Alex) as a regression case. After F1:
#
#   chronic | acute-in-msg | clinical-in-msg | preset                      | reason prefix
#   --------+--------------+-----------------+-----------------------------+--------------
#   yes     | yes          | -               | RESPECTFUL_SERIOUS (acute)  | acute_crisis
#                                              [telemetry: crisis_presence]
#   yes     | no           | yes             | RESPECTFUL_SERIOUS (clinic) | serious_trigger
#   yes     | no           | no              | RELATIONAL_PROBE (movement) | chronic_nonacute_move_allowed
#   no      | yes          | -               | RESPECTFUL_SERIOUS (acute)  | acute_crisis
#                                              [telemetry: crisis_presence]
#   no      | no           | yes             | RESPECTFUL_SERIOUS (clinic) | serious_trigger
#   no      | no           | no              | regular preset flow         | other
#
# is_vulnerable_overlay_selection() recognises all chronic / acute prefixes
# so the safety overlay (chronic_care_constraints, sharpness cap, clinical
# search allowlist, crisis hotlines on acute distress) still activates
# downstream for every routing that crosses the vulnerability threshold.


def _alex_like_facts() -> list[dict]:
    """Reconstruct Alex's fact cluster (diagnosis + meds + clinician)."""
    return [
        {"fact": "Tiene Estrés Postraumático Complejo (CPTSD)"},
        {"fact": "Toma quetiapina y sertralina, dosis aumentada recientemente"},
        {"fact": "Sigue tratamiento con una neuropsiquiatra"},
        {"fact": "Tiene artritis en diagnóstico"},
    ]


def test_vulnerable_user_neutral_message_routes_to_relational_probe():
    """F1 regression: chronic-vulnerable + non-clinical current message
    must NOT collapse to RESPECTFUL_SERIOUS (flat presence). It now routes
    to RELATIONAL_PROBE — a movement-permitting preset whose guidance
    naturally aligns with the chronic-care directive 'sharpness capped,
    movement preserved'. ARC was considered but rejected for carrying too
    much old machinery (mechanism-naming, ideology sub-sections) for this
    routing. The safety overlay still activates via the
    `chronic_nonacute_move_allowed` reason prefix.

    This is the case that aplanó a Alex on the DIF turn before F1."""
    from personas.insult.core.presets import is_vulnerable_overlay_selection

    result = classify_preset(
        "He dormido bastante bien, y cada día me siento un poquito mejor",
        user_facts=_alex_like_facts(),
    )
    assert result.mode == PresetMode.RELATIONAL_PROBE
    assert result.reason.startswith("chronic_nonacute_move_allowed")
    assert is_vulnerable_overlay_selection(result), "safety overlay must still apply"


def test_vulnerable_user_medication_follow_up_routes_to_relational_probe():
    """A reflective message without clinical-vocab triggers AND without
    acute crisis signals must route to RELATIONAL_PROBE for chronic-vulnerable
    users. F1: substantive engagement under the safety overlay, not flat
    presence."""
    from personas.insult.core.presets import is_vulnerable_overlay_selection

    result = classify_preset(
        "Yo sentí efectos muy positivos desde las primeras tomas, como una especie de contención que aumentaba cada día",
        user_facts=_alex_like_facts(),
    )
    assert result.mode == PresetMode.RELATIONAL_PROBE
    assert result.reason.startswith("chronic_nonacute_move_allowed")
    assert is_vulnerable_overlay_selection(result)


def test_vulnerable_user_clinical_vocab_in_current_still_serious():
    """If the current message contains clinical vocabulary (matches
    _SERIOUS_PATTERNS via priority 1), RESPECTFUL_SERIOUS still wins
    over the chronic-nonacute routing.

    Critical: when the user is ALSO chronic-vulnerable, the reason must
    use the `chronic_serious_clinical_current` prefix so the safety
    overlay (clinical-source allowlist, no invented pharmacology, dosing
    discipline) ACTIVATES — this is the exact moment that overlay matters
    most, and dropping it here was the silent regression that the F1
    rewrite almost shipped."""
    from personas.insult.core.presets import is_vulnerable_overlay_selection

    result = classify_preset(
        "Me aumentó dosis de quetiapina",
        user_facts=_alex_like_facts(),
    )
    assert result.mode == PresetMode.RESPECTFUL_SERIOUS
    assert result.reason.startswith("chronic_serious_clinical_current")
    assert is_vulnerable_overlay_selection(result), (
        "Chronic vulnerable + clinical-current MUST keep the overlay — "
        "this is where medlineplus discipline matters most."
    )


def test_non_chronic_user_clinical_vocab_does_not_get_overlay():
    """Inverse: a user WITHOUT chronic facts who happens to write about
    depression in the current message gets RESPECTFUL_SERIOUS via the
    serious_trigger reason — no overlay (no fact history to justify it).
    The chronic-clinical branch must NOT over-trigger."""
    from personas.insult.core.presets import is_vulnerable_overlay_selection

    result = classify_preset("estoy con depresión severa hoy")
    assert result.mode == PresetMode.RESPECTFUL_SERIOUS
    assert result.reason.startswith("serious_trigger")
    assert not is_vulnerable_overlay_selection(result)


def test_acute_crisis_overrides_chronic_arc_routing():
    """Acute crisis signals in the current message ALWAYS route to
    RESPECTFUL_SERIOUS, even for chronic-vulnerable users who would
    otherwise route to ARC."""
    result = classify_preset(
        "ya no puedo más",
        user_facts=_alex_like_facts(),
    )
    assert result.mode == PresetMode.RESPECTFUL_SERIOUS
    assert "acute_crisis" in result.reason


def test_acute_crisis_routes_to_serious_for_new_users_too():
    """A new user (no facts) writing acute distress must also route to
    RESPECTFUL_SERIOUS via the acute branch. Safety floor is independent
    of fact history."""
    result = classify_preset("ya no aguanto, no puedo más con esto")
    assert result.mode == PresetMode.RESPECTFUL_SERIOUS
    assert "acute_crisis" in result.reason


def test_non_vulnerable_user_neutral_message_is_not_serious():
    """Inverse regression: a user without clinical facts writing casually
    must NOT get forced into RESPECTFUL_SERIOUS."""
    facts = [
        {"fact": "Le gusta el café"},
        {"fact": "Es programador"},
    ]
    result = classify_preset("he dormido bien hoy", user_facts=facts)
    assert result.mode != PresetMode.RESPECTFUL_SERIOUS


# ---- display_label rename: CRISIS_PRESENCE in telemetry ----
#
# Aju ste 1 (2026-05-11): the safety floor for acute crisis must be visible
# in telemetry as `crisis_presence`, not hidden under the everyday
# `respectful_serious` label that is also used for clinical-vocab routing
# (e.g. a user asking how quetiapine works — same internal guidance, NOT
# crisis). Internally the mode stays RESPECTFUL_SERIOUS so the guidance
# block is identical; only the display label differs by reason.


def test_acute_crisis_displays_as_crisis_presence():
    """A turn routed via acute_crisis must show up as `crisis_presence`
    in telemetry while the internal mode stays RESPECTFUL_SERIOUS."""
    result = classify_preset("ya no puedo más")
    assert result.mode == PresetMode.RESPECTFUL_SERIOUS  # internal unchanged
    assert result.display_label == "crisis_presence"


def test_clinical_vocab_routing_still_shows_respectful_serious():
    """A clinical-vocab routing (priority 1, NOT acute) keeps the legacy
    respectful_serious telemetry label. The rename is reserved for acute."""
    result = classify_preset("me aumentó dosis de quetiapina")
    assert result.mode == PresetMode.RESPECTFUL_SERIOUS
    assert result.display_label == "respectful_serious"


def test_chronic_nonacute_routing_displays_as_relational_probe():
    """Chronic-vulnerable + non-acute routes to RELATIONAL_PROBE — that is
    the label that appears in telemetry. The display_label rename is
    acute-only; relational_probe stays as itself."""
    result = classify_preset(
        "el día estuvo tranquilo, fui a caminar al parque",
        user_facts=_alex_like_facts(),
    )
    assert result.display_label == "relational_probe"


def test_safety_overlay_activates_for_all_three_routing_reasons():
    """is_vulnerable_overlay_selection must return True for any routing
    that crosses the vulnerability threshold: acute_crisis,
    chronic_nonacute_move_allowed, and the legacy vulnerable_user_overlay
    prefix (kept for any in-flight selection during deploy)."""
    from personas.insult.core.presets import (
        PresetSelection,
        is_vulnerable_overlay_selection,
    )

    acute = PresetSelection(
        mode=PresetMode.RESPECTFUL_SERIOUS,
        reason="acute_crisis_in_current_message",
    )
    assert is_vulnerable_overlay_selection(acute)

    chronic = PresetSelection(
        mode=PresetMode.RELATIONAL_PROBE,
        reason="chronic_nonacute_move_allowed: score=11 signals=['named_diagnosis']",
    )
    assert is_vulnerable_overlay_selection(chronic)

    legacy = PresetSelection(
        mode=PresetMode.RESPECTFUL_SERIOUS,
        reason="vulnerable_user_overlay: score=8 signals=[]",
    )
    assert is_vulnerable_overlay_selection(legacy)

    not_overlay = PresetSelection(
        mode=PresetMode.DEFAULT_ABRASIVE,
        reason="no_specific_trigger: defaulting to abrasive",
    )
    assert not is_vulnerable_overlay_selection(not_overlay)
