"""The shared asyncpg pool in `mcp_tools.shared` — the hot path's connection.

The MCP tools open a one-shot connection per call and that is fine: the model
reaches for memory rarely. The AIRE route's in-band fact pre-fetch is not that —
it fires on EVERY turn, so a connect + TLS handshake + close per turn is latency
nobody chose to spend. What is asserted here is that the pool is really a pool
(built once, connections RELEASED not closed) and that its failure contract is
the repo's law: a DB fault yields None, never an exception.
"""

from __future__ import annotations

import asyncio

import pytest

from persona_runner.mcp_tools import shared


class _FakePool:
    def __init__(self):
        self.acquired = 0
        self.released = 0
        self.closed = False

    async def acquire(self):
        self.acquired += 1
        return object()

    async def release(self, _conn):
        self.released += 1

    async def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def _no_leftover_pool():
    shared._pool = None
    shared._pool_lock = None
    yield
    shared._pool = None
    shared._pool_lock = None


@pytest.fixture
def _fake_pg(monkeypatch):
    """asyncpg replaced by a pool that counts how often it was BUILT."""
    built: list[_FakePool] = []

    async def _create_pool(*_a, **_k):
        pool = _FakePool()
        built.append(pool)
        return pool

    monkeypatch.setenv("POSTGRES_URL", "postgresql://fake/db")
    monkeypatch.setattr(shared.asyncpg, "create_pool", _create_pool)
    return built


@pytest.mark.asyncio
async def test_many_acquires_build_exactly_one_pool(_fake_pg):
    """THE COST: without this the hot path pays a fresh Postgres connection on
    every single turn."""
    for _ in range(5):
        async with shared.acquire() as conn:
            assert conn is not None

    assert len(_fake_pg) == 1
    assert _fake_pg[0].acquired == 5


@pytest.mark.asyncio
async def test_a_pooled_connection_is_released_not_closed(_fake_pg):
    """Closing a pooled connection is what turns a pool back into connect-per-call."""
    async with shared.acquire():
        pass

    assert _fake_pg[0].released == 1


@pytest.mark.asyncio
async def test_concurrent_first_callers_do_not_build_two_pools(_fake_pg):
    """RESISTANCE: the lazy build races too — two turns arriving together on a
    cold process must not each mint a pool (one of them would then leak)."""

    async def _use():
        async with shared.acquire():
            await asyncio.sleep(0)

    await asyncio.gather(*[_use() for _ in range(4)])

    assert len(_fake_pg) == 1


@pytest.mark.asyncio
async def test_an_unconfigured_postgres_yields_none_not_an_exception(monkeypatch):
    """A DB fault never kills a turn (repo law) — the caller gets None."""
    monkeypatch.delenv("POSTGRES_URL", raising=False)

    async with shared.acquire() as conn:
        assert conn is None


@pytest.mark.asyncio
async def test_a_pool_that_refuses_to_build_yields_none(monkeypatch):
    """Same contract when Postgres is configured but unreachable."""

    async def _boom(*_a, **_k):
        raise OSError("pg unreachable")

    monkeypatch.setenv("POSTGRES_URL", "postgresql://fake/db")
    monkeypatch.setattr(shared.asyncpg, "create_pool", _boom)

    async with shared.acquire() as conn:
        assert conn is None


@pytest.mark.asyncio
async def test_close_pool_closes_and_is_idempotent(_fake_pg):
    """Shutdown closes it; calling again on a closed/never-built pool is a no-op."""
    async with shared.acquire():
        pass

    await shared.close_pool()
    await shared.close_pool()

    assert _fake_pg[0].closed
