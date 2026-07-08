"""HOST 5/6 slice C — LLM router cutover stage (acts on the gpt-4.1 decision).

The founding P0 (2026-07-07): mid-exchange with Vultur about non-binary
identity, Bernard's un-mentioned continuation routed to Insult because the live
rule only routes on explicit addressing. This stage lets the context-aware LLM
decision ACTUALLY route implicit turns: a sibling target suppresses Insult's
reply (StageStop) and summons the persona through the gateway /invite.

Mutator rules: positive (sibling decision → invite + StageStop) + resistance on
EVERY fail-safe edge — explicit addressing, empty text, budget cap, timeout,
router fault, unroutable target, rejected invite. A routing fault must never
produce a mute turn: every edge ends with Insult answering as today.
"""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import personas.insult.cogs.chat.stages as stages
from demux_ai.llm_shadow_router import LLMShadowDecision
from personas.insult.cogs.chat.pipeline import StageStop, TurnCtx
from personas.insult.cogs.chat.stages import _stage_llm_router_cutover
from personas.insult.composition import build_llm_router_cutover_route, build_router_budget


def _make_ctx(text: str = "eres un buitre no-cis entonces", persona_id: str | None = None) -> TurnCtx:
    msg = MagicMock()
    msg.channel.id = 111
    msg.author.id = 222
    msg.author.display_name = "tester"
    msg.guild = None
    msg.channel.name = "general"
    msg.attachments = []
    msg.flags.voice = False
    ctx = TurnCtx(message=msg, text=text, turn_start=time.monotonic(), deps=MagicMock())
    ctx.persona_id = persona_id
    ctx.channel_id = "111"
    ctx.user_id = "222"
    ctx.user_name = "tester"
    ctx.guild_id = None
    ctx.channel_name = "general"
    ctx.deps.memory = None
    ctx.deps.router_budget = None
    ctx.deps.settings = SimpleNamespace(llm_router_cutover_timeout_seconds=0.5)
    ctx.deps.llm_router_cutover_route = None
    return ctx


def _decision(target: str) -> LLMShadowDecision:
    return LLMShadowDecision(target=target, reason=f"llm_{target}", input_tokens=900, output_tokens=3)


@pytest.mark.asyncio
async def test_sibling_decision_summons_and_stops(monkeypatch):
    ctx = _make_ctx()
    ctx.deps.llm_router_cutover_route = AsyncMock(return_value=_decision("vultur"))
    fire = AsyncMock(return_value=True)
    monkeypatch.setattr(stages, "fire_invite", fire)
    with pytest.raises(StageStop) as excinfo:
        await _stage_llm_router_cutover(ctx)
    assert "routed_to_vultur" in str(excinfo.value)
    kwargs = fire.call_args.kwargs
    assert kwargs["persona_id"] == "vultur"
    assert kwargs["invited_by"] == "host_router"
    assert "tester" in fire.call_args.args[0]
    assert "buitre no-cis" in fire.call_args.args[0]


@pytest.mark.asyncio
async def test_insult_decision_continues_without_invite(monkeypatch):
    ctx = _make_ctx("hola qué onda")
    ctx.deps.llm_router_cutover_route = AsyncMock(return_value=_decision("insult"))
    fire = AsyncMock(return_value=True)
    monkeypatch.setattr(stages, "fire_invite", fire)
    await _stage_llm_router_cutover(ctx)
    fire.assert_not_called()


@pytest.mark.asyncio
async def test_explicit_addressing_outranks_router():
    ctx = _make_ctx("@vultur reseña Hereditary", persona_id="vultur")
    route = AsyncMock(return_value=_decision("insult"))
    ctx.deps.llm_router_cutover_route = route
    await _stage_llm_router_cutover(ctx)
    route.assert_not_called()


@pytest.mark.asyncio
async def test_unwired_route_is_noop():
    ctx = _make_ctx()
    await _stage_llm_router_cutover(ctx)


@pytest.mark.asyncio
async def test_empty_text_skips_router():
    ctx = _make_ctx("   ")
    route = AsyncMock(return_value=_decision("vultur"))
    ctx.deps.llm_router_cutover_route = route
    await _stage_llm_router_cutover(ctx)
    route.assert_not_called()


