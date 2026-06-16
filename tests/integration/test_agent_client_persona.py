"""The runner client forwards `persona_id` so a sibling persona answers.

Khimeras: a turn for @Vultur must tell the runner to load vultur.md. Insult
(persona_id=None) must NOT add the field, keeping its payload/behavior identical.

Mutator rule: positive (id reaches payload) + resistance (None leaves it out).
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from khimeras_shared.runner.agent_client import AgentRunnerClient


class _FakeResp:
    status_code = 200
    text = ""

    def json(self) -> dict:
        return {"text": "ok", "stop_reason": "end_turn", "model": "agent-runner"}


class _FakeClient:
    captured: ClassVar[dict] = {}

    def __init__(self, *a, **k) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        _FakeClient.captured = json
        return _FakeResp()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("khimeras_shared.runner.agent_client.httpx.AsyncClient", _FakeClient)
    _FakeClient.captured = {}
    return AgentRunnerClient("http://runner", "tok")


def _msgs(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]


@pytest.mark.asyncio
async def test_persona_id_reaches_payload(client):
    await client.chat("sys", _msgs("reséñame Creep"), persona_id="vultur")
    assert _FakeClient.captured["persona_id"] == "vultur"


@pytest.mark.asyncio
async def test_no_persona_id_omitted_for_insult(client):
    await client.chat("sys", _msgs("hola"))
    assert "persona_id" not in _FakeClient.captured
