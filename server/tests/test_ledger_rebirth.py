"""A reborn client must not inherit the dead one's total (#25's silent leak).

The ledger banks a DELTA against the client's CUMULATIVE `total_cost_usd`. That
is right while one client lives and catastrophic across a rebirth: the newborn
counts from zero, so a remembered predecessor makes `max(0.0, cost - seen)`
clamp real turns to $0 — no ceiling movement, no `aire_spend` row, money gone
with no record. `_retire` (#23) forgot; eviction, the COMMON exit on a two-slot
pool, did not.

The first test pins the arithmetic; the second pins the WIRING, which is where
the bug actually lived — the arithmetic was always correct given a clean `_seen`.
"""

from typing import Any

import pytest

from aire.engine.contract import TurnSpec
from aire.engine.core import Engine
from aire.engine.ledger import Ledger


def test_a_reborn_client_does_not_inherit_the_dead_ones_total() -> None:
    ledger, key = Ledger(), "canary/s1"
    for cumulative in (0.028, 0.030, 0.033):
        ledger.account(key, cumulative)
    assert ledger.spend_usd == pytest.approx(0.033)

    ledger.adopt(key)  # the pool evicted it; a new client is being built

    before = ledger.spend_usd
    ledger.account(key, 0.025)  # the newborn's first turn — real money
    assert ledger.spend_usd - before == pytest.approx(0.025), \
        "the turn banked $0: the dead client's total is still on the books"


class _Stub:
    """Stands in for a live `claude` subprocess: entering it must not spawn one."""

    async def __aenter__(self) -> "_Stub":
        return self

    async def __aexit__(self, *_: Any) -> bool:
        return False


class _NoMemory:
    async def load(self, *_: Any, **__: Any) -> list:
        return []


@pytest.mark.asyncio
async def test_building_a_client_clears_the_ledgers_memory(monkeypatch, tmp_path) -> None:
    """The wiring, not the arithmetic. `adopt` is only correct if it runs on
    EVERY rebirth, so this drives the real `_client_for` — the seam every exit
    from the pool funnels back through — and asserts the books are clean before
    the newborn's first turn is ever counted."""
    import aire.engine.core as core

    monkeypatch.setattr(core, "WORKSPACES", tmp_path)
    monkeypatch.setattr(core, "ClaudeSDKClient", lambda options=None: _Stub())
    monkeypatch.setattr(core, "build_options", lambda *a, **k: None)

    engine = Engine(_NoMemory())
    key = "canary/s1"
    engine.ledger.account(key, 0.033)          # a client lived and spent
    await engine.pool.close_one(key)           # …and was evicted, not retired

    await engine._client_for("canary", "s1", TurnSpec(mode="complete"), slot=None)
    assert key not in engine.ledger._seen, \
        "_client_for built a new client on the previous one's cumulative cost"
