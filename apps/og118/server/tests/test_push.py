"""OG118-PUSH-1 — a late answer is announced on the account's phones, and a failed
announcement never loses the answer it rides on."""

from __future__ import annotations

import pytest

from routes import chat as chat_routes
import deps
import push
from conversations import ConversationStore

OWNER = "auth0|owner"
OTHER = "auth0|someone-else"
CID = "c0ffee00-0000-4000-8000-000000000002"
TOKEN = "ab" * 32


def _devices(tmp_path) -> push.DeviceStore:
    return push.DeviceStore(tmp_path / "devices")


def _recorder(status=200, reason=""):
    sent = []

    async def send(token, environment, payload):
        sent.append((token, environment, payload))
        return status, reason

    return sent, send


@pytest.mark.asyncio
async def test_every_device_of_the_account_and_only_that_account_is_told(tmp_path) -> None:
    store = _devices(tmp_path)
    store.register(OWNER, TOKEN, "production")
    store.register(OWNER, "cd" * 32, "development")
    store.register(OTHER, "ef" * 32, "production")
    sent, send = _recorder()
    delivered = await push.notify(store, OWNER, "Yodo", "aquí sigo", CID, send=send)
    assert delivered == 2
    assert sorted(t for t, _, _ in sent) == sorted([TOKEN, "cd" * 32])
    assert {e for _, e, _ in sent} == {"production", "development"}
    payload = sent[0][2]
    assert payload["aps"]["alert"] == {"title": "Yodo", "body": "aquí sigo"}
    assert payload["conversation_id"] == CID and payload["aps"]["thread-id"] == CID


@pytest.mark.asyncio
async def test_a_token_apple_no_longer_knows_is_forgotten(tmp_path) -> None:
    store = _devices(tmp_path)
    store.register(OWNER, TOKEN, "production")
    _, send = _recorder(status=410, reason="Unregistered")
    assert await push.notify(store, OWNER, "og118", "hola", CID, send=send) == 0
    assert store.for_owner(OWNER) == {}


@pytest.mark.asyncio
async def test_a_refusal_that_is_not_about_the_token_keeps_the_device(tmp_path) -> None:
    store = _devices(tmp_path)
    store.register(OWNER, TOKEN, "production")
    _, send = _recorder(status=429, reason="TooManyRequests")
    assert await push.notify(store, OWNER, "og118", "hola", CID, send=send) == 0
    assert TOKEN in store.for_owner(OWNER)


@pytest.mark.asyncio
async def test_without_a_key_nothing_is_sent(tmp_path, monkeypatch) -> None:
    for var in ("OG118_APNS_KEY", "OG118_APNS_KEY_ID", "OG118_APNS_TEAM_ID"):
        monkeypatch.delenv(var, raising=False)
    store = _devices(tmp_path)
    store.register(OWNER, TOKEN, "production")
    assert await push.notify(store, OWNER, "og118", "hola", CID) == 0


def test_a_long_answer_is_cut_to_a_readable_alert() -> None:
    body = push.payload_for("og118", "palabra " * 80, CID)["aps"]["alert"]["body"]
    assert len(body) <= push.BODY_CHARS and body.endswith("…") and "  " not in body


@pytest.mark.asyncio
async def test_the_abandoned_answer_is_stored_and_announced(tmp_path, monkeypatch) -> None:
    conversations = ConversationStore(tmp_path / "conversations")
    devices = _devices(tmp_path)
    devices.register(OWNER, TOKEN, "production")
    told = []

    async def notify(store, owner, title, body, conversation_id, send=None):
        told.append((owner, title, body, conversation_id))
        return 1

    monkeypatch.setattr(deps, "get_conversation_store", lambda: conversations)
    monkeypatch.setattr(deps, "get_device_store", lambda: devices)
    monkeypatch.setattr(push, "notify", notify)
    deliver = chat_routes._abandoned_delivery(OWNER, CID, "¿sigues ahí?")
    await deliver([{"type": "result", "result": {"text": "aquí sigo", "model": "m-1"}}])
    assert conversations.get(OWNER, CID)["messages"][-1]["content"] == "aquí sigo"
    assert told == [(OWNER, "og118", "aquí sigo", CID)]


@pytest.mark.asyncio
async def test_a_push_that_explodes_does_not_lose_the_answer(tmp_path, monkeypatch) -> None:
    conversations = ConversationStore(tmp_path / "conversations")

    async def notify(*args, **kwargs):
        raise RuntimeError("apns is down")

    monkeypatch.setattr(deps, "get_conversation_store", lambda: conversations)
    monkeypatch.setattr(deps, "get_device_store", lambda: _devices(tmp_path))
    monkeypatch.setattr(push, "notify", notify)
    await chat_routes._abandoned_delivery(OWNER, CID, "¿sigues ahí?")([{"type": "result", "result": {"text": "sí"}}])
    assert conversations.get(OWNER, CID)["messages"][-1]["content"] == "sí"
