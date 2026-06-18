"""HOST 5/6 slice A.2 — LLMShadowRouter unit test (no network).

The deterministic shadow (slice A) mirrors the live ``@vultur`` rule by
construction, so it can NEVER diverge — proven in prod (2026-06-18). A GENUINE
divergence needs a router that is NOT identical to the live path: the gpt-4.1
host brain deciding a target independently. This is that router, run in
SHADOW only (logged next to ``current_target``, never acted on, no cutover).

``HostRouterLLM`` is faked so CI never touches Azure / spends.
"""

from __future__ import annotations

import pytest

import demux_ai.llm_shadow_router as llm_shadow_router
from demux_ai.llm_shadow_router import LLMShadowDecision, LLMShadowRouter


class _FakeResult:
    def __init__(self, text: str) -> None:
        self.text = text
        self.input_tokens = 11
        self.output_tokens = 1


class _FakeLLM:
    """Stand-in for HostRouterLLM — records the instruction it was asked, returns
    a canned completion. No Azure, no spend."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[tuple[str, str]] = []

    async def complete(self, instruction: str, user_text: str):
        self.calls.append((instruction, user_text))
        return _FakeResult(self.reply)


@pytest.mark.asyncio
async def test_route_parses_clean_insult():
    router = LLMShadowRouter(llm=_FakeLLM("insult"))
    decision = await router.route("oye qué onda")
    assert isinstance(decision, LLMShadowDecision)
    assert decision.target == "insult"
    assert decision.reason == "llm_insult"
    assert decision.input_tokens == 11
    assert decision.output_tokens == 1


@pytest.mark.asyncio
async def test_route_parses_clean_vultur():
    router = LLMShadowRouter(llm=_FakeLLM("vultur"))
    decision = await router.route("qué peli de terror veo hoy")
    assert decision.target == "vultur"
    assert decision.reason == "llm_vultur"


@pytest.mark.asyncio
async def test_route_loose_match_when_wrapped_in_prose():
    # The model ignored "exactly one word" and wrapped it — we still extract it,
    # but flag the reason as loose so telemetry can tell clean from messy.
    router = LLMShadowRouter(llm=_FakeLLM("I think this should go to vultur."))
    decision = await router.route("reseña de Hereditary")
    assert decision.target == "vultur"
    assert decision.reason == "llm_vultur_loose"


@pytest.mark.asyncio
async def test_route_unparseable_falls_back_to_default_insult():
    router = LLMShadowRouter(llm=_FakeLLM("¯\\_(ツ)_/¯ no idea"))
    decision = await router.route("???")
    assert decision.target == "insult"
    assert decision.reason == "llm_unparseable"


@pytest.mark.asyncio
async def test_route_passes_the_routing_instruction_not_a_persona_prompt():
    fake = _FakeLLM("insult")
    router = LLMShadowRouter(llm=fake)
    await router.route("hola")
    instruction, user_text = fake.calls[0]
    assert user_text == "hola"
    # the host is a router, not a character: the instruction names BOTH targets
    # and asks for a one-word classification, never "be Insult".
    assert "insult" in instruction.lower()
    assert "vultur" in instruction.lower()


def test_valid_targets_mirror_the_registry_in_lockstep():
    # demux_ai must never import personas.*; the target set is mirrored as a
    # constant (parity with shadow_router._VULTUR_PREFIXES) — guard it stays in
    # lockstep with the registered personas + the implicit Insult host.
    from shared.personas.registry import all_personas

    expected = {"insult", *(p.persona_id for p in all_personas())}
    assert set(llm_shadow_router._VALID_TARGETS) == expected
