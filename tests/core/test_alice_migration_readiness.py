"""ALICE migration readiness (PR-4c) — registry + gate + DNA, NOT cutover.

ALICE is being migrated from a separate gpt-4.1 bot (`personas/alice/`, the
`alice-bot` Container App) to a Claude sibling persona on the persona-runner,
addressed by `persona_id="alice"` like Vultur. This file pins the READINESS
invariants that must hold BEFORE the single-owner cutover:

- ALICE is registered (the runner can load her DNA, Insult suppresses her) but
  `gateway_enabled=False`, so `persona_gateway` does NOT spin her up while
  alice-bot still owns the ALICE_DISCORD_TOKEN — the "no two ALICEs" rule.
- Her DNA file exists and PRESERVES the crisis-handling at the prompt level
  (the dormant deterministic triage stays parked, but the patient-facing crisis
  referral must never be lost in the move).

The cutover itself (flip gateway_enabled, move the token, retire alice-bot) is
gated on a live host-router failover replacement — out of scope here.
"""

from __future__ import annotations

from pathlib import Path

from shared.personas import all_personas, gateway_personas, get_persona
from shared.personas.registry import sibling_aliases, sibling_bot_user_ids

ALICE_MD = Path(__file__).resolve().parents[2] / "shared" / "personas" / "alice.md"


def test_alice_is_registered():
    alice = get_persona("alice")
    assert alice is not None
    assert alice.persona_id == "alice"
    assert alice.persona_file == "alice.md"
    assert alice.token_env == "ALICE_DISCORD_TOKEN"  # noqa: S105 — env var NAME, not a secret
    assert alice.bot_user_id  # known to Insult's suppression


def test_alice_gate_off_gateway_does_not_start_her():
    # The cutover gate: registry knows ALICE, but the gateway must NOT spin her
    # up yet (alice-bot still owns the token). RESISTANCE against "two ALICEs".
    alice = get_persona("alice")
    assert alice is not None and alice.gateway_enabled is False
    started_ids = {p.persona_id for p in gateway_personas()}
    assert "alice" not in started_ids
    assert "vultur" in started_ids  # the enabled sibling still starts


def test_alice_known_to_suppression_despite_gate():
    # Insult must stay silent when ALICE is addressed — suppression reads the
    # FULL registry, not just the gateway-enabled subset.
    assert "alice" in {p.persona_id for p in all_personas()}
    alice = get_persona("alice")
    assert alice is not None and alice.bot_user_id in sibling_bot_user_ids()
    assert "alice" in sibling_aliases()


def test_alice_dna_exists_and_is_alice_not_insult():
    text = ALICE_MD.read_text(encoding="utf-8")
    assert text.startswith("# ALICE")
    assert "No eres Insult" in text  # voice boundary preserved


def test_alice_dna_preserves_crisis_referral():
    # LOAD-BEARING: the patient-facing crisis handling (MX hotlines) must survive
    # the move to Claude. The deterministic clinical triage stays parked; this
    # prompt-level referral is the safety net that ships with the persona.
    text = ALICE_MD.read_text(encoding="utf-8")
    assert "SAPTEL" in text
    assert "Línea de la Vida" in text
    assert "55 5259-8121" in text


def test_alice_dna_drops_failover_plumbing_narration():
    # As a sibling she is mention-gated; the gpt-4.1 FAILOVER/invite mechanics are
    # plumbing that must NOT leak into the Claude persona prompt.
    text = ALICE_MD.read_text(encoding="utf-8")
    assert "FAILOVER" not in text
    assert "/invite" not in text
