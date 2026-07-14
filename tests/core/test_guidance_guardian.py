"""The guardian: the vulnerable-user overlay must REACH the model.

The engine has always been able to classify a clinical cluster (a named diagnosis
+ psychiatric medication ⇒ score over the threshold) and to render the safety
overlay. What went missing when the plumbing was purged (2026-07-14) was the
WIRE: nobody built `behavioral_guidance`, so the overlay never left the process.
A user in chronic care received the persona's raw abrasive register.

Positive: Alex's real fact cluster produces guidance carrying the overlay, and it
lands on the runner call. Resistance: a user with no facts gets no overlay but
still gets their turn; a dead fact store, a raising classifier and an over-long
render all degrade to a NORMAL turn — never a mute bot, never a 422.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from khimeras_shared import guidance as guidance_mod
from khimeras_shared.behavior import VULNERABLE_THRESHOLD, compute_vulnerability_score
from khimeras_shared.guidance import (
    MAX_GUIDANCE_CHARS,
    build_turn_guidance,
    guidance_for_turn,
    load_user_facts,
)

# Alex's real cluster, the one that motivated the overlay: a named diagnosis + a
# psychiatric medication + a treating clinician.
ALEX_FACTS = [
    {"id": 1, "fact": "fue diagnosticada con CPTSD por su psiquiatra", "category": "salud"},
    {"id": 2, "fact": "toma quetiapina cada noche para dormir", "category": "salud"},
    {"id": 3, "fact": "va a terapia cada semana", "category": "salud"},
]

OVERLAY_MARKERS = ("saptel", "línea de la vida", "medlineplus")


def _has_overlay(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in OVERLAY_MARKERS)


def test_alex_cluster_crosses_the_threshold():
    """The premise of everything below — if this breaks, the guardian is blind."""
    assert compute_vulnerability_score(ALEX_FACTS) >= VULNERABLE_THRESHOLD


def test_vulnerable_user_gets_the_overlay_in_the_guidance():
    guidance = build_turn_guidance(
        current_message="hoy ando bien perra la ansiedad, no sé ni por dónde empezar",
        recent_messages=[],
        user_facts=ALEX_FACTS,
        persona_id="insult",
    )
    assert guidance
    assert _has_overlay(guidance), "el overlay clínico NO llegó a la guidance"


def test_vulnerable_user_asking_about_their_medication_keeps_the_overlay():
    """The moment the overlay matters MOST: clinical vocabulary from a user in
    chronic care (source discipline, no invented pharmacology)."""
    guidance = build_turn_guidance(
        current_message="me subieron la quetiapina a 100mg, eso está bien?",
        recent_messages=[],
        user_facts=ALEX_FACTS,
        persona_id="insult",
    )
    assert guidance and _has_overlay(guidance)


def test_user_without_facts_gets_guidance_without_overlay():
    """RESISTANCE: the overlay is for clinical clusters, not for everyone — a
    normal user keeps the persona's normal register."""
    guidance = build_turn_guidance(
        current_message="qué opinas del último disco de Rosalía",
        recent_messages=[],
        user_facts=[],
        persona_id="insult",
    )
    assert guidance  # the preset guidance still renders
    assert not _has_overlay(guidance)


def test_empty_message_yields_no_guidance():
    assert build_turn_guidance(current_message="   ", recent_messages=[], user_facts=[], persona_id="insult") is None


def test_persona_without_guidance_content_yields_none_not_a_crash():
    """RESISTANCE: Vultur/Frugi have no guidance .md yet — the engine still
    classifies, the prompt just carries no voice-specific block."""
    guidance = build_turn_guidance(
        current_message="reséñame Stalker",
        recent_messages=[],
        user_facts=[],
        persona_id="vultur",
    )
    assert guidance is None or guidance == ""


def test_classifier_fault_degrades_to_no_guidance_never_raises():
    """RESISTANCE: a fault must cost the guidance, NEVER the turn."""
    with patch.object(guidance_mod, "classify_preset", side_effect=RuntimeError("boom")):
        assert (
            build_turn_guidance(
                current_message="hola",
                recent_messages=[],
                user_facts=ALEX_FACTS,
                persona_id="insult",
            )
            is None
        )


def test_overlong_guidance_is_truncated_to_the_schema_cap():
    """RESISTANCE: the runner rejects >16000 chars with a 422 — a safety feature
    must never become a mute bot. We truncate here, loudly."""
    with (
        patch.object(guidance_mod, "build_preset_prompt", return_value="x" * (MAX_GUIDANCE_CHARS + 5000)),
        patch.object(guidance_mod, "is_vulnerable_overlay_selection", return_value=False),
    ):
        guidance = build_turn_guidance(
            current_message="hola",
            recent_messages=[],
            user_facts=[],
            persona_id="insult",
        )
    assert guidance is not None
    assert len(guidance) == MAX_GUIDANCE_CHARS


async def test_dead_fact_store_degrades_to_empty_facts():
    """RESISTANCE: a DB fault yields an unscored turn, never a dropped turn."""
    memory = MagicMock()
    memory.get_facts = AsyncMock(side_effect=RuntimeError("pg down"))
    assert await load_user_facts(memory, "U1") == []


async def test_guidance_for_turn_loads_facts_and_renders_the_overlay():
    memory = MagicMock()
    memory.get_facts = AsyncMock(return_value=ALEX_FACTS)
    guidance = await guidance_for_turn(
        memory=memory,
        user_id="U-alex",
        current_message="no he dormido en tres días",
        recent_messages=[],
        persona_id="insult",
    )
    memory.get_facts.assert_awaited_once_with("U-alex")
    assert guidance and _has_overlay(guidance)


@pytest.mark.parametrize("bad_memory", [None, MagicMock(get_facts=AsyncMock(side_effect=RuntimeError("x")))])
async def test_guidance_for_turn_survives_a_broken_memory(bad_memory):
    """RESISTANCE: no store / broken store → the turn still happens, unscored."""
    guidance = await guidance_for_turn(
        memory=bad_memory,
        user_id="U1",
        current_message="qué pex",
        recent_messages=[],
        persona_id="insult",
    )
    assert guidance is None or not _has_overlay(guidance)
