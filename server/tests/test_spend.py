"""The month survives what the process does not (#25).

The engine's RAM ledger is born at 0.0 on every start, and the daemon restarts
on every deploy — so the claim under test is not "a row is inserted", it is
"the figure a watchdog alarms on is indifferent to the restart". These run
against a real Postgres for the same reason the blob sweep does: the bug this
prevents lives in SQL (a window that drifts, a total that resets), not in a mock.
"""

import asyncio
import os

import asyncpg
import pytest

from aire import db, spend

DSN = os.environ.get("AIRE_DATABASE_URL", "postgresql://bernardurizaorozco@127.0.0.1:5432/aire")


async def _clean() -> None:
    spend._ready = False
    conn = await asyncpg.connect(DSN, timeout=10)
    await conn.execute("DROP TABLE IF EXISTS aire_spend")
    await conn.close()


@pytest.mark.asyncio
async def test_the_month_outlives_the_process() -> None:
    """Two 'processes' bank into the same month. A ledger that reset the way the
    RAM counter does would answer 0.02 to the second reader; the point of the
    table is that it answers the sum."""
    await _clean()
    await spend.bank("engine", "canary", "s1", None, 0.02)
    spend._ready = False   # a restart: the module forgets, the table does not
    await db.close()
    await spend.bank("gateway", None, None, "someone", 0.03)
    assert await spend.month_to_date() == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_a_free_turn_leaves_no_row() -> None:
    """A pass-through turn costs AIRE nothing and must not inflate the month —
    and a zero row would also make the ledger's own count useless as a turn count."""
    await _clean()
    await spend.bank("gateway", None, None, "passthrough", 0.0)
    assert await spend.month_to_date() == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_last_month_is_not_this_month() -> None:
    """The window is the calendar month, so an old row must not be counted. A
    `sum(usd)` with a drifting or missing WHERE would pass every other test here."""
    await _clean()
    await spend.bank("engine", "canary", "s1", None, 0.07)
    conn = await asyncpg.connect(DSN, timeout=10)
    await conn.execute("INSERT INTO aire_spend (at, door, usd)"
                       " VALUES (now() - interval '45 days', 'engine', 9.99)")
    await conn.close()
    assert await spend.month_to_date() == pytest.approx(0.07)


@pytest.mark.asyncio
async def test_an_unreadable_ledger_is_not_a_cheap_month(monkeypatch) -> None:
    """-1.0, never 0.0. A watchdog that reads zero from a broken ledger reports
    a quiet month for a daemon that may be spending freely — the fake-green this
    whole module exists to end."""
    monkeypatch.setattr(db, "dsn", lambda: "")
    assert await spend.month_to_date() == -1.0


@pytest.mark.asyncio
async def test_banking_never_raises_into_a_turn(monkeypatch) -> None:
    """Accounting must cost the accounting, never the answer the caller waits
    for — the gateway mirror's law, applied to money."""
    class Dead:
        async def __aenter__(self):
            raise RuntimeError("database is gone")

        async def __aexit__(self, *_):
            return False

    monkeypatch.setattr(db, "acquire", lambda *a, **k: Dead())
    await spend.bank("engine", "canary", "s1", None, 0.5)


@pytest.mark.asyncio
async def test_concurrent_first_turns_all_leave_a_row() -> None:
    """The DDL race: several first turns arriving together on a box whose table
    does not exist yet. `CREATE TABLE IF NOT EXISTS` is not a mutex — two of them
    can collide on the catalog, and `bank` swallows the error and prints, so the
    cost is a lost row in the minutes right after a deploy. `ensure()` at startup
    removes the race and the lock covers whoever still gets here first."""
    await _clean()
    await asyncio.gather(*(spend.bank("engine", "canary", f"s{i}", None, 0.01)
                           for i in range(8)))
    assert await spend.month_to_date() == pytest.approx(0.08)


@pytest.mark.asyncio
async def test_ensure_is_what_startup_calls() -> None:
    """The door opens with the table already there, so no paid turn is the one
    that discovers it is missing."""
    await _clean()
    await spend.ensure()
    assert await spend.month_to_date() == pytest.approx(0.0)
