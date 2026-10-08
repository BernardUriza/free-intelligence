"""Text no model ever generated must NEVER reach Discord.

2026-07-19: a revoked OAuth token made the runner answer every turn with
`Failed to authenticate. API Error: 401 ...` — 0 tokens, 200 OK. The gateway
delivered it verbatim, in English, with the version tag appended, for 4.5 hours,
into a live conversation between two real people. Every green light stayed green
(`Running`, `200 OK`, `turn_complete`); the only honest signal was that a turn
had produced text while spending ZERO output tokens.

The guard raises `PersonaTurnError` — the same path the invalid-JSON case
already used — so the gateway's turn guard degrades to its in-character "…"
instead of speaking the vendor's error.

Resistance cases matter as much as the positive one: this is a destructive
mutator on the delivery path, and a false positive silences a real answer.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from persona_core.runner.agent_client import AgentRunnerClient, PersonaTurnError

AUTH_ERROR = "Failed to authenticate. API Error: 401 Invalid authentication credentials"


def _client() -> AgentRunnerClient:
    return AgentRunnerClient("http://runner", "tok")


def _patch_response(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]) -> None:
    """Make the client's HTTP round-trip return `payload` as the runner's JSON."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.text = "{}"

    class _AsyncClient:
        def __init__(self, *a, **k): ...
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *a, **k):
            return resp

    monkeypatch.setattr("persona_core.runner.agent_client.httpx.AsyncClient", _AsyncClient)


MESSAGES = [{"role": "user", "content": "hola"}]


async def test_auth_error_text_with_zero_output_tokens_raises(monkeypatch):
    """THE BUG: 200 OK + prose + 0 tokens is an infra failure wearing an answer."""
    _patch_response(
        monkeypatch,
        {"text": AUTH_ERROR, "input_tokens": 0, "output_tokens": 0, "model": "claude-sonnet-4-6"},
    )
    with pytest.raises(PersonaTurnError) as exc:
        await _client().chat("", MESSAGES, user_id="1", channel_id="c")
    assert "no generation" in str(exc.value)


async def test_the_vendor_string_never_becomes_the_reply(monkeypatch):
    """What the users actually saw must not be returnable as a persona turn."""
    _patch_response(monkeypatch, {"text": AUTH_ERROR, "output_tokens": 0})
    with pytest.raises(PersonaTurnError):
        await _client().chat("", MESSAGES, user_id="1", channel_id="c")


async def test_healthy_turn_passes_through(monkeypatch):
    """RESISTANCE: a real generation spends output tokens — never blocked."""
    _patch_response(
        monkeypatch,
        {"text": "ya estoy", "input_tokens": 8, "output_tokens": 4903, "model": "claude-sonnet-4-6"},
    )
    resp = await _client().chat("", MESSAGES, user_id="1", channel_id="c")
    assert resp.text == "ya estoy"


async def test_cache_read_turn_with_zero_input_tokens_is_not_blocked(monkeypatch):
    """RESISTANCE: input_tokens=0 is legitimate on a cache read. Only OUTPUT
    tokens prove generation — guarding on input would silence real answers."""
    _patch_response(monkeypatch, {"text": "respuesta real", "input_tokens": 0, "output_tokens": 120})
    resp = await _client().chat("", MESSAGES, user_id="1", channel_id="c")
    assert resp.text == "respuesta real"


async def test_tool_only_turn_is_not_blocked(monkeypatch):
    """RESISTANCE: a turn that acted through tools may report no output tokens."""
    _patch_response(
        monkeypatch,
        {"text": "consultando", "output_tokens": 0, "tool_calls": [{"name": "get_facts"}]},
    )
    resp = await _client().chat("", MESSAGES, user_id="1", channel_id="c")
    assert resp.text == "consultando"


async def test_empty_text_is_not_a_zero_generation_failure(monkeypatch):
    """RESISTANCE: silence is a valid turn; only TEXT without generation lies."""
    _patch_response(monkeypatch, {"text": "", "output_tokens": 0})
    resp = await _client().chat("", MESSAGES, user_id="1", channel_id="c")
    assert resp.text == ""


async def test_missing_usage_field_does_not_accuse(monkeypatch):
    """RESISTANCE: absent ≠ zero. A runner build that reports no usage at all is
    UNKNOWN, and unknown must never silence a real answer — only an explicit 0
    is evidence that nothing was generated."""
    _patch_response(monkeypatch, {"text": "respuesta sin usage", "model": "agent-runner"})
    resp = await _client().chat("", MESSAGES, user_id="1", channel_id="c")
    assert resp.text == "respuesta sin usage"


async def test_whitespace_only_text_is_not_flagged(monkeypatch):
    _patch_response(monkeypatch, {"text": "   \n ", "output_tokens": 0})
    resp = await _client().chat("", MESSAGES, user_id="1", channel_id="c")
    assert resp.text.strip() == ""


async def test_null_output_tokens_does_not_accuse(monkeypatch):
    """RESISTANCE: the runner now sends `null` (not 0) when AIRE reported no
    usage — the 2026-09-03 budget-cut shape. Null is unknown, never evidence."""
    _patch_response(monkeypatch, {"text": "Visto, amix.", "input_tokens": None, "output_tokens": None})
    resp = await _client().chat("", MESSAGES, user_id="1", channel_id="c")
    assert resp.text == "Visto, amix."
