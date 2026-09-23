"""demux_ai.summon — the host-side /invite client contract.

The summon client is the wire between whoever owns reception and the persona
gateway. Positive: a 202 returns True and the payload carries every optional
field (persona_id, invited_by, trigger_message_id — the 2026-07-14 reactions
fix). Resistance: missing token / empty reason / non-202 / network error all
return False without raising.
"""

from __future__ import annotations

import re
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


async def test_wait_read_budget_is_below_the_ingress_cap():
    """Hasta el 2026-09-19 esto exigía ≥240 s: una request sosteniendo el turno
    entero. El ingress corta a los 240 s haga lo que haga el número, así que la
    espera va por boleto y cada request queda por debajo del tope."""
    ctx, _ = _mock_json_client(200, {"status": "delivered"})
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx) as cliente:
        await summon_and_wait({"reason": "ven"}, channel_id="123")
    assert cliente.call_args.kwargs["timeout"].read < 240.0


async def test_fire_and_forget_never_sends_wait():
    ctx, client = _mock_async_client(202)
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        await summon_persona({"reason": "ven"}, channel_id="123")
    assert "wait" not in client.post.call_args.kwargs["json"]


# --- boleto (2026-09-19): el turno deja de viajar en UNA request ----------------


def _scripted_client(script: list):
    """POST y GET consumen el mismo guion, en orden."""
    client = MagicMock()
    it = iter(script)

    async def _next(*_a, **_k):
        item = next(it)
        if isinstance(item, BaseException):
            raise item
        return item

    client.post = AsyncMock(side_effect=_next)
    client.get = AsyncMock(side_effect=_next)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, client


def _json_resp(status_code: int, body: dict):
    resp = MagicMock(status_code=status_code, text=str(body))
    resp.json = MagicMock(return_value=body)
    return resp


async def test_wait_asks_for_a_ticket_and_polls_until_the_outcome(monkeypatch):
    """El caso del 2026-09-19: un turno de 327 s. Antes el host cortaba a los 240 s
    y reintentaba ENCIMA; ahora pregunta por el boleto hasta que el gateway diga."""
    ctx, client = _scripted_client(
        [
            _json_resp(202, {"status": "running", "channel_id": "123", "turn_id": "t1"}),
            _json_resp(200, {"status": "running", "channel_id": "123", "turn_id": "t1"}),
            _json_resp(200, {"status": "running", "channel_id": "123", "turn_id": "t1"}),
            _json_resp(200, {"status": "delivered", "channel_id": "123", "turn_id": "t1"}),
        ]
    )
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        outcome = await summon_and_wait({"reason": "ven"}, channel_id="123", persona_id="vultur")
    assert outcome == "delivered"
    assert client.post.call_args.kwargs["json"]["ticket"] is True
    assert client.get.await_count == 3
    assert client.get.call_args.args[0].endswith("/invite/turns/t1")


async def test_no_single_request_of_the_wait_carries_the_turn_budget():
    ctx, _ = _scripted_client(
        [
            _json_resp(202, {"status": "running", "channel_id": "123", "turn_id": "t1"}),
            _json_resp(200, {"status": "delivered", "channel_id": "123", "turn_id": "t1"}),
        ]
    )
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx) as cliente:
        await summon_and_wait({"reason": "ven"}, channel_id="123")
    assert all(c.kwargs["timeout"].read < 240.0 for c in cliente.call_args_list)


async def test_an_old_gateway_that_answers_the_wait_inline_still_works():
    """Un gateway sin boletos ignora `ticket` y contesta el `wait` en la misma
    request: el host lo lee igual que antes, sin poll."""
    ctx, client = _scripted_client([_json_resp(200, {"status": "delivered", "channel_id": "123"})])
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        outcome = await summon_and_wait({"reason": "ven"}, channel_id="123")
    assert outcome == "delivered"
    client.get.assert_not_awaited()


async def test_a_ticket_that_vanishes_is_unreachable_so_the_retry_lands_on_the_new_replica():
    ctx, _ = _scripted_client(
        [
            _json_resp(202, {"status": "running", "channel_id": "123", "turn_id": "t1"}),
            _json_resp(404, {"detail": "unknown turn 't1'"}),
        ]
    )
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        outcome = await summon_and_wait({"reason": "ven"}, channel_id="123")
    assert outcome == "unreachable"


async def test_a_poll_that_drops_on_the_network_is_asked_again(monkeypatch):
    async def _no_sleep(_s):
        return None

    monkeypatch.setattr("demux_ai.summon.asyncio.sleep", _no_sleep)
    ctx, client = _scripted_client(
        [
            _json_resp(202, {"status": "running", "channel_id": "123", "turn_id": "t1"}),
            httpx.ReadTimeout("poll dropped"),
            _json_resp(200, {"status": "failed", "channel_id": "123", "turn_id": "t1"}),
        ]
    )
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        outcome = await summon_and_wait({"reason": "ven"}, channel_id="123")
    assert outcome == "failed"
    assert client.get.await_count == 2


# --- el boleto del host (2026-09-23): el id nace aquí y viaja en el alta ----------


async def test_the_wait_carries_a_host_minted_turn_id():
    ctx, client = _mock_json_client(200, {"status": "delivered", "channel_id": "123"})
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        await summon_and_wait({"reason": "ven"}, channel_id="123")
    turn_id = client.post.call_args.kwargs["json"]["turn_id"]
    assert re.fullmatch(r"[0-9a-f]{32}", turn_id)


async def test_a_given_turn_id_travels_verbatim():
    ctx, client = _mock_json_client(200, {"status": "delivered", "channel_id": "123"})
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        await summon_and_wait({"reason": "ven"}, channel_id="123", turn_id="host-abc")
    assert client.post.call_args.kwargs["json"]["turn_id"] == "host-abc"


async def test_an_old_gateway_that_mints_its_own_id_is_polled_on_its_id():
    ctx, client = _scripted_client(
        [
            _json_resp(202, {"status": "running", "channel_id": "123", "turn_id": "gw1"}),
            _json_resp(200, {"status": "delivered", "channel_id": "123", "turn_id": "gw1"}),
        ]
    )
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        outcome = await summon_and_wait({"reason": "ven"}, channel_id="123", turn_id="host-abc")
    assert outcome == "delivered"
    assert client.get.call_args.args[0].endswith("/invite/turns/gw1")


async def test_uncertain_is_a_terminal_outcome_the_host_reads_as_is():
    ctx, _ = _scripted_client(
        [
            _json_resp(202, {"status": "running", "channel_id": "123", "turn_id": "t1"}),
            _json_resp(200, {"status": "uncertain", "channel_id": "123", "turn_id": "t1"}),
        ]
    )
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        assert await summon_and_wait({"reason": "ven"}, channel_id="123") == "uncertain"
    ctx, _ = _mock_json_client(200, {"status": "uncertain", "channel_id": "123"})
    with patch("demux_ai.summon.httpx.AsyncClient", return_value=ctx):
        assert await summon_and_wait({"reason": "ven"}, channel_id="123") == "uncertain"
