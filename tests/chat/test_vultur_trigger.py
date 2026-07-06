"""Stage-01 Vultur trigger: @vultur / ~vultur prefix → persona_id routing.

Four required cases (coagent spec):
1. @vultur <text> → persona_id="vultur", text stripped
2. ~vultur <text> → persona_id="vultur", text stripped
3. normal message  → persona_id=None (Insult default)
4. bare trigger (no text after prefix) → persona_id="vultur", text=""

Mutator rules: positive + resistance (normal messages untouched).
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from personas.insult.cogs.chat.pipeline import TurnCtx
from personas.insult.cogs.chat.stages import _stage_bind_identity


def _make_ctx(text: str) -> TurnCtx:
    msg = MagicMock()
    msg.channel.id = 111
    msg.author.id = 222
    msg.author.display_name = "tester"
    msg.guild = None
    msg.channel.name = "general"
    msg.attachments = []
    msg.flags.voice = False
    ctx = TurnCtx(message=msg, text=text, turn_start=time.monotonic(), deps=MagicMock())
    # Both shadow routers OFF by default — a MagicMock attr is truthy, which would
    # otherwise fire the deterministic shadow (Mock route) and spawn an un-awaited
    # LLM-shadow coro. Tests that exercise a shadow opt in explicitly.
    ctx.deps.shadow_route = None
    ctx.deps.llm_shadow_route = None
    # HOST 5/6 slice B cutover handle OFF by default (same MagicMock-truthiness
    # reason). Tests that exercise the cutover opt in explicitly.
    ctx.deps.host_router_cutover = None
    return ctx


@pytest.mark.asyncio
async def test_at_vultur_sets_persona_id():
    ctx = _make_ctx("@vultur reseña Hereditary")
    await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"
    assert ctx.text == "reseña Hereditary"


@pytest.mark.asyncio
async def test_tilde_vultur_sets_persona_id():
    ctx = _make_ctx("~vultur ¿qué piensas de Midsommar?")
    await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"
    assert ctx.text == "¿qué piensas de Midsommar?"


@pytest.mark.asyncio
async def test_normal_message_keeps_insult_default():
    ctx = _make_ctx("oye insult qué onda")
    await _stage_bind_identity(ctx)
    assert ctx.persona_id is None
    assert ctx.text == "oye insult qué onda"


@pytest.mark.asyncio
async def test_bare_trigger_no_text():
    ctx = _make_ctx("@vultur ")
    await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"
    assert ctx.text == ""


# --- HOST 5/6 slice A: shadow router (behavior-neutral + logged) -------------

from structlog.testing import capture_logs  # noqa: E402

from demux_ai.shadow_router import shadow_route  # noqa: E402


def _make_ctx_shadow(text: str, *, route=shadow_route) -> TurnCtx:
    ctx = _make_ctx(text)
    ctx.deps.shadow_route = route
    return ctx


@pytest.mark.asyncio
async def test_shadow_logs_decision_for_normal_message():
    ctx = _make_ctx_shadow("oye insult qué onda")
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    # behavior-neutral: live routing untouched
    assert ctx.persona_id is None
    assert ctx.text == "oye insult qué onda"
    sd = [e for e in logs if e["event"] == "shadow_router_decision"]
    assert len(sd) == 1
    assert sd[0]["current_target"] == "insult"
    assert sd[0]["shadow_target"] == "insult"
    assert sd[0]["diverged"] is False


@pytest.mark.asyncio
async def test_shadow_mirrors_live_vultur_no_divergence():
    # Shadow sees the RAW (pre-strip) text, so it observes the @vultur prefix the
    # same way the live rule did → shadow_target=vultur, diverged=False.
    ctx = _make_ctx_shadow("@vultur reseña Hereditary")
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"
    assert ctx.text == "reseña Hereditary"
    sd = next(e for e in logs if e["event"] == "shadow_router_decision")
    assert sd["current_target"] == "vultur"
    assert sd["shadow_target"] == "vultur"
    assert sd["diverged"] is False


@pytest.mark.asyncio
async def test_shadow_disabled_emits_no_decision():
    ctx = _make_ctx_shadow("hola", route=None)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert not [e for e in logs if e["event"] == "shadow_router_decision"]


@pytest.mark.asyncio
async def test_shadow_fault_is_invisible_to_turn():
    def _boom(_text):
        raise RuntimeError("shadow exploded")

    ctx = _make_ctx_shadow("@vultur dame cine", route=_boom)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    # the turn is unaffected by a shadow fault
    assert ctx.persona_id == "vultur"
    assert ctx.text == "dame cine"
    assert any(e["event"] == "shadow_router_failed" for e in logs)
    assert not [e for e in logs if e["event"] == "shadow_router_decision"]


# --- HOST 5/6 slice A.2: gpt-4.1 LLM shadow router (background + divergence) ---

from types import SimpleNamespace  # noqa: E402

from demux_ai.llm_shadow_router import LLMShadowDecision  # noqa: E402


class _SpawnCapture:
    """Stand-in for ctx.deps.spawn_task — captures the coroutine instead of
    scheduling it, so a test can prove the LLM route runs OFF the critical path
    (deferred) and then drain it deterministically."""

    def __init__(self) -> None:
        self.spawned: list[tuple[str | None, object]] = []

    def __call__(self, coro, name=None) -> None:
        self.spawned.append((name, coro))


def _make_ctx_llm(text: str, *, route, spawn: _SpawnCapture) -> TurnCtx:
    ctx = _make_ctx(text)
    # Real-ish deps: deterministic shadow OFF (None), only the LLM shadow wired.
    ctx.deps = SimpleNamespace(shadow_route=None, llm_shadow_route=route, spawn_task=spawn)
    return ctx


def _fake_route(target: str, reason: str = "llm_x"):
    async def _route(_text: str, _context: str | None = None) -> LLMShadowDecision:
        _route.calls.append((_text, _context))
        return LLMShadowDecision(target=target, reason=reason, input_tokens=7, output_tokens=1)

    _route.calls = []
    return _route


@pytest.mark.asyncio
async def test_llm_shadow_runs_in_background_not_inline():
    # The stage must SPAWN the gpt-4.1 route, never await it inline — the reply
    # cannot wait on routing telemetry.
    spawn = _SpawnCapture()
    ctx = _make_ctx_llm("oye qué onda", route=_fake_route("insult"), spawn=spawn)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert len(spawn.spawned) == 1
    assert spawn.spawned[0][0] == "llm_shadow_router"
    # not awaited yet → no decision logged at stage return (proves it's deferred)
    assert not [e for e in logs if e["event"] == "llm_shadow_router_decision"]
    spawn.spawned[0][1].close()


@pytest.mark.asyncio
async def test_llm_shadow_logs_genuine_divergence():
    # current_target=insult (no prefix), host brain says vultur → diverged=True:
    # the genuine-divergence signal the deterministic shadow can never produce.
    spawn = _SpawnCapture()
    ctx = _make_ctx_llm("recomiéndame algo de Lynch", route=_fake_route("vultur", "llm_vultur"), spawn=spawn)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
        assert ctx.persona_id is None  # behavior-neutral: live routing untouched
        await spawn.spawned[0][1]  # drain the background coro
    d = next(e for e in logs if e["event"] == "llm_shadow_router_decision")
    assert d["current_target"] == "insult"
    assert d["llm_shadow_target"] == "vultur"
    assert d["llm_shadow_reason"] == "llm_vultur"
    assert d["llm_diverged"] is True
    assert d["llm_input_tokens"] == 7


@pytest.mark.asyncio
async def test_llm_shadow_agreement_is_not_divergence():
    spawn = _SpawnCapture()
    ctx = _make_ctx_llm("hola insult", route=_fake_route("insult", "llm_insult"), spawn=spawn)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
        await spawn.spawned[0][1]
    d = next(e for e in logs if e["event"] == "llm_shadow_router_decision")
    assert d["llm_diverged"] is False


@pytest.mark.asyncio
async def test_llm_shadow_disabled_emits_no_spawn():
    spawn = _SpawnCapture()
    ctx = _make_ctx_llm("hola", route=None, spawn=spawn)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert spawn.spawned == []
    assert not [e for e in logs if e["event"] == "llm_shadow_router_decision"]


@pytest.mark.asyncio
async def test_llm_shadow_fault_is_invisible_to_turn():
    async def _boom(_text, _context=None):
        raise RuntimeError("azure exploded")

    spawn = _SpawnCapture()
    ctx = _make_ctx_llm("@vultur dame cine", route=_boom, spawn=spawn)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
        # the turn is unaffected — live routing already sent it to vultur
        assert ctx.persona_id == "vultur"
        await spawn.spawned[0][1]  # drain: must not raise
    assert any(e["event"] == "llm_shadow_router_failed" for e in logs)
    assert not [e for e in logs if e["event"] == "llm_shadow_router_decision"]


@pytest.mark.asyncio
async def test_llm_shadow_skips_empty_input():
    # Gap B (rev161 autopsy): an attachment-only / empty-text turn was reaching the
    # gpt-4.1 router, which needs a non-empty user_message and threw a spurious
    # error-level ValueError. The stage must SKIP the LLM shadow on empty input
    # (no spawn) and log llm_shadow_router_skipped reason="empty_input" at non-error
    # level — keeping the error rate clean for A.2.3 direct-only measurement.
    spawn = _SpawnCapture()
    ctx = _make_ctx_llm("   ", route=_fake_route("insult"), spawn=spawn)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert spawn.spawned == []
    skipped = [e for e in logs if e["event"] == "llm_shadow_router_skipped"]
    assert len(skipped) == 1
    assert skipped[0]["reason"] == "empty_input"
    assert skipped[0]["log_level"] != "error"


@pytest.mark.asyncio
async def test_llm_shadow_still_runs_on_normal_text():
    # Resistance case: a normal non-empty message must STILL spawn the shadow and
    # emit NO skip — the empty-input guard must not suppress real routing telemetry.
    spawn = _SpawnCapture()
    ctx = _make_ctx_llm("recomiéndame algo", route=_fake_route("insult"), spawn=spawn)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert len(spawn.spawned) == 1
    assert spawn.spawned[0][0] == "llm_shadow_router"
    assert not [e for e in logs if e["event"] == "llm_shadow_router_skipped"]
    spawn.spawned[0][1].close()


class _FakeRouterMemory:
    """Stand-in for the shared MemoryStore — canned recent rows, records calls."""

    def __init__(self, rows: list[dict] | None = None, boom: bool = False) -> None:
        self.rows = rows or []
        self.boom = boom
        self.calls: list[tuple[str, int]] = []

    async def get_recent(self, channel_id: str, limit: int = 20, user_id=None) -> list[dict]:
        self.calls.append((channel_id, limit))
        if self.boom:
            raise RuntimeError("pg down")
        return self.rows


@pytest.mark.asyncio
async def test_llm_shadow_routes_with_recent_channel_context():
    """HOST paso 2 (P0 2026-07-06): the router must see the channel's recent
    conversation — Alex's bare pantry list mid-fruit-conversation routed
    default_insult because the brain saw the message ALONE. The background task
    fetches recent messages (off the critical path) and forwards them to route."""
    spawn = _SpawnCapture()
    route = _fake_route("frugivoro", "llm_frugivoro")
    ctx = _make_ctx_llm("Avena\nChía\nZanahorias", route=route, spawn=spawn)
    memory = _FakeRouterMemory(
        rows=[
            {"user_name": "bernard2389", "content": "dile a frugi lo que tienes"},
            {"user_name": "Frugívoro", "content": "compárteme tu inventario"},
        ]
    )
    ctx.deps.memory = memory
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
        await spawn.spawned[0][1]
    text, context = route.calls[0]
    assert text == "Avena\nChía\nZanahorias"
    assert "bernard2389: dile a frugi lo que tienes" in context
    assert "Frugívoro: compárteme tu inventario" in context
    assert memory.calls, "the background task must fetch recent channel messages"
    d = next(e for e in logs if e["event"] == "llm_shadow_router_decision")
    assert d["llm_shadow_target"] == "frugivoro"
    assert d["route_context_chars"] > 0


@pytest.mark.asyncio
async def test_llm_shadow_context_fetch_fault_still_routes_without_context():
    # Resistance case: a memory fault must NOT kill the routing decision — the
    # shadow routes context-less (None) and logs the fetch failure.
    spawn = _SpawnCapture()
    route = _fake_route("insult", "llm_insult")
    ctx = _make_ctx_llm("hola qué onda", route=route, spawn=spawn)
    ctx.deps.memory = _FakeRouterMemory(boom=True)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
        await spawn.spawned[0][1]
    text, context = route.calls[0]
    assert text == "hola qué onda"
    assert context is None
    assert any(e["event"] == "llm_router_context_fetch_failed" for e in logs)
    d = next(e for e in logs if e["event"] == "llm_shadow_router_decision")
    assert d["route_context_chars"] == 0


# --- HOST 5/6 slice B: deterministic CUTOVER (flag-off no-op + flag-on routes) ---
#
# A cutover handle is a callable ``(live_persona_id, raw_text) -> str | None`` that
# returns the persona the turn should run as. It is wired ONLY when
# host_router_cutover_enabled (default False) AND the deterministic shadow is on.
# When the handle is None (the default), routing is byte-identical to today.


def _make_ctx_cutover(text: str, *, cutover, route=shadow_route) -> TurnCtx:
    ctx = _make_ctx(text)
    ctx.deps.shadow_route = route
    ctx.deps.host_router_cutover = cutover
    return ctx


def _det_cutover(live_persona_id, raw_text):
    # The real handle composition builds: apply_cutover(live, shadow_route(raw)).
    from demux_ai.shadow_router import apply_cutover

    return apply_cutover(live_persona_id=live_persona_id, decision=shadow_route(raw_text))


@pytest.mark.asyncio
async def test_cutover_off_is_behavior_neutral_for_vultur():
    # Flag off (handle None) → routing untouched, even on a @vultur turn. The shadow
    # still logs (slice A) but NOTHING acts on it.
    ctx = _make_ctx_cutover("@vultur reseña Hereditary", cutover=None)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"  # set by the LIVE rule, not the cutover
    assert ctx.text == "reseña Hereditary"
    assert not [e for e in logs if e["event"].startswith("host_router_cutover")]


@pytest.mark.asyncio
async def test_cutover_off_is_behavior_neutral_for_insult():
    ctx = _make_ctx_cutover("oye insult qué onda", cutover=None)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert ctx.persona_id is None
    assert not [e for e in logs if e["event"].startswith("host_router_cutover")]


@pytest.mark.asyncio
async def test_cutover_on_routes_per_decision_vultur():
    # Flag ON: the deterministic cutover sets persona_id. Today it equals the live
    # rule (vultur) — a true no-op result — but it is now the CUTOVER that set it.
    ctx = _make_ctx_cutover("@vultur reseña Hereditary", cutover=_det_cutover)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"
    ev = next(e for e in logs if e["event"] == "host_router_cutover_applied")
    assert ev["live_persona_id"] == "vultur"
    assert ev["cutover_persona_id"] == "vultur"
    assert ev["diverged"] is False


@pytest.mark.asyncio
async def test_cutover_on_routes_per_decision_insult():
    ctx = _make_ctx_cutover("oye insult qué onda", cutover=_det_cutover)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert ctx.persona_id is None
    ev = next(e for e in logs if e["event"] == "host_router_cutover_applied")
    assert ev["live_persona_id"] is None
    assert ev["cutover_persona_id"] is None
    assert ev["diverged"] is False


@pytest.mark.asyncio
async def test_cutover_can_change_routing_when_decision_differs():
    # Prove the seam ACTUALLY routes: a (hypothetical future) cutover that disagrees
    # with the live rule changes persona_id. Slice B's deterministic handle never
    # does this today, but the mechanism must be able to.
    def _force_vultur(_live, _raw):
        return "vultur"

    ctx = _make_ctx_cutover("oye insult qué onda", cutover=_force_vultur)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"  # live rule said None; cutover overrode it
    ev = next(e for e in logs if e["event"] == "host_router_cutover_applied")
    assert ev["live_persona_id"] is None
    assert ev["cutover_persona_id"] == "vultur"
    assert ev["diverged"] is True


@pytest.mark.asyncio
async def test_cutover_fault_falls_back_to_live_rule():
    # A cutover fault must NEVER break the turn — persona_id stays as the live rule
    # set it, and a host_router_cutover_failed event is logged.
    def _boom(_live, _raw):
        raise RuntimeError("cutover exploded")

    ctx = _make_ctx_cutover("@vultur dame cine", cutover=_boom)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
    assert ctx.persona_id == "vultur"  # live rule's value preserved
    assert ctx.text == "dame cine"
    assert any(e["event"] == "host_router_cutover_failed" for e in logs)
    assert not [e for e in logs if e["event"] == "host_router_cutover_applied"]
