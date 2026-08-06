"""demux_ai.summon — the host-side /invite client contract.

The summon client is the wire between whoever owns reception and the persona
gateway. Positive: a 202 returns True and the payload carries every optional
field (persona_id, invited_by, trigger_message_id — the 2026-07-14 reactions
fix). Resistance: missing token / empty reason / non-202 / network error all
return False without raising.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from demux_ai.summon import summon_persona


def _mock_async_client(status_code: int = 202, text: str = ""):
    resp = MagicMock(status_code=status_code, text=text)
    client = MagicMock()
    client.post = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, client


@pytest.fixture(autouse=True)
def _invite_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_INVITE_URL", "http://gateway.internal/invite")
    monkeypatch.setenv("GATEWAY_INVITE_TOKEN", "t0ken")


async def test_202_returns_true_and_payload_carries_all_fields():
    ctx, client = _mock_async_client(202)
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        ok = await summon_persona(
            {"reason": "toma el turno"},
            channel_id="123",
            guild_id="456",
            channel_name="general",
            persona_id="vultur",
            invited_by="host_router",
            trigger_message_id="1526655478313127987",
        )
    assert ok is True
    payload = client.post.call_args.kwargs["json"]
    assert payload["channel_id"] == "123"
    assert payload["reason"] == "toma el turno"
    assert payload["persona_id"] == "vultur"
    assert payload["invited_by"] == "host_router"
    assert payload["trigger_message_id"] == "1526655478313127987"


async def test_optional_fields_omitted_when_absent():
    ctx, client = _mock_async_client(202)
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        ok = await summon_persona({"reason": "ven"}, channel_id="123")
    assert ok is True
    payload = client.post.call_args.kwargs["json"]
    assert "persona_id" not in payload
    assert "invited_by" not in payload
    assert "trigger_message_id" not in payload


async def test_missing_token_returns_false_without_calling(monkeypatch):
    monkeypatch.setenv("GATEWAY_INVITE_TOKEN", "")
    ctx, client = _mock_async_client(202)
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        ok = await summon_persona({"reason": "ven"}, channel_id="123")
    assert ok is False
    client.post.assert_not_called()


async def test_empty_reason_returns_false_without_calling():
    ctx, client = _mock_async_client(202)
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        ok = await summon_persona({"reason": "   "}, channel_id="123")
    assert ok is False
    client.post.assert_not_called()


async def test_non_202_returns_false():
    ctx, _ = _mock_async_client(401, "bad token")
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        ok = await summon_persona({"reason": "ven"}, channel_id="123")
    assert ok is False


async def test_network_error_swallowed_returns_false():
    ctx, client = _mock_async_client(202)
    client.post = AsyncMock(side_effect=httpx.ConnectError("down"))
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        ok = await summon_persona({"reason": "ven"}, channel_id="123")
    assert ok is False
