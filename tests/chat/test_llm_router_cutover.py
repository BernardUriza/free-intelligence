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
from structlog.testing import capture_logs

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


# --- telemetry: the watch metric must not lie -------------------------------
#
# It shipped as `diverged`, computed `target != "insult"` — with nothing to
# diverge FROM. Every healthy sibling summon read as a disagreement, so the
# "divergence rate" Bernard was told to watch counted the router WORKING.


@pytest.mark.asyncio
async def test_sibling_route_is_logged_as_routed_to_sibling_not_diverged(monkeypatch):
    ctx = _make_ctx()
    ctx.deps.llm_router_cutover_route = AsyncMock(return_value=_decision("vultur"))
    monkeypatch.setattr(stages, "fire_invite", AsyncMock(return_value=True))
    with capture_logs() as logs, pytest.raises(StageStop):
        await _stage_llm_router_cutover(ctx)
    ev = next(e for e in logs if e["event"] == "llm_router_cutover_decision")
    assert ev["routed_to_sibling"] is True
    assert ev["target"] == "vultur"
    assert "diverged" not in ev, "the old lying field name must be gone, not aliased"


@pytest.mark.asyncio
async def test_insult_route_is_logged_as_not_routed_to_sibling(monkeypatch):
    ctx = _make_ctx("hola qué onda")
    ctx.deps.llm_router_cutover_route = AsyncMock(return_value=_decision("insult"))
    monkeypatch.setattr(stages, "fire_invite", AsyncMock(return_value=True))
    with capture_logs() as logs:
        await _stage_llm_router_cutover(ctx)
    ev = next(e for e in logs if e["event"] == "llm_router_cutover_decision")
    assert ev["routed_to_sibling"] is False
    assert ev["target"] == "insult"


def test_timeout_ceiling_clears_the_observed_success_tail():
    """The 3.0s ceiling clipped a p95 of 1401ms / max 2865ms and lost 11.9% of
    calls to pure timeouts. Whatever this value is, it must sit above the tail
    the healthy path actually reaches.

    Read from source, not imported: `personas.insult.config` builds its Settings
    singleton at import time and needs a `.env` that CI does not have.
    """
    import re
    from pathlib import Path

    config_src = (Path(__file__).resolve().parents[2] / "personas" / "insult" / "config.py").read_text()
    match = re.search(r"llm_router_cutover_timeout_seconds:\s*float\s*=\s*([\d.]+)", config_src)
    assert match, "llm_router_cutover_timeout_seconds default not found in config.py"

    ceiling_ms = float(match.group(1)) * 1000
    observed_success_max_ms = 2865
    assert ceiling_ms > observed_success_max_ms * 1.5, (
        f"ceiling {ceiling_ms}ms leaves no headroom over the observed {observed_success_max_ms}ms success tail"
    )


def test_stage_has_no_second_ceiling_of_its_own():
    """The ceiling lives in config.py, once. A `getattr(settings, ..., 3.0)` in
    the stage is a second, silently stale copy: the day the setting is renamed,
    the stage stops raising and quietly reinstalls the 3.0s ceiling that lost
    11.9% of the calls.
    """
    import re
    from pathlib import Path

    stages_src = (
        Path(__file__).resolve().parents[2] / "personas" / "insult" / "cogs" / "chat" / "stages.py"
    ).read_text()
    assert not re.search(r"getattr\([^)]*llm_router_cutover_timeout_seconds[^)]*,\s*[\d.]+\s*\)", stages_src), (
        "the stage carries its own timeout default — config.py is the only source of truth"
    )


@pytest.mark.asyncio
async def test_preset_persona_id_outranks_router_seam_contract_only():
    """SEAM CONTRACT, NOT production coverage — read this before trusting it green.

    Nothing sets `ctx.persona_id` anymore: the `~vultur `/`@vultur ` prefix was its
    only writer and died with the strangler-fig (88481c9). So in production this
    stage always sees None and the guard below is unreachable. What actually keeps
    the router off an addressed turn is `batch.handle_incoming`, which returns
    before the turn is ever queued — pinned in
    `tests/integration/test_sibling_addressing.py`.

    Kept because the guard is the seam's contract: if a future host writes
    `persona_id` again (a demux front-door picking the persona), explicit addressing
    must still outrank the LLM. It just doesn't guard anything today.
    """
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


def test_emit_typing_runs_after_the_router_so_insult_never_types_on_a_routed_turn():
    """Regression guard (2026-07-11): ``emit_typing`` must come AFTER the router
    (and the triviality gate). It used to sit at position 2 — BEFORE routing — so
    on an implicit turn the DeMux would resolve to a sibling (ALICE) while Insult
    had ALREADY fired a typing indicator during the router's ~1-4s deliberation.
    The user saw Insult "typing", then ALICE appear, then Insult's indicator time
    out: the exact smell Bernard caught. A sibling-routed or trivial turn StageStops
    above, so emit_typing must sit below both gates to never fire for a turn Insult
    won't answer."""
    names = [s.name for s in stages.DEFAULT_STAGES]
    assert names.index("emit_typing") > names.index("llm_router_cutover")
    assert names.index("emit_typing") > names.index("ensure_not_trivial")


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
