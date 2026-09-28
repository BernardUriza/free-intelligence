"""The runner client must replay the recent CHANNEL conversation into user_text.

The runner DISCARDS the plumbing-built `messages[]` and keeps only PER-USER
session state, so it never sees what OTHER participants just said. Concrete
bug (2026-06-05, #general): Bernard names the film "Creep" in his own message;
seconds later Alex says "me dio ptsd la peli" WITHOUT naming it — her turn's
session never saw Bernard's line, so the bot answered "¿cuál peli?". The fix
replays the tail of the shared channel as a <recent_conversation> block in the
user_text the runner DOES read, mirroring `relevant_memory` / `other_people`.

Mutator rule: positive (prior turns reach user_text) + resistance (a lone
message leaves user_text clean) + ordering (recent context is closest to the
current message).
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from persona_core.runner.agent_client import (
    _RECENT_CONTEXT_MAX_CHARS,
    AgentRunnerClient,
    _format_recent_context,
)


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


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("persona_core.runner.agent_client.httpx.AsyncClient", _FakeClient)
    _FakeClient.captured = {}
    return AgentRunnerClient("http://runner", "tok")


# The #general thread, Anthropic-shape as the plumbing builds it: prior turns
# are speaker-prefixed strings; the final entry is the current user message.
def _creep_thread() -> list[dict]:
    return [
        {"role": "user", "content": "Bernard: deja la pongo en party"},
        {"role": "assistant", "content": "Va bebe, ponle. Que Alex no se asuste sola."},
        {"role": "user", "content": "Bernard: Creep sí jala, found footage barato"},
        {"role": "user", "content": "Alex: a mi me dio ptsd la peli jajajaj"},
    ]


@pytest.mark.asyncio
async def test_recent_conversation_reaches_user_text(client):
    """POSITIVE: prior channel turns ride along so 'la peli' resolves to Creep."""
    await client.chat("discarded system prompt", _creep_thread())
    ut = _FakeClient.captured["user_text"]
    assert "<recent_conversation>" in ut
    assert "Creep" in ut  # the answer to "¿cuál peli?" is now in front of the runner
    assert "Bernard: deja la pongo en party" in ut
    # The current message is still the payload, and comes AFTER the context.
    assert "a mi me dio ptsd la peli" in ut
    assert ut.index("Creep sí jala") < ut.rindex("a mi me dio ptsd la peli")


@pytest.mark.asyncio
async def test_single_message_leaves_user_text_clean(client):
    """RESISTANCE: a lone message has no prior context — no stray block."""
    await client.chat("sys", [{"role": "user", "content": "hola bot"}])
    ut = _FakeClient.captured["user_text"]
    # <current_time> always rides along now; the message is the tail.
    assert ut.endswith("hola bot")
    assert "recent_conversation" not in ut


@pytest.mark.asyncio
async def test_recent_context_ordering_with_other_blocks(client):
    """Recent conversation is closest to the current message (after memory/people)."""
    await client.chat(
        "sys",
        _creep_thread(),
        relevant_memory="chunk viejo",
        other_people="- Alex: dato",
    )
    ut = _FakeClient.captured["user_text"]
    assert ut.index("relevant_memory") < ut.index("recent_conversation")
    assert ut.index("other_people_in_channel") < ut.index("recent_conversation")
    assert ut.index("recent_conversation") < ut.rindex("a mi me dio ptsd la peli")


def test_format_recent_context_excludes_current_and_caps():
    """Helper drops the final (current) message and truncates from the front."""
    msgs = [{"role": "user", "content": f"linea {i}: " + "x" * 200} for i in range(40)]
    msgs.append({"role": "user", "content": "MENSAJE ACTUAL"})
    out = _format_recent_context(msgs)
    assert "MENSAJE ACTUAL" not in out  # current message is excluded
    assert len(out) <= _RECENT_CONTEXT_MAX_CHARS + 2  # "…\n" prefix allowed
    assert out.startswith("…")  # truncated from the front, freshest tail kept


def test_format_recent_context_empty_for_lone_message():
    assert _format_recent_context([{"role": "user", "content": "solo"}]) == ""
    assert _format_recent_context([]) == ""
