"""Insult's rebirth entry (2026-07-14) — a persona like its siblings.

Positive: registered with its DNA file and real bot id, gateway-enabled.
Resistance: the gateway spins it ONLY when INSULT_DISCORD_TOKEN is present in
the env (the single-owner cutover gate — never two live bots on one token),
and its DNA file actually exists where the runner image will look for it.
"""

from __future__ import annotations

from pathlib import Path

from shared.personas import gateway_personas, get_persona
from shared.personas.registry import persona_id_by_bot_user_id, persona_id_by_role_name


def test_insult_is_a_registered_persona():
    insult = get_persona("insult")
    assert insult is not None
    assert insult.persona_file == "insult.md"
    assert insult.token_env == "INSULT_DISCORD_TOKEN"  # noqa: S105 — env-var NAME, not a secret
    assert insult.bot_user_id == "1488415576551325906"
    assert insult.gateway_enabled is True


def test_insult_dna_file_exists_next_to_its_siblings():
    dna = Path(__file__).parents[2] / "shared" / "personas" / "insult.md"
    assert dna.is_file()
    assert dna.stat().st_size > 1000


def test_insult_dna_and_runner_fallback_never_drift():
    """persona.md (the runner's PERSONA_PATH fallback + sync_capabilities target)
    and shared/personas/insult.md (the DNA served for persona_id='insult') were
    born as verbatim copies (296fe8d) with NO sync mechanism. Until the physical
    dedup lands, this harness is what makes silent drift impossible: edit one,
    edit both, or CI goes red."""
    root = Path(__file__).parents[2]
    fallback = (root / "persona.md").read_text(encoding="utf-8")
    dna = (root / "shared" / "personas" / "insult.md").read_text(encoding="utf-8")
    assert fallback == dna


def test_insult_guidance_content_is_in_place():
    guidance = Path(__file__).parents[2] / "shared" / "personas" / "guidance" / "insult"
    assert (guidance / "presets" / "preset_vulnerable_overlay.md").is_file()
    assert (guidance / "presets" / "preset_guidance_default_abrasive.md").is_file()


def test_insult_is_gateway_enabled_in_the_registry():
    assert any(p.persona_id == "insult" for p in gateway_personas())


def test_persona_id_by_bot_user_id_maps_registered_bots():
    """Host mention routing can resolve every live sibling bot id deterministically."""
    assert persona_id_by_bot_user_id() == {
        "1488415576551325906": "insult",
        "1512687836766404618": "vultur",
        "1503983124982534284": "alice",
        "1521273256236023989": "frugivoro",
        "1527357397884993677": "unborn_being",
    }


def test_persona_id_by_role_name_resolves_registered_personas():
    """Host role mention routing resolves Discord role names through registry data."""
    assert persona_id_by_role_name("Vultur") == "vultur"
    assert persona_id_by_role_name("Frugívoro") == "frugivoro"
    assert persona_id_by_role_name("Frugivoro") == "frugivoro"
    assert persona_id_by_role_name("Insult") == "insult"


def test_persona_id_by_role_name_unknown_returns_none():
    """RESISTANCE: unknown Discord role names must not force a persona route."""
    assert persona_id_by_role_name("Moderadores") is None
