"""The runner client must forward wall-clock time into user_text for EVERY persona.

Time is SSOT'd in `shared.time_context` but only ever reached the plumbing-built
`system_prompt` — which the runner DISCARDS under LEGACY=false. So neither Insult
nor the siblings knew the date/time; Frugívoro built a weekly menu saying "domingo
prep" on a Wednesday (2026-07-08). Same loss class as `other_people`; same fix:
inject a dynamic `<current_time>` prefix_block on the user_text the runner reads.

One seam (`agent_client.chat`) → all personas inherit it. The block must be
non-cacheable (changes every minute) so it rides FIRST, in the dynamic tail.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from persona_core.runner.agent_client import AgentRunnerClient


class _FakeResp:
    status_code = 200
    text = ""

    def json(self) -> dict:
        return {"text": "respuesta", "stop_reason": "end_turn", "model": "agent-runner"}


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


def _msgs(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("persona_core.runner.agent_client.httpx.AsyncClient", _FakeClient)
    _FakeClient.captured = {}
    return AgentRunnerClient("http://runner", "tok")


@pytest.mark.asyncio
async def test_current_time_block_reaches_user_text(client):
    """POSITIVE: every turn carries the wall-clock block with the IANA timezone."""
    await client.chat("discarded system prompt", _msgs("¿qué día es hoy?"))
    ut = _FakeClient.captured["user_text"]
    assert "<current_time>" in ut
    assert "America/Mexico_City" in ut
    assert "¿qué día es hoy?" in ut


@pytest.mark.asyncio
async def test_current_time_present_for_sibling_persona(client):
    """The fix must cover siblings (persona_id set), not only Insult."""
    await client.chat("sys", _msgs("recomiéndame comida"), persona_id="frugivoro")
    ut = _FakeClient.captured["user_text"]
    assert "<current_time>" in ut
    assert _FakeClient.captured.get("persona_id") == "frugivoro"


@pytest.mark.asyncio
async def test_current_time_present_for_insult_no_persona_id(client):
    """Insult omits persona_id — the block must still be there (shared seam)."""
    await client.chat("sys", _msgs("qué onda"))
    ut = _FakeClient.captured["user_text"]
    assert "<current_time>" in ut
    assert "persona_id" not in _FakeClient.captured


@pytest.mark.asyncio
async def test_current_time_rides_first_before_other_blocks(client):
    """Non-cacheable time leads the dynamic tail: before memory/other-people and
    always before the user's own message."""
    await client.chat(
        "sys",
        _msgs("cuéntame"),
        relevant_memory="chunk",
        other_people="- Alex: dato",
    )
    ut = _FakeClient.captured["user_text"]
    assert ut.index("<current_time>") < ut.index("<relevant_memory>")
    assert ut.index("<current_time>") < ut.index("cuéntame")
