"""OG118-TURN-SURVIVES-1 — a phone that leaves the foreground drops its socket.
The turn used to die with it and the retry paid for a second one."""

from __future__ import annotations

import asyncio

import pytest

import app as app_module
import detached_turn
from conversations import ConversationStore

KEY = ("auth0|owner", "c0ffee00-0000-4000-8000-000000000001")


async def _settle() -> None:
    for _ in range(20):
        await asyncio.sleep(0.01)
        if not detached_turn._LATE_TASKS and KEY not in detached_turn._RUNNING:
            return


def _turn(gate: asyncio.Event, *, fail: bool = False):
    async def events():
        yield {"type": "text", "text": "ho"}
        await gate.wait()
        if fail:
            raise RuntimeError("backend exploded")
        yield {"type": "result", "result": {"text": "hola", "model": "m"}}

    return events()


@pytest.mark.asyncio
async def test_a_turn_heard_to_the_end_is_not_delivered_twice() -> None:
    gate, delivered = asyncio.Event(), []
    gate.set()

    async def deliver(events):
        delivered.append(events)

    seen = [e async for e in detached_turn.surviving(_turn(gate), key=KEY, deliver_late=deliver)]
    await _settle()
    assert [e["type"] for e in seen] == ["text", "result"]
    assert delivered == []


@pytest.mark.asyncio
async def test_an_abandoned_turn_finishes_and_delivers_its_answer() -> None:
    gate, delivered = asyncio.Event(), []

    async def deliver(events):
        delivered.append(events)

    stream = detached_turn.surviving(_turn(gate), key=KEY, deliver_late=deliver)
    assert (await stream.__anext__())["type"] == "text"
    await stream.aclose()
    assert delivered == [], "nothing lands before the runner settles"

    gate.set()
    await _settle()
    assert len(delivered) == 1
    assert delivered[0][-1] == {"type": "result", "result": {"text": "hola", "model": "m"}}


@pytest.mark.asyncio
async def test_an_abandoned_turn_that_failed_delivers_nothing() -> None:
    gate, delivered = asyncio.Event(), []

    async def deliver(events):
        delivered.append(events)

    stream = detached_turn.surviving(_turn(gate, fail=True), key=KEY, deliver_late=deliver)
    await stream.__anext__()
    await stream.aclose()
    gate.set()
    await _settle()
    assert delivered == []


@pytest.mark.asyncio
async def test_an_explicit_stop_ends_the_turn_and_nothing_lands() -> None:
    gate, delivered = asyncio.Event(), []

    async def deliver(events):
        delivered.append(events)

    stream = detached_turn.surviving(_turn(gate), key=KEY, deliver_late=deliver)
    await stream.__anext__()
    await stream.aclose()
    assert detached_turn.cancel(KEY) is True
    gate.set()
    await _settle()
    assert delivered == []
    assert detached_turn.cancel(KEY) is False, "a turn that is gone cannot be cancelled again"


@pytest.mark.asyncio
async def test_the_abandoned_answer_lands_in_the_record(tmp_path, monkeypatch) -> None:
    store = ConversationStore(tmp_path / "conversations")
    monkeypatch.setattr(app_module, "get_conversation_store", lambda: store)
    deliver = app_module._abandoned_delivery(KEY[0], KEY[1], "¿sigues ahí?")
    await deliver([{"type": "text", "text": "aquí"}, {"type": "result", "result": {"text": "aquí sigo", "model": "m-1"}}])
    messages = store.get(KEY[0], KEY[1])["messages"]
    assert [(m["role"], m["content"]) for m in messages] == [("user", "¿sigues ahí?"), ("assistant", "aquí sigo")]
    assert messages[-1]["model"] == "m-1"


@pytest.mark.asyncio
async def test_a_dropped_connection_under_the_heartbeat_still_delivers() -> None:
    """The route wraps the turn in the heartbeat and Starlette cancels the
    response task when the socket drops: that is the path a phone takes."""
    gate, delivered, heard = asyncio.Event(), [], []

    async def deliver(events):
        delivered.append(events)

    async def respond() -> None:
        turn = detached_turn.surviving(_turn(gate), key=KEY, deliver_late=deliver)
        async for event in app_module._with_heartbeat(turn, interval=0.05):
            heard.append(event["type"])

    response = asyncio.create_task(respond())
    await asyncio.sleep(0.12)
    response.cancel()
    with pytest.raises(asyncio.CancelledError):
        await response
    assert "text" in heard and "result" not in heard

    gate.set()
    await _settle()
    assert len(delivered) == 1
