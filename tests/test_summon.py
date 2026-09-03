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

from demux_ai.summon import summon_and_wait, summon_persona


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


async def test_read_budget_outlasts_a_cold_gateway_boot():
    """A scaled-to-zero gateway must not be mistaken for a dead one.

    Container Apps' ingress holds the request open while the replica boots, so
    the cold start shows up as READ latency, not as a connection error. The old
    flat 5.0s budget expired mid-boot and dropped the summon silently; the read
    now has to outlast a real boot (~20-35s measured on this environment) while
    CONNECT stays short so a genuinely unreachable gateway still fails fast.
    """
    ctx, _ = _mock_async_client(202)
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx) as cliente:
        await summon_persona({"reason": "ven"}, channel_id="123")

    timeout = cliente.call_args.kwargs["timeout"]
    assert timeout.read >= 60.0, "el read no aguanta un arranque en frio"
    assert timeout.connect <= 10.0, "el connect dejo de fallar rapido"


# --- summon_and_wait: the host reads the turn's real outcome (2026-09-03) -----


def _mock_json_client(status_code: int, body: dict):
    resp = MagicMock(status_code=status_code, text=str(body))
    resp.json = MagicMock(return_value=body)
    client = MagicMock()
    client.post = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, client


async def test_wait_sends_the_flag_and_returns_delivered_on_200():
    ctx, client = _mock_json_client(200, {"status": "delivered", "channel_id": "123"})
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        outcome = await summon_and_wait({"reason": "ven"}, channel_id="123", persona_id="insult")
    assert outcome == "delivered"
    assert client.post.call_args.kwargs["json"]["wait"] is True


async def test_wait_returns_failed_on_502():
    ctx, _ = _mock_json_client(502, {"status": "failed", "channel_id": "123", "detail": "RuntimeError"})
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        outcome = await summon_and_wait({"reason": "ven"}, channel_id="123")
    assert outcome == "failed"


async def test_wait_transport_error_is_unreachable_not_failed():
    """A gateway that never answered is a different diagnosis from a persona
    that answered 'failed' — both retry, but KQL must tell them apart."""
    ctx, client = _mock_json_client(200, {})
    client.post = AsyncMock(side_effect=httpx.ReadTimeout("slow"))
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        outcome = await summon_and_wait({"reason": "ven"}, channel_id="123")
    assert outcome == "unreachable"


async def test_wait_read_budget_outlasts_a_whole_turn():
    """The gateway's runner call is budgeted at 240s; a shorter read here would
    report a slow-but-alive turn as unreachable and retry ON TOP of it."""
    ctx, _ = _mock_json_client(200, {"status": "delivered"})
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx) as cliente:
        await summon_and_wait({"reason": "ven"}, channel_id="123")
    assert cliente.call_args.kwargs["timeout"].read >= 240.0


async def test_fire_and_forget_never_sends_wait():
    ctx, client = _mock_async_client(202)
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        await summon_persona({"reason": "ven"}, channel_id="123")
    assert "wait" not in client.post.call_args.kwargs["json"]
