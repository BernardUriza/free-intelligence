"""The host's gpt-4.1 router — ``DirectAzureLLMRouter`` unit tests (no network).

Born as a shadow (HOST 5/6 slice A.2, 2026-06-18), THE router since the cutover
of 2026-07-08: the decision it emits is where the turn goes. The Azure client is
faked so CI never touches Azure / spends.

(The agentic ``LLMShadowRouter`` and its ``_FakeLLM`` lived here until
2026-09-23; the class had been constructed only by this file since v4.21.82.
The parser behaviors its tests pinned — loose match, unparseable fallback,
first-line match with trailing prose, bare payload without context — are live
behaviors of the direct router and are pinned on it below.)
"""

from __future__ import annotations

import pytest
import structlog

import demux_ai.llm_shadow_router as llm_shadow_router
from demux_ai.llm_shadow_router import DirectAzureLLMRouter, LLMShadowDecision

# --- DirectAzureLLMRouter: the live transport (slice A.2 token-bloat fix) -----


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
async def test_direct_route_returns_a_decision_the_dispatcher_can_read():
    # the contract `demux_ai.dispatch` consumes: `.route(text)` → a decision with
    # `.target` and a greppable `.reason`.
    direct = await DirectAzureLLMRouter(client=_FakeAzureClient("insult")).route("x")
    assert isinstance(direct, LLMShadowDecision)
    assert direct.target == "insult"
    assert direct.reason == "llm_insult"


@pytest.mark.asyncio
async def test_direct_route_parses_clean_frugivoro():
    decision = await DirectAzureLLMRouter(client=_FakeAzureClient("frugivoro")).route(
        "qué hago de cenar con lentejas y espinacas?"
    )
    assert decision.target == "frugivoro"
    assert decision.reason == "llm_frugivoro"


@pytest.mark.asyncio
async def test_direct_route_loose_match_when_wrapped_in_prose():
    # The model ignored "exactly one word" and wrapped it — we still extract it,
    # but flag the reason as loose so telemetry can tell clean from messy.
    decision = await DirectAzureLLMRouter(client=_FakeAzureClient("I think this should go to vultur.")).route(
        "reseña de Hereditary"
    )
    assert decision.target == "vultur"
    assert decision.reason == "llm_vultur_loose"


@pytest.mark.asyncio
async def test_direct_route_unparseable_falls_back_to_default_insult():
    decision = await DirectAzureLLMRouter(client=_FakeAzureClient("¯\\_(ツ)_/¯ no idea")).route("???")
    assert decision.target == llm_shadow_router.DEFAULT_TARGET
    assert decision.reason == "llm_unparseable"


@pytest.mark.asyncio
async def test_direct_route_with_context_composes_recent_block():
    """HOST paso 2 (P0 2026-07-06): Alex's bare pantry list mid-fruit-conversation
    routed default_insult because the router saw the message ALONE. With context,
    the recent-conversation block rides above the current message."""
    client = _FakeAzureClient("frugivoro")
    router = DirectAzureLLMRouter(client=client)
    context = (
        "bernard2389: dile a frugi que tienes ahorita para que no alucine con el tahini\n"
        "Frugívoro: perfecto, compárteme tu inventario y armamos el menú"
    )
    await router.route("Avena\nChía\nZanahorias\nJitomate", context)
    user_text = client.calls[0]["messages"][1]["content"]
    assert "Recent channel conversation" in user_text
    assert "dile a frugi" in user_text
    assert "Current message to route:" in user_text
    assert user_text.endswith("Avena\nChía\nZanahorias\nJitomate")


@pytest.mark.asyncio
async def test_direct_route_without_context_is_byte_identical_to_before():
    # Resistance case: no context → the payload is the bare message, so existing
    # telemetry windows stay comparable (no silent input-shape change).
    client = _FakeAzureClient("insult")
    await DirectAzureLLMRouter(client=client).route("hola")
    assert client.calls[0]["messages"][1]["content"] == "hola"


def test_routing_instruction_names_every_routable_persona():
    """The 2026-07-06 root: _VALID_TARGETS knew frugivoro but the INSTRUCTION only
    offered insult|vultur, so the brain literally could not pick frugivoro. Every
    valid target must be described in the instruction the model actually reads."""
    instr = llm_shadow_router._routing_instruction().lower()
    for target in llm_shadow_router._VALID_TARGETS:
        assert target in instr, f"routing instruction never mentions {target!r}"


