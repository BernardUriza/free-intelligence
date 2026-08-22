"""`TURN_BACKEND` routes the turn, the judge and the boot check — both ways.

The flag is SCAFFOLDING: the default stays `local` until the AIRE route is
live-verified, and the local path dies when it flips permanent (backlog
aire-engine-stage2.md). Until then both directions are asserted, so neither can
break silently — and the default is pinned, so nobody ships a surprise cutover.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from persona_runner.api import judge as judge_api
from persona_runner.api import turn as turn_api
from persona_runner.core import config
from persona_runner.core.schemas import JudgeRequest, JudgeResponse, TurnRequest, TurnResponse


def test_the_default_backend_is_local():
    """The flag ships OFF: a deploy that sets nothing keeps today's turn."""
    assert config.TURN_BACKEND == "local"


@pytest.mark.asyncio
async def test_the_turn_endpoint_delegates_to_aire_when_the_flag_is_on(monkeypatch):
    """With the flag on, /v1/turn never touches the local SDK host."""
    monkeypatch.setattr(config, "TURN_BACKEND", "aire")
    monkeypatch.setattr(turn_api, "check_auth", lambda _a: None)
    called = AsyncMock(return_value=TurnResponse(text="desde aire"))
    monkeypatch.setattr("persona_runner.engine.aire_route.turn_via_aire", called)

    resp = await turn_api.turn(TurnRequest(channel_id="1", user_id="2", user_text="hey"), authorization=None)

    assert resp.text == "desde aire"
    called.assert_awaited_once()


@pytest.mark.asyncio
async def test_the_turn_endpoint_ignores_aire_when_the_flag_is_off(monkeypatch):
    """Resistance: the local path must not consult AIRE at all."""
    monkeypatch.setattr(config, "TURN_BACKEND", "local")
    monkeypatch.setattr(turn_api, "check_auth", lambda _a: None)
    called = AsyncMock(side_effect=AssertionError("the local path called AIRE"))
    monkeypatch.setattr("persona_runner.engine.aire_route.turn_via_aire", called)
    monkeypatch.setattr(
        "persona_runner.engine.session_pool.get_or_create_client",
        AsyncMock(side_effect=RuntimeError("local path reached")),
    )

    with pytest.raises(Exception, match="local path reached"):
        await turn_api.turn(TurnRequest(channel_id="1", user_id="2", user_text="hey"), authorization=None)
    called.assert_not_awaited()


@pytest.mark.asyncio
async def test_the_judge_endpoint_delegates_to_aire_when_the_flag_is_on(monkeypatch):
    """The judge rides the same flag — no half-migrated state with two SDK hosts."""
    monkeypatch.setattr(config, "TURN_BACKEND", "aire")
    monkeypatch.setattr(judge_api, "check_auth", lambda _a: None)
    judge_api.reset_judge_semaphore()
    called = AsyncMock(return_value=JudgeResponse(text="veredicto"))
    monkeypatch.setattr("persona_runner.engine.aire_route.judge_via_aire", called)

    resp = await judge_api.judge(JudgeRequest(system_prompt="p", user_text="u"), authorization=None)

    assert resp.text == "veredicto"
    called.assert_awaited_once()


@pytest.mark.asyncio
async def test_the_judge_keeps_its_concurrency_gate_on_the_aire_route(monkeypatch):
    """The pile-up only MOVED (to AIRE's 2 RAM slots): the queue must stay here."""
    monkeypatch.setattr(config, "TURN_BACKEND", "aire")
    monkeypatch.setattr(judge_api, "check_auth", lambda _a: None)
    judge_api.reset_judge_semaphore()
    held: list[int] = []

    async def _observe(_req):
        held.append(judge_api.get_judge_semaphore()._value)
        return JudgeResponse(text="ok")

    monkeypatch.setattr("persona_runner.engine.aire_route.judge_via_aire", _observe)

    await judge_api.judge(JudgeRequest(system_prompt="p", user_text="u"), authorization=None)

    assert held == [config.JUDGE_MAX_CONCURRENCY - 1], "the judge ran without holding the gate"
