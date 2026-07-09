"""Stage-01 bind-identity: the gpt-4.1 LLM SHADOW router (HOST 5/6 slice A.2).

Prefix addressing (`@vultur ` / `~vultur ` as literal TEXT) was RETIRED on
2026-07-08, closing the strangler-fig once the gpt-4.1 cutover went live. With it
went the deterministic shadow (slice A) and its cutover (slice B): both mirrored
the prefix rule BY CONSTRUCTION, so with the rule gone they could only ever agree
with themselves — they measured nothing.

What still routes a turn to a sibling: a real Discord mention or a vocative alias
("frugi, ..."), both owned by the gateway's `should_respond` (covered by
`tests/integration/test_sibling_addressing.py`), and the LLM router summoning the
persona through /invite (covered by `tests/chat/test_llm_router_cutover.py`).

What survives here is the ONE shadow that could ever disagree: the gpt-4.1 router
picking a target independently, off the critical path, never acted on.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from structlog.testing import capture_logs

from demux_ai.llm_shadow_router import LLMShadowDecision
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
    # A MagicMock attr is truthy, which would spawn an un-awaited LLM-shadow coro.
    ctx.deps.llm_shadow_route = None
    return ctx


# --- the retirement itself: prefix text must NOT route -----------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["@vultur reseña Hereditary", "~vultur reseña Hereditary"])
async def test_prefix_text_no_longer_routes_to_vultur(text: str) -> None:
    """The retired rule: `@vultur ` as plain text is now just text."""
    ctx = _make_ctx(text)
    await _stage_bind_identity(ctx)
    assert ctx.persona_id is None, "prefix addressing was retired 2026-07-08"


@pytest.mark.asyncio
async def test_prefix_text_is_no_longer_stripped_from_the_message() -> None:
    """Resistance case: the text must reach the persona INTACT, not silently
    mutilated by a rule that no longer routes."""
    ctx = _make_ctx("@vultur reseña Hereditary")
    await _stage_bind_identity(ctx)
    assert ctx.text == "@vultur reseña Hereditary"


@pytest.mark.asyncio
async def test_normal_message_keeps_insult_default() -> None:
    ctx = _make_ctx("hola qué onda")
    await _stage_bind_identity(ctx)
    assert ctx.persona_id is None
    assert ctx.text == "hola qué onda"


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
    ctx = _make_ctx_llm("dame cine", route=_boom, spawn=spawn)
    with capture_logs() as logs:
        await _stage_bind_identity(ctx)
        # the turn is unaffected — the shadow never touches routing, and with the
        # prefix rule retired an un-addressed turn stays with Insult.
        assert ctx.persona_id is None
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
