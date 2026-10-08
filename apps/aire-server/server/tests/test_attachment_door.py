"""The attachment customs (#50): the order of the gates is the point."""

import asyncio

import pytest
from fastapi import HTTPException

from aire import attachment_door as door
from aire.engine import attachment_budget

KEY = {"project_key": "pk", "session_id": "s"}
URL = [{"url": "https://cdn.discordapp.com/a.png?ex=1"}]


@pytest.mark.asyncio
async def test_a_full_session_is_refused_before_anything_is_fetched(monkeypatch):
    async def full(*_):
        return attachment_budget.MAX_SESSION_IMAGES, 0

    async def must_not_prepare(*_):
        raise AssertionError("fetched for a session that could only refuse")
    monkeypatch.setattr(attachment_budget, "held", full)
    monkeypatch.setattr(door, "prepare_images", must_not_prepare)
    with pytest.raises(HTTPException) as exc:
        await door.safe_attachments(URL, None, KEY)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_a_malformed_list_is_refused_before_the_store_is_read(monkeypatch):
    async def must_not_read(*_):
        raise AssertionError("read the store for a malformed request")
    monkeypatch.setattr(attachment_budget, "held", must_not_read)
    with pytest.raises(HTTPException) as exc:
        await door.safe_attachments("not-a-list", None, KEY)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_two_requests_never_fetch_and_decode_at_the_same_time(monkeypatch):
    live = {"now": 0, "peak": 0}

    async def empty(*_):
        return 0, 0

    async def slow_prepare(_raw):
        live["now"] += 1
        live["peak"] = max(live["peak"], live["now"])
        await asyncio.sleep(0.05)
        live["now"] -= 1
        return ({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "x"}},)

    async def no_docs(_raw):
        return ()
    monkeypatch.setattr(door, "_prep_gate", None)
    monkeypatch.setattr(attachment_budget, "held", empty)
    monkeypatch.setattr(door, "prepare_images", slow_prepare)
    monkeypatch.setattr(door, "prepare_documents", no_docs)
    await asyncio.gather(*(door.safe_attachments(URL, None, KEY) for _ in range(3)))
    assert live["peak"] == 1


@pytest.mark.asyncio
async def test_a_text_only_turn_touches_nothing(monkeypatch):
    async def must_not_read(*_):
        raise AssertionError("text-only turn read the store")
    monkeypatch.setattr(attachment_budget, "held", must_not_read)
    assert await door.safe_attachments(None, None, KEY) == ()
