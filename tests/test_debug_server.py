"""Tests for the debug HTTP server."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

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
# /debug/moltbook/* — admin endpoints (Phase 5)
# ---------------------------------------------------------------------------


@pytest.fixture
def moltbook_ctx_unconfigured(memory_with_data):
    """No source — endpoints should 503 to signal 'lane not enabled here'."""
    from insult.core.debug_server import MoltbookDebugContext

    return MoltbookDebugContext(
        source_factory=lambda: None,
        llm=MagicMock(),
        settings=MagicMock(),
    )


@pytest.fixture
def moltbook_ctx_ready(memory_with_data):
    """Source + llm + settings populated for happy-path tests."""
    from insult.core.debug_server import MoltbookDebugContext
    from insult.core.sources.base import Post

    fake_source = MagicMock()
    fake_source.fetch_feed = AsyncMock(
        return_value=[
            Post(
                id="p1",
                title="t1",
                content="c1",
                author="DuckBot",
                submolt="m/philosophy",
                upvotes=5,
                comment_count=2,
                created_at=1700000000.0,
                source="moltbook",
            )
        ]
    )
    fake_source.fetch_submolt_posts = AsyncMock(return_value=[])
    fake_source.create_post = AsyncMock(
        return_value=Post(
            id="new_post_id",
            title="t",
            content="c",
            author="InsultMx",
            submolt="m/philosophy",
            upvotes=0,
            comment_count=0,
            created_at=1700000000.0,
            source="moltbook",
            url="https://www.moltbook.com/p/new_post_id",
        )
    )

    settings = MagicMock()
    settings.moltbook_submolts = ["m/philosophy"]
    settings.system_prompt = "persona"
    settings.summary_model = "haiku"

    llm = MagicMock()
    llm.client = MagicMock()
    llm.chat = AsyncMock(return_value=MagicMock(text='{"title":"T","content":"long enough content here"}'))
    response = MagicMock()
    response.content = [MagicMock(text="redacted version of the content keeping the take")]
    llm.client.messages.create = AsyncMock(return_value=response)

    return MoltbookDebugContext(source_factory=lambda: fake_source, llm=llm, settings=settings)


@pytest.fixture
async def client_with_moltbook(memory_with_data, moltbook_ctx_ready):
    from insult.core.debug_server import build_app

    app = build_app(memory_with_data, TOKEN, moltbook_ctx=moltbook_ctx_ready)
    async with TestClient(TestServer(app)) as c:
        yield c


@pytest.fixture
async def client_unconfigured(memory_with_data, moltbook_ctx_unconfigured):
    from insult.core.debug_server import build_app

    app = build_app(memory_with_data, TOKEN, moltbook_ctx=moltbook_ctx_unconfigured)
    async with TestClient(TestServer(app)) as c:
        yield c


async def test_moltbook_feed_requires_auth(client_with_moltbook):
    resp = await client_with_moltbook.get("/debug/moltbook/feed")
    assert resp.status == 401


async def test_moltbook_feed_503_when_unconfigured(client_unconfigured):
    resp = await client_unconfigured.get("/debug/moltbook/feed", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 503


async def test_moltbook_feed_returns_posts(client_with_moltbook):
    resp = await client_with_moltbook.get("/debug/moltbook/feed", headers={"Authorization": f"Bearer {TOKEN}"})
    assert resp.status == 200
    data = await resp.json()
    assert data["count"] == 1
    assert data["posts"][0]["id"] == "p1"


async def test_moltbook_feed_invalid_limit(client_with_moltbook):
    resp = await client_with_moltbook.get(
        "/debug/moltbook/feed?limit=abc",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status == 400


async def test_moltbook_feed_limit_out_of_range(client_with_moltbook):
    resp = await client_with_moltbook.get(
        "/debug/moltbook/feed?limit=999",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status == 400


async def test_moltbook_preview_requires_channel_id(client_with_moltbook):
    resp = await client_with_moltbook.get(
        "/debug/moltbook/preview-outbound",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status == 400


async def test_moltbook_preview_skipped_no_users(client_with_moltbook, memory_with_data):
    """Channel with no recent user messages → skip the pipeline."""
    memory_with_data.get_recent = AsyncMock(return_value=[])
    resp = await client_with_moltbook.get(
        "/debug/moltbook/preview-outbound?channel_id=ch1",
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status == 200
    data = await resp.json()
    assert data["skipped_reason"] == "no_users_in_channel"


async def test_moltbook_post_requires_hash(client_with_moltbook):
    resp = await client_with_moltbook.post(
        "/debug/moltbook/post",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"title": "x", "content": "y", "submolt": "m/x"},
    )
    assert resp.status == 400


async def test_moltbook_post_rejects_wrong_hash(client_with_moltbook):
    resp = await client_with_moltbook.post(
        "/debug/moltbook/post",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "title": "x",
            "content": "y",
            "submolt": "m/x",
            "preview_hash": "0" * 16,
        },
    )
    assert resp.status == 409


async def test_moltbook_post_publishes_with_correct_hash(client_with_moltbook):
    from insult.core.debug_server import _draft_hash

    title, content, submolt = "T", "C", "m/x"
    h = _draft_hash(title, content, submolt)
    resp = await client_with_moltbook.post(
        "/debug/moltbook/post",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"title": title, "content": content, "submolt": submolt, "preview_hash": h},
    )
    assert resp.status == 201
    data = await resp.json()
    assert data["published"] is True
    assert data["id"] == "new_post_id"


async def test_moltbook_post_503_when_unconfigured(client_unconfigured):
    resp = await client_unconfigured.post(
        "/debug/moltbook/post",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={"title": "x", "content": "y", "submolt": "m/x", "preview_hash": "x"},
    )
    assert resp.status == 503


async def test_draft_hash_is_stable():
    """Same inputs → same hash. Used by the operator to confirm preview."""
    from insult.core.debug_server import _draft_hash

    a = _draft_hash("title", "content", "m/x")
    b = _draft_hash("title", "content", "m/x")
    assert a == b


async def test_draft_hash_differs_on_any_change():
    """Changing any of (title, content, submolt) changes the hash."""
    from insult.core.debug_server import _draft_hash

    base = _draft_hash("title", "content", "m/x")
    assert _draft_hash("TITLE", "content", "m/x") != base
    assert _draft_hash("title", "CONTENT", "m/x") != base
    assert _draft_hash("title", "content", "m/y") != base
