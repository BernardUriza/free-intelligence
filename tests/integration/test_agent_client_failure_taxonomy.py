"""PR-4b slice 2 — AgentRunnerClient failure taxonomy (no network).

The runner failure used to collapse into a single ``AgentRunnerError``, so
``stages.py`` could not tell "the runner PROCESS is down" (failover to a real
sibling persona is legitimate) from "the runner answered but rejected THIS
turn" (failing over fabricates a 'fake ALICE'). This pins the mapping:

- read timeout / transport error / 5xx  → ``RunnerDownError``
- 4xx / invalid JSON                     → ``PersonaTurnError``

Both remain ``AgentRunnerError`` subclasses so existing catch sites keep
working (positive + resistance per the destructive-post-processing rule).
"""

from __future__ import annotations

from typing import ClassVar

import httpx
import pytest

from khimeras_shared.runner.agent_client import (
    AgentRunnerClient,
    AgentRunnerError,
    PersonaTurnError,
    RunnerDownError,
)


def _messages() -> list[dict]:
    return [{"role": "user", "content": "oye"}]


class _Resp:
    def __init__(self, status_code: int, body: str = "", *, bad_json: bool = False) -> None:
        self.status_code = status_code
        self.text = body
        self._bad_json = bad_json

    def json(self) -> dict:
        if self._bad_json:
            raise ValueError("not json")
        return {"text": "ok", "stop_reason": "end_turn", "model": "agent-runner"}


class _Client:
    """Posts a canned response, or raises a canned transport error."""

    resp: ClassVar[_Resp | None] = None
    raise_exc: ClassVar[BaseException | None] = None

    def __init__(self, *a, **k) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        if _Client.raise_exc is not None:
            raise _Client.raise_exc
        return _Client.resp


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("khimeras_shared.runner.agent_client.httpx.AsyncClient", _Client)
    _Client.resp = None
    _Client.raise_exc = None
    return AgentRunnerClient("http://runner", "tok")


@pytest.mark.asyncio
async def test_read_timeout_is_runner_down(client):
    _Client.raise_exc = httpx.ReadTimeout("slow")
    with pytest.raises(RunnerDownError):
        await client.chat("sys", _messages())


@pytest.mark.asyncio
async def test_transport_error_is_runner_down(client):
    _Client.raise_exc = httpx.ConnectError("refused")
    with pytest.raises(RunnerDownError):
        await client.chat("sys", _messages())


@pytest.mark.asyncio
async def test_5xx_is_runner_down(client):
    _Client.resp = _Resp(503, "upstream down")
    with pytest.raises(RunnerDownError):
        await client.chat("sys", _messages())


@pytest.mark.asyncio
async def test_4xx_is_persona_turn_error(client):
    """The runner is UP and refused this turn — NOT a downed runner. Failing
    over to ALICE here would fabricate a fake-ALICE for a request she can't fix."""
    _Client.resp = _Resp(422, "bad turn")
    with pytest.raises(PersonaTurnError):
        await client.chat("sys", _messages())


@pytest.mark.asyncio
async def test_invalid_json_is_persona_turn_error(client):
    """Reachable but emitting garbage = a bug to SEE, not mask with failover."""
    _Client.resp = _Resp(200, "<html>", bad_json=True)
    with pytest.raises(PersonaTurnError):
        await client.chat("sys", _messages())


@pytest.mark.asyncio
async def test_subclasses_are_agent_runner_errors(client):
    """Existing ``except AgentRunnerError`` catch sites must keep catching both."""
    _Client.resp = _Resp(503)
    with pytest.raises(AgentRunnerError):
        await client.chat("sys", _messages())
    _Client.resp = _Resp(404)
    with pytest.raises(AgentRunnerError):
        await client.chat("sys", _messages())
