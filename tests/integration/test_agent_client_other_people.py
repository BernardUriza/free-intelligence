"""The runner client must forward the 'Other People' block into user_text.

The runner DISCARDS `system_prompt` and rebuilds only the AUTHOR's facts from
its filesystem (via the user_id it receives). Facts about OTHER channel
participants live only in the plumbing-built system_prompt — so without
forwarding them, the bot knew Alex when SHE spoke (her user_id) but answered
"no me lo has contado" when Bernard asked ABOUT Alex (2026-06-03 second-layer
bug). The fix injects the pre-built block into the user_text the runner DOES
read, mirroring `relevant_memory`.

Mutator rule: positive (block reaches user_text) + resistance (absent block
leaves user_text clean) + coexistence with relevant_memory.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from khimeras_shared.runner.agent_client import AgentRunnerClient


class _FakeResp:
    status_code = 200
    text = ""

    def json(self) -> dict:
        return {"text": "respuesta", "stop_reason": "end_turn", "model": "agent-runner"}


class _FakeClient:
    """Captures the POST payload instead of hitting the network."""

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


def _msgs(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("khimeras_shared.runner.agent_client.httpx.AsyncClient", _FakeClient)
    _FakeClient.captured = {}
    return AgentRunnerClient("http://runner", "tok")


@pytest.mark.asyncio
async def test_other_people_block_reaches_user_text(client):
    """POSITIVE: the block is injected so the runner can answer about a third party."""
    await client.chat(
        "discarded system prompt",
        _msgs("¿Por qué Alex va a Guadalajara?"),
        other_people="## Other People in This Channel\n- Alex: Irá a Guadalajara para consulta reumatológica",
    )
    ut = _FakeClient.captured["user_text"]
    assert "<other_people_in_channel>" in ut
    assert "Alex: Irá a Guadalajara" in ut
    # The user's actual question must still be present and after the context block.
    assert "¿Por qué Alex va a Guadalajara?" in ut
    assert ut.index("Guadalajara para consulta") < ut.index("¿Por qué Alex")


@pytest.mark.asyncio
async def test_no_other_people_leaves_user_text_clean(client):
    """RESISTANCE: without the block, user_text is just the message — no stray tags."""
    await client.chat("sys", _msgs("hola bot"))
    ut = _FakeClient.captured["user_text"]
    assert ut == "hola bot"
    assert "other_people_in_channel" not in ut


@pytest.mark.asyncio
async def test_other_people_and_relevant_memory_coexist(client):
    """Both context blocks ride along, in order, with the message last."""
    await client.chat(
        "sys",
        _msgs("cuéntame"),
        relevant_memory="chunk del pasado",
        other_people="- Alex: dato",
    )
    ut = _FakeClient.captured["user_text"]
    assert "<relevant_memory>" in ut
    assert "<other_people_in_channel>" in ut
    assert ut.index("relevant_memory") < ut.index("other_people_in_channel") < ut.index("cuéntame")
