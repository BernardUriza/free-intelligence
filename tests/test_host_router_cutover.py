"""HOST 5/6 slice B — the CUTOVER policy unit test (pure, no network).

Slice A logged what the deterministic host router WOULD route to; slice B is the
first cut where the host router's decision can ACTUALLY route the turn. The pure
policy ``apply_cutover`` answers ONE question: given the live rule's chosen
persona and the deterministic shadow decision, what persona should the turn run
as under cutover?

Slice B cuts over ONLY the deterministic shadow (instant, zero added latency).
Because the deterministic shadow mirrors the live ``@vultur`` rule by
construction (proven in prod 2026-06-18: it can never diverge), the cutover
result is byte-identical to the live rule today — a TRUE structural no-op that
proves the routing seam works without behavior change (textbook strangler-fig
first cut). The gpt-4.1 LLM router stays shadow-only.
"""

from __future__ import annotations

from demux_ai.shadow_router import ShadowDecision, apply_cutover, shadow_route


def test_cutover_default_insult_keeps_none() -> None:
    # live rule chose Insult (None); deterministic shadow agrees → still Insult.
    decision = ShadowDecision(target="insult", reason="default_insult")
    assert apply_cutover(live_persona_id=None, decision=decision) is None


def test_cutover_vultur_routes_to_vultur() -> None:
    decision = ShadowDecision(target="vultur", reason="vultur_prefix")
    assert apply_cutover(live_persona_id="vultur", decision=decision) == "vultur"


def test_cutover_mirrors_live_rule_for_every_input() -> None:
    # The slice-B invariant: for the deterministic shadow, the cutover target ALWAYS
    # equals what the live @vultur rule would have set. So acting on it is a no-op.
    cases = [
        ("oye insult qué onda", None),
        ("@vultur reseña Hereditary", "vultur"),
        ("~vultur dame algo de Lynch", "vultur"),
        ("@vultur ", "vultur"),
        ("normal text", None),
    ]
    for raw_text, live_persona in cases:
        decision = shadow_route(raw_text)
        assert apply_cutover(live_persona_id=live_persona, decision=decision) == live_persona
