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
from demux_ai.llm_shadow_router import DirectAzureLLMRouter, LLMShadowDecision, LLMShadowRouter


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


# --- DirectAzureLLMRouter: the cheap transport (slice A.2 token-bloat fix) -----


class _FakeUsage:
    def __init__(self, prompt: int, completion: int) -> None:
        self.prompt_tokens = prompt
        self.completion_tokens = completion


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeCompletion:
    def __init__(self, content: str, prompt: int, completion: int) -> None:
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage(prompt, completion)


class _FakeCompletions:
    def __init__(self, parent: _FakeAzureClient) -> None:
        self._parent = parent

    async def create(self, *, model, messages, **kwargs):
        self._parent.calls.append({"model": model, "messages": messages, "kwargs": kwargs})
        return _FakeCompletion(self._parent.reply, self._parent.prompt_tokens, self._parent.completion_tokens)


class _FakeChat:
    def __init__(self, parent: _FakeAzureClient) -> None:
        self.completions = _FakeCompletions(parent)


class _FakeAzureClient:
    """Stand-in for openai.AsyncAzureOpenAI — no Azure, no spend."""

    def __init__(self, reply: str, prompt_tokens: int = 142, completion_tokens: int = 1) -> None:
        self.reply = reply
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.calls: list[dict] = []
        self.chat = _FakeChat(self)


@pytest.mark.asyncio
async def test_direct_route_parses_and_reports_real_prompt_tokens():
    client = _FakeAzureClient("vultur", prompt_tokens=142, completion_tokens=1)
    router = DirectAzureLLMRouter(client=client)
    decision = await router.route("reseña de Hereditary")
    assert decision.target == "vultur"
    assert decision.reason == "llm_vultur"
    # the whole point: the direct path reports the REAL prompt_tokens (hundreds,
    # not the agentic ~9.5k) — usage.prompt_tokens flows straight through.
    assert decision.input_tokens == 142
    assert decision.output_tokens == 1


@pytest.mark.asyncio
async def test_direct_route_sends_only_instruction_plus_input_no_agent_harness():
    client = _FakeAzureClient("insult")
    router = DirectAzureLLMRouter(client=client)
    await router.route("hola")
    call = client.calls[0]
    # exactly two messages: the routing instruction (system) + the user input.
    # No tool schemas, no agent scaffold — that's why it's cheap.
    roles = [m["role"] for m in call["messages"]]
    assert roles == ["system", "user"]
    assert call["messages"][1]["content"] == "hola"
    assert "vultur" in call["messages"][0]["content"].lower()


@pytest.mark.asyncio
async def test_direct_route_is_shape_compatible_with_agentic():
    # same contract → drops into TurnRuntimeDeps.llm_shadow_route behind the seam.
    direct = await DirectAzureLLMRouter(client=_FakeAzureClient("insult")).route("x")
    assert isinstance(direct, LLMShadowDecision)
    assert direct.reason == "llm_insult"


def test_valid_targets_mirror_the_registry_in_lockstep():
    # demux_ai must never import personas.*; the target set is mirrored as a
    # constant (parity with shadow_router._VULTUR_PREFIXES) — guard it stays in
    # lockstep with the registered personas + the implicit Insult host.
    from shared.personas.registry import all_personas

    expected = {"insult", *(p.persona_id for p in all_personas())}
    assert set(llm_shadow_router._VALID_TARGETS) == expected


def test_routing_instruction_encodes_intent_not_mention():
    """Guard the false-positive fix (2026-06-21): the router must route on INTENT,
    not on a topic word appearing. Someone reverting to keyword-matching ('mentions
    a movie -> vultur') would re-introduce the misroute Bernard hit. Pin the
    discriminating language + the mention counter-examples."""
    instr = llm_shadow_router._ROUTING_INSTRUCTION.lower()
    assert "intent" in instr
    assert "passing" in instr  # "mentioning ... in passing is NOT enough"
    assert "recommend" in instr or "recomi" in instr  # the seeking-expertise signal
    assert "netflix" in instr  # the exact false-positive trigger, now a counter-example
