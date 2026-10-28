"""Astra (2026-10-28) — the PlusvalíaLeaks script coagent, registered for og118.

Positive: she exists in the registry with her DNA and rides AIRE's Codex backend
on GPT-6 Astra (aire-server #49/#52). Resistance: registering her opened NO
Discord door — no gateway bot, no alias — and left every Claude persona on the
per-turn router exactly as before.
"""

from __future__ import annotations

from pathlib import Path

from persona_runner.engine.aire_route import engine_for
from shared.personas import gateway_personas, get_persona

ROOT = Path(__file__).parents[2]


def test_astra_is_a_registered_persona_on_codex():
    a = get_persona("astra")
    assert a is not None
    assert a.persona_file == "astra.md"
    assert a.provider == "codex"
    assert a.model == "gpt-6-astra"


def test_astra_dna_is_the_verbatim_script_coagent_prompt():
    dna = ROOT / "shared" / "personas" / "astra.md"
    assert dna.is_file()
    text = dna.read_text(encoding="utf-8")
    assert "PlusvalíaLeaks" in text
    assert len(text) > 1000


def test_astra_has_no_discord_door():
    a = get_persona("astra")
    assert a.gateway_enabled is False
    assert a.aliases == []
    assert all(p.persona_id != "astra" for p in gateway_personas())


def test_engine_for_pins_astra_and_leaves_claude_personas_to_the_router():
    assert engine_for("astra") == ("codex", "gpt-6-astra")
    assert engine_for("insult") == ("claude", None)
    assert engine_for("vultur") == ("claude", None)
    assert engine_for("no-such-persona") == ("claude", None)


def test_every_other_persona_still_defaults_to_claude():
    from shared.personas import all_personas

    others = [p for p in all_personas() if p.persona_id != "astra"]
    assert others
    assert all(p.provider == "claude" and p.model is None for p in others)
