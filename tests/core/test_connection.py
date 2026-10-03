"""Tests for ConnectionManager boot instrumentation, idempotency, and
background embedding prewarm.

Registered after the 2026-06-13 boot-hang incident: the boot deadlocked inside
connect() with ZERO telemetry between `debug_server_started` and the success
line, making the root cause unprovable. These tests lock in the boundary
telemetry (no blind spot) and the fail-fast-friendly design (idempotent pool,
prewarm off the critical path)."""

from __future__ import annotations

import asyncio

import pytest
import structlog

from persona_core.memory import connection as conn_mod
from persona_core.memory.connection import ConnectionManager


class _FakeConn:
    async def execute(self, *_a, **_k):
        return None

    async def fetchval(self, *_a, **_k):
        return 1


class _FakeAcquire:
    async def __aenter__(self):
        return _FakeConn()

    async def __aexit__(self, *_a):
        return False


class _FakePool:
    def __init__(self):
        self.closed = False

    def acquire(self):
        return _FakeAcquire()

    async def close(self):
        self.closed = True


@pytest.fixture
def fake_pool(monkeypatch):
    """Patch asyncpg.create_pool to return a fake pool, and stub the embedding
    model so the background prewarm never touches HuggingFace."""
    created = {"count": 0}

    async def _fake_create_pool(*_a, **_k):
        created["count"] += 1
        return _FakePool()

    monkeypatch.setattr(conn_mod.asyncpg, "create_pool", _fake_create_pool)

    class _FakeModel:
        def embed(self, _text):
            return [0.0]

    import persona_core.vectors as vectors_mod

    monkeypatch.setattr(vectors_mod, "get_embedding_model", lambda: _FakeModel())
    return created


@pytest.mark.asyncio
async def test_connect_emits_boundary_telemetry(fake_pool):
    """No blind spot: every step of connect() leaves a structured log so a
    stall inside any step is diagnosable from telemetry alone."""
    mgr = ConnectionManager("postgresql://x/y")
    with structlog.testing.capture_logs() as logs:
        await mgr.connect()
    events = [e["event"] for e in logs]
    # The exact boundary sequence the 2026-06-13 incident lacked.
    for expected in (
        "pg_pool_creating",
        "pg_pool_created",
        "pg_schema_applying",
        "pg_schema_applied",
        "memory_connected_pg",
    ):
        assert expected in events, f"missing boundary telemetry: {expected}"
    assert events.index("pg_pool_creating") < events.index("pg_pool_created")
    assert events.index("pg_pool_created") < events.index("memory_connected_pg")
    if mgr._prewarm_task:
        mgr._prewarm_task.cancel()


@pytest.mark.asyncio
async def test_connect_idempotent_does_not_rebuild_pool(fake_pool):
    """A second connect() (gateway reconnect) must NOT create a second pool —
    that orphans the first and leaks connections."""
    mgr = ConnectionManager("postgresql://x/y")
    await mgr.connect()
    assert fake_pool["count"] == 1
    with structlog.testing.capture_logs() as logs:
        await mgr.connect()
    assert fake_pool["count"] == 1, "second connect rebuilt the pool"
    assert any(e["event"] == "pg_connect_skipped_already_connected" for e in logs)
    if mgr._prewarm_task:
        mgr._prewarm_task.cancel()


@pytest.mark.asyncio
async def test_prewarm_runs_off_critical_path(fake_pool):
    """The embedding prewarm must be a background task, not awaited inside
    connect() — a slow HF download must never gate bot_ready."""
    mgr = ConnectionManager("postgresql://x/y")
    await mgr.connect()
    # connect() returned; the prewarm was scheduled as a task, not awaited.
    assert isinstance(mgr._prewarm_task, asyncio.Task)
    # Let the background task complete and confirm it logged the warm event.
    with structlog.testing.capture_logs() as logs:
        await mgr._prewarm_task
    events = [e["event"] for e in logs]
    assert "embedding_model_prewarmed" in events or "embedding_prewarm_failed" in events


@pytest.mark.asyncio
async def test_prewarm_failure_is_non_fatal(fake_pool, monkeypatch):
    """If the embedding model blows up, connect() still succeeds — the prewarm
    is best-effort, the lazy path covers the first turn."""
    import persona_core.vectors as vectors_mod

    def _boom():
        raise RuntimeError("HF unreachable")

    monkeypatch.setattr(vectors_mod, "get_embedding_model", _boom)
    mgr = ConnectionManager("postgresql://x/y")
    await mgr.connect()  # must not raise
    assert mgr.pool is not None
    assert mgr._prewarm_task is not None
    with structlog.testing.capture_logs() as logs:
        await mgr._prewarm_task
    assert any(e["event"] == "embedding_prewarm_failed" for e in logs)


# --- the runner awaits the warmup connect() starts (2026-09-28) --------------


@pytest.mark.asyncio
async def test_wait_embeddings_prewarmed_is_false_when_connect_started_nothing():
    manager = ConnectionManager("postgresql://x")
    assert await manager.wait_embeddings_prewarmed() is False


@pytest.mark.asyncio
async def test_wait_embeddings_prewarmed_awaits_the_warmup_task():
    manager = ConnectionManager("postgresql://x")
    done: list[str] = []

    async def warmup() -> None:
        await asyncio.sleep(0)
        done.append("loaded")

    manager._prewarm_task = asyncio.create_task(warmup())
    assert await manager.wait_embeddings_prewarmed() is True
    assert done == ["loaded"], "the caller must not return before the model is resident"
