"""Session-pool cap — LRU eviction at MAX_POOL_SESSIONS.

Each pool slot is a live Node subprocess. OG118-CONTINUITY keys slots by
client-minted conversation UUIDs, so an authed caller can request unlimited
distinct channels; without a ceiling that is a subprocess bomb on the
1-CPU/2Gi runner (the 2026-05-22 judge pile-up OOM'd it). The cap closes the
least-recently-used slot before opening a new one. Positive + resistance
cases per .claude/rules/robustness.md.
"""

from __future__ import annotations

import asyncio

import claude_agent_sdk
import pytest

from persona_runner import runner


class _FakeClient:
    def __init__(self, *a, **k) -> None:
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a) -> bool:
        self.closed = True
        return False


@pytest.fixture(autouse=True)
def _clean_pool(monkeypatch):
    """Isolated pool state + fake SDK client per test — no real subprocesses."""
    monkeypatch.setattr(runner, "_pool", {})
    monkeypatch.setattr(runner, "_pool_last_used", {})
    monkeypatch.setattr(runner, "_channel_locks", {})
    monkeypatch.setattr(runner, "_pool_models", {})
    monkeypatch.setattr(claude_agent_sdk, "ClaudeSDKClient", _FakeClient)
    yield


def _seed(key: str, last_used: float) -> _FakeClient:
    client = _FakeClient()
    runner._pool[key] = client
    runner._pool_last_used[key] = last_used
    runner._channel_locks[key] = asyncio.Lock()
    runner._pool_models[key] = "m"
    return client


async def test_at_cap_evicts_the_lru_slot(monkeypatch):
    monkeypatch.setattr(runner, "MAX_POOL_SESSIONS", 2)
    oldest = _seed("conv-old", 100.0)
    newer = _seed("conv-new", 200.0)

    await runner._get_or_create_client("conv-incoming")

    assert "conv-incoming" in runner._pool
    assert oldest.closed and "conv-old" not in runner._pool
    assert not newer.closed and "conv-new" in runner._pool
    assert len(runner._pool) <= 2


async def test_under_cap_evicts_nothing(monkeypatch):
    # RESISTANCE: normal operation below the ceiling never closes a session.
    monkeypatch.setattr(runner, "MAX_POOL_SESSIONS", 8)
    kept = _seed("conv-a", 100.0)

    await runner._get_or_create_client("conv-b")

    assert not kept.closed
    assert set(runner._pool) == {"conv-a", "conv-b"}


async def test_existing_slot_reuse_never_evicts(monkeypatch):
    # RESISTANCE: a turn on an ALREADY-open slot at the cap must not evict —
    # only slot CREATION pays the eviction.
    monkeypatch.setattr(runner, "MAX_POOL_SESSIONS", 2)
    a = _seed("conv-a", 100.0)
    b = _seed("conv-b", 200.0)

    got = await runner._get_or_create_client("conv-a")

    assert got is a
    assert not a.closed and not b.closed
    assert set(runner._pool) == {"conv-a", "conv-b"}


async def test_eviction_close_failure_still_frees_the_slot(monkeypatch):
    # RESISTANCE: a broken client's __aexit__ raising must not wedge creation.
    monkeypatch.setattr(runner, "MAX_POOL_SESSIONS", 1)

    class _Broken(_FakeClient):
        async def __aexit__(self, *a) -> bool:
            raise RuntimeError("subprocess already dead")

    runner._pool["conv-broken"] = _Broken()
    runner._pool_last_used["conv-broken"] = 100.0

    await runner._get_or_create_client("conv-next")

    assert "conv-broken" not in runner._pool
    assert "conv-next" in runner._pool