def test_routing_instruction_encodes_continuation_rule():
    """Pin the context rule: a continuation of a specialist's exchange routes to
    that specialist (the founding P0 case: pantry list mid-fruit-conversation)."""
    instr = llm_shadow_router._routing_instruction().lower()
    assert "continuation" in instr
    assert "inventory" in instr  # the founding example rides in the instruction


def test_routing_instruction_keeps_food_mere_mention_with_insult():
    # Resistance case (mutator rule): casually mentioning food must NOT route to
    # frugivoro — the mere-mention counter-example is pinned like Netflix's.
    instr = llm_shadow_router._routing_instruction().lower()
    assert "tacos" in instr
    assert "mere mention of food" in instr


def test_routing_instruction_continuation_overrides_specialty_gates():
    """The 2026-07-07 P0: mid-exchange with vultur about non-binary identity,
    'Eres un buitre no-cis. Entonces.' routed insult because the specialty gate
    ('vultur ONLY when seeking film expertise') dominated the continuation clause.
    The continuation rule must outrank every specialty gate and say so explicitly,
    with the founding vultur case pinned as an example."""
    instr = llm_shadow_router._routing_instruction().lower()
    assert "regardless of topic" in instr
    assert "no-cis" in instr
    assert "presagio" in instr  # the second-participant continuation (Alex, 17:23)


def test_routing_instruction_maps_display_names_to_targets():
    # Context lines carry Discord display names ("Vultur Analytica"), not target
    # tokens ("vultur") — the brain needs the mapping to see who holds the floor.
    instr = llm_shadow_router._routing_instruction().lower()
    assert "vultur analytica" in instr
    assert "a.l.i.c.e." in instr
    assert "frugívoro" in instr


def test_routing_instruction_closed_exchange_returns_to_insult():
    # Resistance case: continuation must not become sticky forever — a life
    # update long after a specialist exchange closed stays with the host.
    instr = llm_shadow_router._routing_instruction().lower()
    assert "mason jar" in instr
    assert "exchange closed" in instr


def test_routing_instruction_loads_from_content_file_not_inline():
    """prompts-as-content-not-code (P0, playbook SSOT): the routing prompt lives
    in demux_ai/prompts/host_routing.md behind the mtime-aware persona_core
    loader — never as an inline Python constant requiring a redeploy to tune."""
    assert not hasattr(llm_shadow_router, "_ROUTING_INSTRUCTION")
    assert (llm_shadow_router._PROMPTS_DIR / "host_routing.md").exists()


def test_valid_targets_mirror_the_registry_in_lockstep():
    # demux_ai must never import personas.*; the target set is mirrored as a
    # constant — guard it stays in lockstep with the registered personas + the
    # implicit Insult host.
    from shared.personas.registry import all_personas

    expected = {"insult", *(p.persona_id for p in all_personas())}
    assert set(llm_shadow_router._VALID_TARGETS) == expected


def test_routing_instruction_encodes_intent_not_mention():
    """Guard the false-positive fix (2026-06-21): the router must route on INTENT,
    not on a topic word appearing. Someone reverting to keyword-matching ('mentions
    a movie -> vultur') would re-introduce the misroute Bernard hit. Pin the
    discriminating language + the mention counter-examples."""
    instr = llm_shadow_router._routing_instruction().lower()
    assert "intent" in instr
    assert "passing" in instr  # "mentioning ... in passing is NOT enough"
    assert "recommend" in instr or "recomi" in instr  # the seeking-expertise signal
    assert "netflix" in instr  # the exact false-positive trigger, now a counter-example


@pytest.mark.asyncio
async def test_a_reply_with_extra_prose_after_the_word_still_clean_matches():
    """Lo único que valía la pena de los seis tests de `effort` borrados el
    2026-08-06: el parser matchea la PRIMERA LÍNEA, no el texto entero, así que
    un modelo que se pone charlatán después de la palabra sigue dando un
    clean match en vez de degradar a `_loose`."""
    decision = await DirectAzureLLMRouter(client=_FakeAzureClient("insult\nporque es un desahogo personal")).route(
        "investígame con rigor el barrio bravo"
    )
    assert decision.target == "insult"
    assert decision.reason == "llm_insult"


