"""#38: a turn that asks for a different shape must not be answered by the
client the session was born with.

The SDK takes mode/tools/model at CONSTRUCTION, so a pooled client froze the
first turn's shape for its whole idle life (~55 min) and every later request was
accepted and dropped — no error, no warning. Measured live 2026-08-22 on the
gate: one session, haiku then sonnet, haiku both times. These tests fail if that
silence ever comes back.
"""

import asyncio

import pytest

from aire.engine.contract import TurnSpec
from aire.engine.core import Engine

HAIKU = TurnSpec(mode="complete", model="claude-haiku-4-5-20251001")
SONNET = TurnSpec(mode="complete", model="claude-sonnet-4-6")


class FakeClient:
    def __init__(self) -> None:
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc) -> None:
        self.closed = True


@pytest.fixture
def engine(monkeypatch, tmp_path):
    monkeypatch.setattr("aire.engine.core.WORKSPACES", tmp_path)
    monkeypatch.setattr("aire.engine.core.SDKClient", lambda provider="claude", *, options=None: FakeClient())
    monkeypatch.setattr("aire.engine.core.build_options", lambda *a, **k: object())
    eng = Engine(session_store=None)
    monkeypatch.setattr(eng, "has_session", _false)
    return eng


async def _false(*_a, **_k) -> bool:
    return False


async def _client(engine, spec):
    await engine._rebind("p", "s", spec)
    client, _ = await engine._client_for("p", "s", spec)
    return client


@pytest.mark.asyncio
async def test_a_turn_asking_another_model_gets_a_new_client(engine):
    first = await _client(engine, HAIKU)
    second = await _client(engine, SONNET)
    assert second is not first, "the sonnet turn was served by the haiku client — #38 is back"
    assert first.closed, "the stale client was dropped from the pool but never closed"
    assert engine.spec_of["p/s"] == SONNET


@pytest.mark.asyncio
async def test_the_same_shape_keeps_its_warm_client(engine):
    """The whole point of the pool: an unchanged shape must NOT pay a rebirth."""
    first = await _client(engine, HAIKU)
    assert await _client(engine, HAIKU) is first
    assert not first.closed


@pytest.mark.asyncio
async def test_mode_and_tools_count_as_a_different_shape(engine):
    """model is what was measured, but the SDK binds all three the same way."""
    first = await _client(engine, TurnSpec(mode="complete"))
    assert await _client(engine, TurnSpec(mode="agent")) is not first
    with_tools = await _client(engine, TurnSpec(mode="agent", tools=("persona",)))
    assert with_tools is not first


@pytest.mark.asyncio
async def test_a_client_is_never_closed_under_an_in_flight_turn(engine):
    """The hazard the wait exists for: closing a client whose turn is mid-drain
    would tear a live stream. _rebind must block until the lock is free."""
    first = await _client(engine, HAIKU)
    _, lock = await engine._client_for("p", "s", HAIKU)
    await lock.acquire()
    rebinding = asyncio.create_task(engine._rebind("p", "s", SONNET))
    await asyncio.sleep(0.05)
    assert not rebinding.done(), "_rebind closed the client while a turn held the lock"
    assert not first.closed
    lock.release()
    await rebinding
    assert first.closed


@pytest.mark.asyncio
async def test_the_real_turn_path_rebinds_before_it_takes_a_client(engine, monkeypatch):
    """The wiring, not just the helper.

    Written after the first version of these tests passed with the call REMOVED
    from turn.py — they exercised `_rebind` directly, so they proved the mechanism
    and not the fix. A turn that never calls it is the bug, whatever `_rebind`
    itself does.
    """
    from aire.engine import turn as turn_mod

    order: list[str] = []
    real_rebind, real_client_for = engine._rebind, engine._client_for

    async def spy_rebind(*a, **k):
        order.append("rebind")
        return await real_rebind(*a, **k)

    async def spy_client_for(*a, **k):
        order.append("client_for")
        return await real_client_for(*a, **k)

    monkeypatch.setattr(engine, "_rebind", spy_rebind)
    monkeypatch.setattr(engine, "_client_for", spy_client_for)
    monkeypatch.setattr(turn_mod, "send_turn", _noop)
    monkeypatch.setattr(turn_mod, "drain", _empty_stream)
    slot = type("Slot", (), {"name": "oauth-primary", "env": {}})()

    async for _ in turn_mod._attempt(engine, "p", "s", "hola", HAIKU, (), slot):
        pass
    assert order == ["rebind", "client_for"], f"turn path did not rebind first: {order}"


async def _noop(*_a, **_k) -> None:
    return None


async def _empty_stream(*_a, **_k):
    for event in ():
        yield event


@pytest.mark.asyncio
async def test_dropping_forgets_every_piece_of_the_client_state(engine):
    """One way out of the pool, so a retire and a rebind cannot forget half."""
    await _client(engine, HAIKU)
    engine.slot_of["p/s"] = "oauth-primary"
    engine.ledger.account("p/s", 0.42)
    await engine._retire("p", "s")
    assert "p/s" not in engine.spec_of
    assert "p/s" not in engine.slot_of
    assert "p/s" not in engine.ledger._seen
    assert "p/s" not in engine.pool.clients
