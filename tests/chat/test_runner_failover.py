"""PR-4b slice 2 — runner-down detection + honest failover/degradation.

The pre-slice failover invited ALICE on ANY agent-runner failure. That
fabricated a 'fake ALICE' whenever the runner was actually ALIVE but rejected
THIS turn (4xx / invalid JSON → ``PersonaTurnError``): ALICE can't fix a bad
request, so the user saw voice B for no reason. This pins the new policy:

- ALICE failover is attempted ONLY when the runner PROCESS is down
  (``RunnerDownError`` → ``runner_down``).
- A ``PersonaTurnError`` (``persona_error``) NEVER fails over — honest
  degradation instead (the resistance case that guards the regression).
- Failover requires REAL ALICE availability: ``summon_persona`` returns
  True only on a 202 from her container. A non-202 → honest degradation, never
  a silent drop.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

import personas.insult.cogs.chat.stages as stages
from khimeras_shared.runner.agent_client import PersonaTurnError, RunnerDownError
from personas.insult.cogs.chat._failure import (
    FailoverReason,
    StageFailure,
    StageStop,
    classify_failover_reason,
    decide_failover,
)
from personas.insult.cogs.chat.pipeline import TurnCtx, TurnRuntimeDeps

# --------------------------------------------------------------------------
# Pure policy — classify_failover_reason + decide_failover
# --------------------------------------------------------------------------


class TestClassifyFailoverReason:
    def test_runner_down_error(self):
        assert classify_failover_reason(RunnerDownError("x")) is FailoverReason.RUNNER_DOWN

    def test_persona_turn_error(self):
        assert classify_failover_reason(PersonaTurnError("x")) is FailoverReason.PERSONA_ERROR

    def test_host_router_error_by_name(self):
        from demux_ai.host_llm import HostRouterError

        assert classify_failover_reason(HostRouterError("x")) is FailoverReason.ROUTER_ERROR

    def test_unknown_falls_through(self):
        assert classify_failover_reason(ValueError("x")) is FailoverReason.UNKNOWN


class TestDecideFailover:
    def test_runner_down_attempts_alice(self):
        d = decide_failover(RunnerDownError("x"), backend="agent_runner", alice_failover_enabled=True)
        assert d.reason is FailoverReason.RUNNER_DOWN
        assert d.attempt_alice is True

    def test_persona_error_never_attempts_alice(self):
        """The 'fake ALICE' regression guard: a live runner rejecting a turn
        must NOT trigger failover."""
        d = decide_failover(PersonaTurnError("x"), backend="agent_runner", alice_failover_enabled=True)
        assert d.reason is FailoverReason.PERSONA_ERROR
        assert d.attempt_alice is False

    def test_disabled_flag_blocks_failover_even_when_runner_down(self):
        d = decide_failover(RunnerDownError("x"), backend="agent_runner", alice_failover_enabled=False)
        assert d.attempt_alice is False

    def test_non_agent_backend_never_attempts_alice(self):
        d = decide_failover(RunnerDownError("x"), backend="legacy", alice_failover_enabled=True)
        assert d.attempt_alice is False


# --------------------------------------------------------------------------
# Integration — _stage_call_llm failover wiring
# --------------------------------------------------------------------------


def _mk_llm_ctx(*, chat_exc: Exception, alice_failover_enabled: bool = True) -> TurnCtx:
    settings = MagicMock()
    settings.alice_failover_enabled = alice_failover_enabled
    settings.llm_model = "claude"

    channel = MagicMock()
    channel.id = 42
    channel.send = AsyncMock(return_value=None)
    message = MagicMock()
    message.channel = channel
    message.add_reaction = AsyncMock(return_value=None)

    agent_client = MagicMock()
    agent_client.chat = AsyncMock(side_effect=chat_exc)

    ctx = TurnCtx(
        message=message,
        text="oye",
        turn_start=time.monotonic(),
        deps=TurnRuntimeDeps(
            memory=MagicMock(),
            settings=settings,
            bot=MagicMock(),
            expression_history=MagicMock(),
            spawn_task=lambda *a, **kw: None,
            facts=MagicMock(),
            stance=MagicMock(),
            arc=MagicMock(),
            retrieval=MagicMock(),
            preset_engine=MagicMock(),
            policy=MagicMock(),
            mutation=MagicMock(),
            agent_client=agent_client,
        ),
    )
    ctx.channel_id = "42"
    ctx.user_id = "7"
    ctx.guild_id = "99"
    ctx.channel_name = "general"
    ctx.system_prompt = "sys"
    ctx.context = []
    ctx.model_choice = None
    ctx.persona_id = None
    return ctx


@pytest.fixture(autouse=True)
def _stub_pre_chat(monkeypatch):
    """The pre-chat assembly (behavioral guidance + knowledge) is exercised by
    its own tests; here we stub it so the failover branch is the unit under
    test, not the prompt builder."""
    monkeypatch.setattr(stages, "_build_behavioral_guidance", lambda ctx: "")

    async def _empty_knowledge(*a, **k):
        return MagicMock(combined_memory=None, other_people_block=None)

    monkeypatch.setattr(stages, "assemble_knowledge", _empty_knowledge)


@pytest.mark.asyncio
async def test_runner_down_with_alice_available_failover(monkeypatch):
    """RunnerDownError + ALICE accepts (202) → StageStop, delivery_mode set,
    no in-character error sent (ALICE delivers async)."""
    invoke = AsyncMock(return_value=True)
    monkeypatch.setattr("demux_ai.summon.summon_persona", invoke)

    ctx = _mk_llm_ctx(chat_exc=RunnerDownError("runner 503"))

    with pytest.raises(StageStop) as ei:
        await stages._stage_call_llm(ctx)
    assert ei.value.outcome == "alice_failover"
    assert ctx.delivery_mode == "alice_failover"
    invoke.assert_awaited_once()
    ctx.message.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_runner_down_with_alice_unavailable_degrades(monkeypatch):
    """RunnerDownError but ALICE's /invite is NOT accepted → honest
    degradation (StageFailure + user notice), NOT a silent drop."""
    invoke = AsyncMock(return_value=False)
    monkeypatch.setattr("demux_ai.summon.summon_persona", invoke)

    ctx = _mk_llm_ctx(chat_exc=RunnerDownError("runner 503"))

    with pytest.raises(StageFailure):
        await stages._stage_call_llm(ctx)
    invoke.assert_awaited_once()
    ctx.message.channel.send.assert_awaited()  # honest in-character notice


@pytest.mark.asyncio
async def test_persona_error_never_invites_alice(monkeypatch):
    """THE regression guard: a live runner rejecting the turn (4xx →
    PersonaTurnError) must NOT invoke ALICE — degrade honestly."""
    invoke = AsyncMock(return_value=True)
    monkeypatch.setattr("demux_ai.summon.summon_persona", invoke)

    ctx = _mk_llm_ctx(chat_exc=PersonaTurnError("runner 422"))

    with pytest.raises(StageFailure):
        await stages._stage_call_llm(ctx)
    invoke.assert_not_awaited()
    ctx.message.channel.send.assert_awaited()


@pytest.mark.asyncio
async def test_failover_disabled_never_invites_alice(monkeypatch):
    invoke = AsyncMock(return_value=True)
    monkeypatch.setattr("demux_ai.summon.summon_persona", invoke)

    ctx = _mk_llm_ctx(chat_exc=RunnerDownError("runner 503"), alice_failover_enabled=False)

    with pytest.raises(StageFailure):
        await stages._stage_call_llm(ctx)
    invoke.assert_not_awaited()
    ctx.message.channel.send.assert_awaited()
