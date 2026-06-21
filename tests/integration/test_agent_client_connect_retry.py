"""Connect-level retry for AgentRunnerClient (no network).

Root cause, 2026-06-21: Alex sent an image; the runner was alive + idle but a
single transient ``ConnectTimeout`` (10s, the TCP connect never completed) was
turned STRAIGHT into ``RunnerDownError`` with zero retries, so a one-off blip
summoned ALICE — who never receives the image and answers blind. A ConnectTimeout
/ ConnectError happens BEFORE the request body is sent, so the turn provably never
reached the runner: re-POSTing is safe (no duplicate turn) and is the correct
resilience move.

Resistance case (the one that makes this safe): a ``ReadTimeout`` means the
request MAY have landed and be processing — re-POSTing it would double-spend the
turn. ReadTimeout must NOT be retried; it stays a single-shot ``RunnerDownError``.
"""

from __future__ import annotations

from typing import ClassVar

import httpx
import pytest

from khimeras_shared.runner.agent_client import AgentRunnerClient, RunnerDownError


def _messages() -> list[dict]:
    return [{"role": "user", "content": "mira esta imagen"}]


class _Resp:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code
        self.text = "ok"

    def json(self) -> dict:
        return {"text": "ok", "stop_reason": "end_turn", "model": "agent-runner"}


class _ScriptedClient:
    """Raises a scripted sequence of transport errors, then returns a resp.

    ``script`` is a list where each element is either an exception instance (raise
    it on that POST attempt) or an ``_Resp`` (return it). ``calls`` counts POSTs.
    """

    script: ClassVar[list] = []
    calls: ClassVar[int] = 0

    def __init__(self, *a, **k) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        idx = _ScriptedClient.calls
        _ScriptedClient.calls += 1
        item = _ScriptedClient.script[min(idx, len(_ScriptedClient.script) - 1)]
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("khimeras_shared.runner.agent_client.httpx.AsyncClient", _ScriptedClient)

    # No real backoff sleeps in tests.
    async def _no_sleep(_s):
        return None

    monkeypatch.setattr("khimeras_shared.runner.agent_client.asyncio.sleep", _no_sleep)
    _ScriptedClient.script = []
    _ScriptedClient.calls = 0
    return AgentRunnerClient("http://runner", "tok")


@pytest.mark.asyncio
async def test_connect_timeout_retries_then_succeeds(client):
    """Two transient ConnectTimeouts then a good response → NO failover, the turn
    is served by the runner. This is the Alex-image incident, fixed."""
    _ScriptedClient.script = [
        httpx.ConnectTimeout("syn dropped"),
        httpx.ConnectTimeout("syn dropped"),
        _Resp(200),
    ]
    out = await client.chat("sys", _messages())
    assert out.text == "ok"
    assert _ScriptedClient.calls == 3  # retried twice, succeeded on the third


@pytest.mark.asyncio
async def test_connect_error_retries_then_succeeds(client):
    """ConnectError (refused) is also pre-send → retryable."""
    _ScriptedClient.script = [httpx.ConnectError("refused"), _Resp(200)]
    out = await client.chat("sys", _messages())
    assert out.text == "ok"
    assert _ScriptedClient.calls == 2


@pytest.mark.asyncio
async def test_connect_timeout_exhausts_then_runner_down(client):
    """A genuinely unreachable runner still fails over after the retries are spent."""
    _ScriptedClient.script = [httpx.ConnectTimeout("down")]  # always raises
    with pytest.raises(RunnerDownError):
        await client.chat("sys", _messages())
    assert _ScriptedClient.calls == 3  # 1 + 2 retries


@pytest.mark.asyncio
async def test_read_timeout_is_not_retried(client):
    """RESISTANCE: a ReadTimeout means the request may have landed; re-POSTing
    would double-spend the turn. It must stay single-shot RunnerDownError."""
    _ScriptedClient.script = [httpx.ReadTimeout("processing")]
    with pytest.raises(RunnerDownError):
        await client.chat("sys", _messages())
    assert _ScriptedClient.calls == 1  # NOT retried