@pytest.mark.asyncio
async def test_timeout_falls_back_to_insult(monkeypatch):
    ctx = _make_ctx()

    async def _slow_route(text, context=None):
        await asyncio.sleep(5)
        return _decision("vultur")

    ctx.deps.llm_router_cutover_route = _slow_route
    ctx.deps.settings = SimpleNamespace(llm_router_cutover_timeout_seconds=0.01)
    fire = AsyncMock(return_value=True)
    monkeypatch.setattr(stages, "fire_invite", fire)
    await _stage_llm_router_cutover(ctx)
    fire.assert_not_called()


@pytest.mark.asyncio
async def test_router_fault_falls_back_to_insult(monkeypatch):
    ctx = _make_ctx()
    ctx.deps.llm_router_cutover_route = AsyncMock(side_effect=RuntimeError("azure down"))
    fire = AsyncMock(return_value=True)
    monkeypatch.setattr(stages, "fire_invite", fire)
    await _stage_llm_router_cutover(ctx)
    fire.assert_not_called()


@pytest.mark.asyncio
async def test_rejected_invite_falls_back_to_insult(monkeypatch):
    ctx = _make_ctx()
    ctx.deps.llm_router_cutover_route = AsyncMock(return_value=_decision("vultur"))
    monkeypatch.setattr(stages, "fire_invite", AsyncMock(return_value=False))
    await _stage_llm_router_cutover(ctx)


@pytest.mark.asyncio
async def test_unroutable_target_falls_back_to_insult(monkeypatch):
    ctx = _make_ctx()
    ctx.deps.llm_router_cutover_route = AsyncMock(return_value=_decision("gandalf"))
    fire = AsyncMock(return_value=True)
    monkeypatch.setattr(stages, "fire_invite", fire)
    await _stage_llm_router_cutover(ctx)
    fire.assert_not_called()


@pytest.mark.asyncio
async def test_budget_cap_skips_the_azure_call():
    ctx = _make_ctx()
    route = AsyncMock(return_value=_decision("vultur"))
    ctx.deps.llm_router_cutover_route = route
    ctx.deps.router_budget = SimpleNamespace(
        can_spend=lambda: False,
        spent_this_week=lambda: 5.01,
        cap_usd=5.0,
    )
    await _stage_llm_router_cutover(ctx)
    route.assert_not_called()


@pytest.mark.asyncio
async def test_budget_records_real_token_cost(monkeypatch):
    ctx = _make_ctx()
    ctx.deps.llm_router_cutover_route = AsyncMock(return_value=_decision("insult"))
    recorded: list[tuple[int, int]] = []
    ctx.deps.router_budget = SimpleNamespace(
        can_spend=lambda: True,
        record=lambda i, o: recorded.append((i, o)) or 0.01,
        spent_this_week=lambda: 0.01,
        cap_usd=5.0,
    )
    await _stage_llm_router_cutover(ctx)
    assert recorded == [(900, 3)]


def test_stage_is_registered_after_memory_store():
    names = [s.name for s in stages.DEFAULT_STAGES]
    assert names.index("llm_router_cutover") == names.index("memory_store") + 1
    assert names.index("llm_router_cutover") < names.index("ensure_not_trivial")


def test_builder_off_by_default_returns_none():
    assert build_llm_router_cutover_route(SimpleNamespace(llm_router_cutover_enabled=False)) is None


def test_builder_on_returns_direct_route_callable():
    route = build_llm_router_cutover_route(SimpleNamespace(llm_router_cutover_enabled=True))
    assert route is not None
    assert asyncio.iscoroutinefunction(route)


def test_router_budget_builds_under_cutover_flag_alone():
    budget = build_router_budget(SimpleNamespace(llm_shadow_router_enabled=False, llm_router_cutover_enabled=True))
    assert budget is not None
    assert budget.can_spend()


def test_router_budget_stays_none_when_both_routers_off():
    assert (
        build_router_budget(SimpleNamespace(llm_shadow_router_enabled=False, llm_router_cutover_enabled=False)) is None
    )
