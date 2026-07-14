"""Session reset must close EVERY persona's slot in a channel, not just Insult's.

Found while modularizing runner.py (2026-07-14). A channel hosts one SDK session
per persona — keyed `channel_id` for the default persona and `channel_id:<id>` for
each sibling. `DELETE /v1/session/{channel_id}` closed only the bare key, so a
Vultur/Frugívoro/ALICE session stuck in a poisoned belief (the exact failure the
endpoint exists to cure, 2026-05-19) survived the reset SILENTLY and kept
answering from the bad state.

Positive: every slot of the channel closes. Resistance: another channel's slots
are never touched, and resetting an idle channel is a no-op that doesn't raise.
"""

from __future__ import annotations

import asyncio

import pytest

from persona_runner.engine import session_pool


class _FakeClient:
    def __init__(self) -> None:
        self.closed = False

    async def __aexit__(self, *exc) -> bool:
        self.closed = True
        return False


@pytest.fixture(autouse=True)
def _clean_pool(monkeypatch):
    monkeypatch.setattr(session_pool, "_pool", {})
    monkeypatch.setattr(session_pool, "_pool_last_used", {})
    monkeypatch.setattr(session_pool, "_channel_locks", {})
    monkeypatch.setattr(session_pool, "_pool_models", {})
    yield


def _seed(key: str) -> _FakeClient:
    client = _FakeClient()
    session_pool._pool[key] = client
    session_pool._pool_last_used[key] = 100.0
    session_pool._channel_locks[key] = asyncio.Lock()
    session_pool._pool_models[key] = "m"
    return client


async def test_reset_closes_every_persona_slot_of_the_channel():
    insult = _seed("C1")
    vultur = _seed("C1:vultur")
    frugi = _seed("C1:frugivoro")

    closed = await session_pool.close_channel("C1")

    assert sorted(closed) == ["C1", "C1:frugivoro", "C1:vultur"]
    assert insult.closed and vultur.closed and frugi.closed
    assert session_pool.pool_size() == 0


async def test_reset_never_touches_another_channel():
    """RESISTANCE: a prefix collision must not evict a neighbour's sessions."""
    mine = _seed("C1:vultur")
    other = _seed("C12")  # startswith("C1") but is a DIFFERENT channel
    other_sibling = _seed("C12:vultur")

    closed = await session_pool.close_channel("C1")

    assert closed == ["C1:vultur"]
    assert mine.closed
    assert not other.closed and not other_sibling.closed
    assert session_pool.pool_size() == 2


async def test_reset_of_idle_channel_is_a_noop():
    assert await session_pool.close_channel("nobody-home") == []
    assert session_pool.pool_size() == 0