def test_the_prompt_asks_for_one_word_only():
    """El prompt pedía DOS líneas (persona + effort). El effort se borró de los
    dos lados; si el formato vuelve a pedir dos líneas sin consumidor, este test
    y el arnés de tests/arch/ lo cazan."""
    instr = llm_shadow_router._routing_instruction().lower()
    assert "one lowercase word" in instr
    assert "effort" not in instr


def test_routing_instruction_gives_personal_disclosure_back_to_the_host():
    """Guard the misroute the offline eval caught (2026-07-09, 1/30 real #general
    messages): right after frugivoro explained gut physiology, Bernard opened a new
    topic — "hoy en mis trabajos he sentido mucha presión, ¿sabes cómo?" — and the
    router handed that confession to the nutritionist, because frugivoro had spoken
    one line earlier. A specialist speaking last does not own a change of subject,
    and emotional weight is the host's whole reason to exist. Pin both halves."""
    instr = llm_shadow_router._routing_instruction().lower()
    assert "does not keep the floor" in instr
    assert "disclosure" in instr
    assert "presión" in instr  # the counter-example, verbatim from the eval


# --- Observability: the ONLY live router must log its own decision -----------
# The A.2.3 window went dark post-cutover because `host_router_llm_response`
# lived only in the retired Codex backend — the DirectAzureLLMRouter routed
# 100+ turns with zero latency/token telemetry. These pin the emitter to the
# live path so the measurement window has an instrument.


class _ExplodingCompletions:
    async def create(self, **kwargs):
        raise RuntimeError("azure down")


