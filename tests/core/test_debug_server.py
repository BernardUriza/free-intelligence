"""Tests for the debug HTTP server."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from personas.insult.core.debug_server import build_app

TOKEN = "test-token-xyz"  # noqa: S105 — fixture token, not a real secret


@pytest.fixture
def memory_with_data():
    mem = AsyncMock()
    mem.get_recent = AsyncMock(
        return_value=[
            {"user_name": "Bernard", "role": "user", "content": "hola", "timestamp": 1700000000.0},
            {"user_name": "Insult", "role": "assistant", "content": "que quieres", "timestamp": 1700000001.0},
        ]
    )
    mem.get_stats = AsyncMock(return_value={"total_messages": 42, "unique_users": 3, "unique_channels": 2})
    mem.get_channel_activity_since = AsyncMock(
        return_value=[{"channel_id": "111", "count": 20}, {"channel_id": "222", "count": 5}]
    )
    mem.get_channels_overview = AsyncMock(
        return_value=[
            {"channel_id": "111", "channel_name": "general", "guild_id": "gid", "count": 50, "last_ts": 1700000000.0},
            {"channel_id": "222", "channel_name": "random", "guild_id": "gid", "count": 10, "last_ts": 1699999000.0},
        ]
    )
    mem.get_channel_reminders = AsyncMock(
        return_value=[
            {
                "id": 1,
                "channel_id": "111",
                "guild_id": "gid",
                "created_by": "user1",
                "description": "comprar leche",
                "remind_at": 1700100000.0,
                "mention_user_ids": "",
                "recurring": "none",
            },
        ]
    )
    mem.get_facts = AsyncMock(
        return_value=[
            {"fact": "Estudió psicología sin titularse", "category": "professional", "ts": 1700000000.0},
            {"fact": "Trabajó como gerente en un bar de vino natural", "category": "professional", "ts": 1700000001.0},
            {"fact": "Tiene CPTSD diagnosticado", "category": "health", "ts": 1700000002.0},
        ]
    )
    mem.save_reminder = AsyncMock(return_value=42)
    mem.delete_reminder = AsyncMock(return_value=True)
    mem.update_reminder_fields = AsyncMock(return_value=True)
    mem.get_pending_reminders = AsyncMock(
        return_value=[
            {
                "id": 1,
                "channel_id": "111",
                "guild_id": "gid",
                "created_by": "user1",
                "description": "comprar leche",
                "remind_at": 1700100000.0,
                "mention_user_ids": "",
                "recurring": "none",
            },
            {
                "id": 2,
                "channel_id": "222",
                "guild_id": "gid",
                "created_by": "user2",
                "description": "gym",
                "remind_at": 1700200000.0,
                "mention_user_ids": "user2",
                "recurring": "daily",
            },
        ]
    )
    return mem


@pytest.fixture
async def client(memory_with_data):
    app = build_app(memory_with_data, TOKEN)
    async with TestClient(TestServer(app)) as c:
        yield c


async def test_health_no_auth_required(client):
    resp = await client.get("/debug/health")
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"


async def test_health_exposes_pr1_fields(client):
    """PR 1: /debug/health must expose readiness + bot-responsive signals
    so the KQL alert and Container Apps probe can distinguish liveness
    from readiness from zombie-handler."""
    from personas.insult.core.health_state import _reset_for_tests

    _reset_for_tests()
    resp = await client.get("/debug/health")
    data = await resp.json()
    # All keys must be present even on cold-start (None values are fine).
    for key in (
        "status",
        "healthy",
        "is_ready",
        "serving",
        "guild_count",
        "gateway_latency_ms",
        "last_turn_age_s",
        "last_turn_within_15min",
        "last_turn_outcome",
        "uptime_s",
        "turns_total",
        "pg",
    ):
        assert key in data, f"missing key in /debug/health: {key}"
    # Cold start: no turns, no bot wired.
    assert data["last_turn_age_s"] is None
    assert data["last_turn_within_15min"] is False
    assert data["last_turn_outcome"] is None
    assert data["turns_total"] == 0
    assert data["is_ready"] is None
    assert data["gateway_latency_ms"] is None
    # No bot wired and on_ready never completed → unambiguously not healthy.
    assert data["healthy"] is False
    assert data["serving"] is False
    assert data["guild_count"] is None
    # PG block always present, shape consistent across reachable/unreachable.
    assert "reachable" in data["pg"]
    assert "latency_ms" in data["pg"]
    assert "error" in data["pg"]


# ---------------------------------------------------------------------------
# /debug/health — PG reachability probe (v3.8.7 OBS-1)
# ---------------------------------------------------------------------------


async def test_health_pg_unreachable_when_pool_missing(client):
    """The default `memory_with_data` is AsyncMock — `_manager` is also
    AsyncMock, its `.pool` returns another AsyncMock object that isn't a
    real asyncpg.Pool, so `pool.acquire()` will raise. We assert that the
    probe handles ANY failure as `reachable=False` rather than 500'ing
    the endpoint — Azure liveness must stay 200 even when PG is gone."""
    resp = await client.get("/debug/health")
    assert resp.status == 200, "health must stay 200 even when PG is unreachable"
    data = await resp.json()
    assert data["status"] == "ok"  # never flipped by PG failure
    assert data["pg"]["reachable"] is False
    assert data["pg"]["latency_ms"] is None
    assert data["pg"]["error"] is not None


async def test_health_pg_reachable_when_pool_returns_one():
    """Wire a stub pool that answers `SELECT 1` in <1s and assert the
    endpoint reports `reachable=True` + a sensible latency."""
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    # Build a minimal asyncpg-Pool-shaped stub
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=1)

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    pool_stub = MagicMock()
    pool_stub.acquire = fake_acquire  # used as: `async with pool.acquire() as conn`

    mem = AsyncMock()
    mem._manager = MagicMock()
    mem._manager.pool = pool_stub

    app = build_app(mem, TOKEN)
    async with TestClient(TestServer(app)) as c:
        resp = await c.get("/debug/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["pg"]["reachable"] is True
        assert isinstance(data["pg"]["latency_ms"], int)
        assert data["pg"]["latency_ms"] < 1000
        assert data["pg"]["error"] is None


async def test_health_pg_timeout_does_not_500():
    """If the pool's SELECT 1 stalls past the 1s timeout, the probe MUST
    still return a 200 with `reachable=False, error=timeout_1s`. Liveness
    cannot blink off because of a slow query — Azure would needlessly
    restart the bot during a transient DB lock."""
    import asyncio as _asyncio
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock

    async def slow_fetchval(_sql):
        await _asyncio.sleep(3.0)  # past the 1s timeout
        return 1

    conn = MagicMock()
    conn.fetchval = slow_fetchval

    @asynccontextmanager
    async def fake_acquire():
        yield conn

    pool_stub = MagicMock()
    pool_stub.acquire = fake_acquire

    mem = AsyncMock()
    mem._manager = MagicMock()
    mem._manager.pool = pool_stub

    app = build_app(mem, TOKEN)
    async with TestClient(TestServer(app)) as c:
        resp = await c.get("/debug/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "ok"
        assert data["pg"]["reachable"] is False
        assert data["pg"]["error"] == "timeout_1s"


async def test_health_reflects_recorded_turn(client):
    """After a turn is recorded, the endpoint reports a fresh age."""
    from personas.insult.core.health_state import _reset_for_tests, get_state

    _reset_for_tests()
    get_state().record_turn_end("ok")
    resp = await client.get("/debug/health")
    data = await resp.json()
    assert data["turns_total"] == 1
    assert data["last_turn_outcome"] == "ok"
    assert data["last_turn_within_15min"] is True
    assert data["last_turn_age_s"] is not None
    assert data["last_turn_age_s"] < 1.0
    _reset_for_tests()


async def test_health_reflects_bot_ref(client):
    """When the bot ref is wired, is_ready and gateway_latency_ms are set."""
    from unittest.mock import MagicMock

    from personas.insult.core.health_state import _reset_for_tests, get_state

    _reset_for_tests()
    bot = MagicMock()
    bot.is_ready = MagicMock(return_value=True)
    bot.latency = 0.025  # 25 ms
    bot.guilds = [object()]
    get_state().set_bot(bot)
    resp = await client.get("/debug/health")
    data = await resp.json()
    assert data["is_ready"] is True
    assert data["gateway_latency_ms"] == 25.0
    # set_bot alone (boot still mid-on_ready) must NOT read healthy.
    assert data["serving"] is False
    assert data["healthy"] is False
    _reset_for_tests()


async def test_health_zombie_ready_but_not_serving(client):
    """The 2026-06-13 outage shape, end-to-end through the endpoint: the
    gateway is ready (is_ready=true, real latency, in a guild) but on_ready
    hung before wiring the cogs, so serving was never marked. The endpoint
    must report healthy=false — the false-positive that misled diagnosis."""
    from unittest.mock import MagicMock

    from personas.insult.core.health_state import _reset_for_tests, get_state

    _reset_for_tests()
    bot = MagicMock()
    bot.is_ready = MagicMock(return_value=True)
    bot.latency = 0.0151
    bot.guilds = [object()]
    get_state().set_bot(bot)  # mark_serving() intentionally NOT called
    resp = await client.get("/debug/health")
    data = await resp.json()
    assert data["is_ready"] is True
    assert data["gateway_latency_ms"] == 15.1
    assert data["guild_count"] == 1
    assert data["serving"] is False
    assert data["healthy"] is False
    _reset_for_tests()


async def test_health_fully_wired_is_healthy(client):
    """Positive case: set_bot + mark_serving + in a guild → healthy=true."""
    from unittest.mock import MagicMock

    from personas.insult.core.health_state import _reset_for_tests, get_state

    _reset_for_tests()
    bot = MagicMock()
    bot.is_ready = MagicMock(return_value=True)
    bot.latency = 0.02
    bot.guilds = [object()]
    state = get_state()
    state.set_bot(bot)
    state.mark_serving()
    resp = await client.get("/debug/health")
    data = await resp.json()
    assert data["serving"] is True
    assert data["healthy"] is True
    _reset_for_tests()


async def test_messages_requires_auth(client):
    resp = await client.get("/debug/messages?channel_id=123")
    assert resp.status == 401


async def test_messages_rejects_wrong_token(client):
    resp = await client.get("/debug/messages?channel_id=123", headers={"Authorization": "Bearer wrong"})
    assert resp.status == 401


async def test_messages_rejects_missing_bearer_prefix(client):
    resp = await client.get("/debug/messages?channel_id=123", headers={"Authorization": TOKEN})
    assert resp.status == 401


async def test_messages_returns_data_with_valid_token(client, memory_with_data):
    resp = await client.get("/debug/messages?channel_id=555&limit=15", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    data = await resp.json()
    assert data["channel_id"] == "555"
    assert data["count"] == 2
    assert len(data["messages"]) == 2
    assert data["messages"][0]["user_name"] == "Bernard"
    memory_with_data.get_recent.assert_awaited_once_with("555", limit=15)


async def test_messages_missing_channel_id(client):
    resp = await client.get("/debug/messages", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 400


async def test_messages_invalid_limit(client):
    resp = await client.get(
        "/debug/messages?channel_id=555&limit=notanumber", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert resp.status == 400


async def test_messages_limit_out_of_range(client):
    resp = await client.get("/debug/messages?channel_id=555&limit=9999", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 400


async def test_messages_default_limit(client, memory_with_data):
    resp = await client.get("/debug/messages?channel_id=555", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    memory_with_data.get_recent.assert_awaited_once_with("555", limit=15)


async def test_stats_endpoint(client):
    resp = await client.get("/debug/stats", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    data = await resp.json()
    assert data["total_messages"] == 42
    assert data["unique_users"] == 3


async def test_stats_requires_auth(client):
    resp = await client.get("/debug/stats")
    assert resp.status == 401


async def test_channels_endpoint(client, memory_with_data):
    resp = await client.get("/debug/channels?guild_id=abc&since_hours=1", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    data = await resp.json()
    assert data["guild_id"] == "abc"
    assert data["since_hours"] == 1
    assert data["count"] == 2
    assert data["channels"][0]["channel_id"] == "111"
    memory_with_data.get_channel_activity_since.assert_awaited_once()


async def test_channels_without_guild_returns_overview(client, memory_with_data):
    """When guild_id is omitted, /debug/channels returns overview of all channels."""
    resp = await client.get("/debug/channels", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    data = await resp.json()
    assert data["count"] == 2
    assert data["channels"][0]["channel_name"] == "general"
    memory_with_data.get_channels_overview.assert_awaited_once_with(limit=50)


async def test_channels_overview_custom_limit(client, memory_with_data):
    resp = await client.get("/debug/channels?limit=10", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    memory_with_data.get_channels_overview.assert_awaited_once_with(limit=10)


async def test_channels_overview_invalid_limit(client):
    resp = await client.get("/debug/channels?limit=notanumber", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 400


async def test_channels_invalid_since_hours(client):
    resp = await client.get(
        "/debug/channels?guild_id=abc&since_hours=nope", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert resp.status == 400


async def test_reminders_all_pending(client, memory_with_data):
    resp = await client.get("/debug/reminders", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    data = await resp.json()
    assert data["count"] == 2
    assert data["reminders"][0]["description"] == "comprar leche"
    assert data["reminders"][1]["recurring"] == "daily"
    memory_with_data.get_pending_reminders.assert_awaited_once()


async def test_reminders_by_channel(client, memory_with_data):
    resp = await client.get("/debug/reminders?channel_id=111", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    data = await resp.json()
    assert data["count"] == 1
    memory_with_data.get_channel_reminders.assert_awaited_once_with("111")


async def test_reminders_requires_auth(client):
    resp = await client.get("/debug/reminders")
    assert resp.status == 401


async def test_create_reminder_requires_auth(client):
    resp = await client.post("/debug/reminders", json={"channel_id": "1", "description": "x", "remind_at": "x"})
    assert resp.status == 401


async def test_create_reminder_rejects_missing_fields(client):
    resp = await client.post(
        "/debug/reminders",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"channel_id": "111"},
    )
    assert resp.status == 400


async def test_create_reminder_rejects_past_time(client):
    resp = await client.post(
        "/debug/reminders",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"channel_id": "111", "description": "x", "remind_at": "2000-01-01T00:00:00-06:00"},
    )
    assert resp.status == 400


async def test_create_reminder_success(client, memory_with_data):
    resp = await client.post(
        "/debug/reminders",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "channel_id": "111",
            "guild_id": "gid",
            "description": "llamar a la dentista",
            "remind_at": "2099-01-01T09:00:00-06:00",
            "mention_user_ids": ["907264175246569543"],
            "created_by": "admin",
        },
    )
    assert resp.status == 201
    data = await resp.json()
    assert data["id"] == 42
    assert data["description"] == "llamar a la dentista"
    memory_with_data.save_reminder.assert_awaited_once()
    kwargs = memory_with_data.save_reminder.await_args.kwargs
    assert kwargs["channel_id"] == "111"
    assert kwargs["mention_user_ids"] == "907264175246569543"
    assert kwargs["recurring"] == "none"


async def test_create_reminder_invalid_recurring(client):
    resp = await client.post(
        "/debug/reminders",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "channel_id": "111",
            "description": "x",
            "remind_at": "2099-01-01T09:00:00-06:00",
            "recurring": "yearly",
        },
    )
    assert resp.status == 400


async def test_create_reminder_invalid_json(client):
    resp = await client.post(
        "/debug/reminders",
        headers={"Authorization": f"Bearer {TOKEN}"},
        data="not json",
    )
    assert resp.status == 400


async def test_delete_reminder_requires_auth(client):
    resp = await client.delete("/debug/reminders/4")
    assert resp.status == 401


async def test_delete_reminder_invalid_id(client):
    resp = await client.delete("/debug/reminders/abc", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 400


async def test_delete_reminder_success(client, memory_with_data):
    resp = await client.delete("/debug/reminders/4", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    data = await resp.json()
    assert data == {"id": 4, "deleted": True}
    memory_with_data.delete_reminder.assert_awaited_once_with(4)


async def test_delete_reminder_not_found(client, memory_with_data):
    memory_with_data.delete_reminder = AsyncMock(return_value=False)
    resp = await client.delete("/debug/reminders/999", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 404


async def test_patch_reminder_requires_auth(client):
    resp = await client.patch("/debug/reminders/4", json={"description": "x"})
    assert resp.status == 401


async def test_patch_reminder_invalid_id(client):
    resp = await client.patch(
        "/debug/reminders/abc",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"description": "x"},
    )
    assert resp.status == 400


async def test_patch_reminder_empty_payload(client):
    resp = await client.patch(
        "/debug/reminders/4",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={},
    )
    assert resp.status == 400


async def test_patch_reminder_blank_description(client):
    resp = await client.patch(
        "/debug/reminders/4",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"description": "   "},
    )
    assert resp.status == 400


async def test_patch_reminder_past_remind_at(client):
    resp = await client.patch(
        "/debug/reminders/4",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"remind_at": "2000-01-01T00:00:00-06:00"},
    )
    assert resp.status == 400


async def test_patch_reminder_success_description_only(client, memory_with_data):
    resp = await client.patch(
        "/debug/reminders/4",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"description": "nuevo texto"},
    )
    assert resp.status == 200
    memory_with_data.update_reminder_fields.assert_awaited_once()
    kwargs = memory_with_data.update_reminder_fields.await_args.kwargs
    assert kwargs["new_description"] == "nuevo texto"
    assert kwargs["new_remind_at"] is None


async def test_patch_reminder_success_remind_at_only(client, memory_with_data):
    resp = await client.patch(
        "/debug/reminders/4",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"remind_at": "2099-06-01T08:00:00-06:00"},
    )
    assert resp.status == 200
    kwargs = memory_with_data.update_reminder_fields.await_args.kwargs
    assert kwargs["new_remind_at"] is not None
    assert kwargs["new_description"] is None


async def test_patch_reminder_not_found(client, memory_with_data):
    memory_with_data.update_reminder_fields = AsyncMock(return_value=False)
    resp = await client.patch(
        "/debug/reminders/999",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"description": "x"},
    )
    assert resp.status == 404


# ---------------------------------------------------------------------------
# /sync/serenityops — per-user bearer auth + snapshot persistence (v3.8.0 SY-2)
# ---------------------------------------------------------------------------
#
# The sync endpoint uses a DIFFERENT auth path than /debug/*: each user has
# their own bearer token stored hashed in user_sync_tokens, and the middleware
# resolves it via `memory.resolve_sync_token(plain) -> user_id | None`. Tests
# below pin: rejection when token unknown, rejection when body malformed,
# happy path persists snapshot with resolved user_id.


@pytest.fixture
async def sync_client():
    """Variant of the client fixture wired with a memory mock that knows about
    sync tokens. The handler resolves bearer → user_id and writes a snapshot."""
    mem = AsyncMock()
    # Token resolves to alex; any other token returns None (rejected).
    mem.resolve_sync_token = AsyncMock(
        side_effect=lambda t: "alex-1431300030823927999" if t == "user-token-alex" else None
    )
    mem.insert_serenityops_snapshot = AsyncMock(return_value=77)
    app = build_app(mem, TOKEN)
    async with TestClient(TestServer(app)) as c:
        yield c, mem


async def test_sync_rejects_missing_bearer(sync_client):
    client, _ = sync_client
    resp = await client.post("/sync/serenityops", json={"curriculum": {"x": 1}})
    assert resp.status == 401


async def test_sync_rejects_unknown_token(sync_client):
    client, _ = sync_client
    resp = await client.post(
        "/sync/serenityops",
        json={"curriculum": {"x": 1}},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status == 401


async def test_sync_rejects_non_json_body(sync_client):
    client, _ = sync_client
    resp = await client.post(
        "/sync/serenityops",
        data="not-json-at-all",
        headers={"Authorization": "Bearer user-token-alex", "Content-Type": "application/json"},
    )
    assert resp.status == 400


async def test_sync_rejects_array_body(sync_client):
    """The endpoint expects a JSON object — top-level array is invalid input."""
    client, _ = sync_client
    resp = await client.post(
        "/sync/serenityops",
        json=[],
        headers={"Authorization": "Bearer user-token-alex"},
    )
    assert resp.status == 400


async def test_sync_rejects_empty_body(sync_client):
    """At least one of curriculum/opportunities must be present."""
    client, _ = sync_client
    resp = await client.post(
        "/sync/serenityops",
        json={"client_version": "lite-1.0.0"},
        headers={"Authorization": "Bearer user-token-alex"},
    )
    assert resp.status == 400


async def test_sync_persists_snapshot_and_returns_id(sync_client):
    """Happy path: snapshot row is appended; response carries id + user_id."""
    client, mem = sync_client
    payload = {
        "curriculum": {"personal": {"full_name": "Alex"}},
        "opportunities": {"pipeline": []},
        "client_version": "lite-1.0.0",
    }
    resp = await client.post(
        "/sync/serenityops",
        json=payload,
        headers={"Authorization": "Bearer user-token-alex"},
    )
    assert resp.status == 201
    data = await resp.json()
    assert data["ok"] is True
    assert data["snapshot_id"] == 77
    assert data["user_id"] == "alex-1431300030823927999"
    mem.insert_serenityops_snapshot.assert_awaited_once_with(
        "alex-1431300030823927999",
        {"personal": {"full_name": "Alex"}},
        {"pipeline": []},
        "lite-1.0.0",
    )


async def test_sync_accepts_curriculum_only(sync_client):
    """Either payload alone is enough — the endpoint should not require both."""
    client, mem = sync_client
    resp = await client.post(
        "/sync/serenityops",
        json={"curriculum": {"summary": "psicóloga 15 años"}},
        headers={"Authorization": "Bearer user-token-alex"},
    )
    assert resp.status == 201
    mem.insert_serenityops_snapshot.assert_awaited_once_with(
        "alex-1431300030823927999",
        {"summary": "psicóloga 15 años"},
        None,
        None,
    )
