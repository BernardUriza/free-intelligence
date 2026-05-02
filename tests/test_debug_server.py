"""Tests for the debug HTTP server."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from insult.core.debug_server import build_app

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
    mem.save_reminder = AsyncMock(return_value=42)
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