@pytest.mark.asyncio
async def test_direct_route_logs_host_router_llm_response():
    client = _FakeAzureClient("vultur", prompt_tokens=142, completion_tokens=1)
    router = DirectAzureLLMRouter(client=client)
    with structlog.testing.capture_logs() as logs:
        await router.route("reseña de Hereditary")
    events = [entry for entry in logs if entry["event"] == "host_router_llm_response"]
    assert len(events) == 1
    entry = events[0]
    assert entry["target"] == "vultur"
    assert entry["input_tokens"] == 142
    assert entry["output_tokens"] == 1
    assert entry["backend"] == "azure_direct"
    assert isinstance(entry["latency_ms"], int)
    assert entry["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_direct_route_logs_host_router_llm_error_and_reraises():
    client = _FakeAzureClient("insult")
    client.chat.completions = _ExplodingCompletions()
    router = DirectAzureLLMRouter(client=client)
    with structlog.testing.capture_logs() as logs, pytest.raises(RuntimeError):
        await router.route("hola")
    events = [entry for entry in logs if entry["event"] == "host_router_llm_error"]
    assert len(events) == 1
    assert events[0]["error_type"] == "RuntimeError"
    assert events[0]["backend"] == "azure_direct"


class _ContentFilterError(Exception):
    """Shape of the Azure 400 the content filter raises (openai.BadRequestError
    carries ``code='content_filter'`` and this message verbatim)."""

    code = "content_filter"

    def __init__(self) -> None:
        super().__init__(
            "Error code: 400 - {'error': {'message': \"The response was filtered due to "
            "the prompt triggering Azure OpenAI's content management policy.\"}}"
        )


class _FilteringCompletions:
    """Rejects any prompt carrying the recent-conversation block, answers a bare
    message — the real 2026-08-06 failure: an inert 'explica mejor lo anterior'
    died because the WINDOW behind it mentioned drugs, not the message itself."""

    def __init__(self, reply: str, filter_bare: bool = False) -> None:
        self.reply = reply
        self.filter_bare = filter_bare
        self.calls: list[str] = []

    async def create(self, *, model, messages, **kwargs):
        user_text = messages[1]["content"]
        self.calls.append(user_text)
        if self.filter_bare or "Recent channel conversation" in user_text:
            raise _ContentFilterError()
        return _FakeCompletion(self.reply, 40, 1)


@pytest.mark.asyncio
async def test_content_filtered_context_retries_without_it_and_keeps_the_real_target():
    """A poisoned context must not cost the routing DECISION. Dropping the window
    and re-asking recovers the target the brain would have picked all along."""
    client = _FakeAzureClient("vultur")
    completions = _FilteringCompletions("vultur")
    client.chat.completions = completions
    router = DirectAzureLLMRouter(client=client)

    with structlog.testing.capture_logs() as logs:
        decision = await router.route("explica mejor lo anterior", context="bernard: fumo un porro")

    assert decision.target == "vultur"
    assert decision.reason == "llm_vultur"
    assert len(completions.calls) == 2
    assert "Recent channel conversation" in completions.calls[0]
    assert completions.calls[1] == "explica mejor lo anterior"
    filtered = [e for e in logs if e["event"] == "host_router_content_filtered"]
    assert filtered and filtered[0]["recovered_without_context"] is True


@pytest.mark.asyncio
async def test_content_filtered_message_falls_back_to_default_target_never_silence():
    """RESISTANCE: when even the bare message is filtered, the brain has no
    opinion — that is the SAME case as an unparseable reply, so it takes the same
    default. Raising here reached the host as total silence in prod."""
    client = _FakeAzureClient("insult")
    completions = _FilteringCompletions("insult", filter_bare=True)
    client.chat.completions = completions
    router = DirectAzureLLMRouter(client=client)

    with structlog.testing.capture_logs() as logs:
        decision = await router.route("algo", context="contexto")

    assert decision.target == llm_shadow_router.DEFAULT_TARGET
    assert decision.reason == "llm_content_filtered"
    assert len(completions.calls) == 2
    filtered = [e for e in logs if e["event"] == "host_router_content_filtered"]
    assert filtered and filtered[-1]["recovered_without_context"] is False


@pytest.mark.asyncio
async def test_non_filter_api_error_still_raises_and_is_not_retried():
    """RESISTANCE: the content-filter recovery must not swallow a transport
    failure — a timeout is not a brain declining to answer, it stays loud and is
    never re-sent (that would double the spend on every Azure blip)."""
    client = _FakeAzureClient("insult")
    client.chat.completions = _ExplodingCompletions()
    router = DirectAzureLLMRouter(client=client)
    with pytest.raises(RuntimeError):
        await router.route("hola", context="ctx")


class TestRouterBudgetIsEnforced:
    """El cap de $5/semana que Bernard autorizó (d194292, 2026-06-21) dejó de
    cumplirse cuando la purga se llevó a su único llamador: `RouterBudget` quedó
    intacto en el árbol, con cero consumidores, mientras el router seguía
    gastando. Un mes en producción sin tope y sin una sola señal roja — el módulo
    escrito para no hacer fake-green era él mismo un fake-green.

    Estos tests son el mecanismo que faltaba: si alguien vuelve a desconectar el
    cap, se ponen rojos."""

    @pytest.mark.asyncio
    async def test_over_the_cap_it_degrades_instead_of_calling_azure(self):
        from demux_ai.router_budget import RouterBudget

        spent = RouterBudget(weekly_cap_usd=0.0001)
        spent.record(1_000_000, 1_000_000)
        client = _FakeAzureClient("vultur")
        decision = await DirectAzureLLMRouter(client=client, budget=spent).route("reseña de Dune")

        assert decision.target == "insult", "rebasar el cap debe degradar al default, no elegir persona"
        assert decision.reason == "llm_budget_exceeded"

    @pytest.mark.asyncio
    async def test_under_the_cap_it_routes_normally(self):
        from demux_ai.router_budget import RouterBudget

        decision = await DirectAzureLLMRouter(
            client=_FakeAzureClient("vultur"), budget=RouterBudget(weekly_cap_usd=5.0)
        ).route("reseña de Dune")

        assert decision.target == "vultur"
        assert decision.reason == "llm_vultur"

    @pytest.mark.asyncio
    async def test_every_call_is_charged_to_the_week(self):
        """Sin `record` el contador nunca sube y el cap no puede morder jamás —
        que es exactamente el estado en el que estuvo un mes."""
        from demux_ai.router_budget import RouterBudget

        budget = RouterBudget(weekly_cap_usd=5.0)
        assert budget.spent_this_week() == 0.0
        await DirectAzureLLMRouter(client=_FakeAzureClient("insult"), budget=budget).route("hola")
        assert budget.spent_this_week() > 0.0
