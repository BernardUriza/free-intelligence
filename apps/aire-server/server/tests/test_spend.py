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


@pytest.mark.asyncio
async def test_nominal_spend_is_recorded_but_never_alarms() -> None:
    """An OAuth turn's dollars are nominal — the Max subscription already paid.
    Its row survives (the usage record), but the figure costwatch alarms on
    counts metered dollars only: summing nominal spend held the alarm
    permanently red over money nobody was billed (2026-08-26)."""
    await _clean()
    await spend.bank("engine", "canary", "s1", None, 0.50, metered=False)
    await spend.bank("engine", "canary", "s1", None, 0.05)

    assert await spend.month_to_date() == pytest.approx(0.05)

    conn = await asyncpg.connect(DSN, timeout=10)
    rows = await conn.fetch("SELECT usd, metered FROM aire_spend ORDER BY seq")
    await conn.close()
    assert [(float(r["usd"]), r["metered"]) for r in rows] == [(0.50, False), (0.05, True)], \
        "the nominal row must survive — only the alarm's sum filters it"


@pytest.mark.asyncio
async def test_the_metered_column_migrates_onto_a_pre_existing_table() -> None:
    """The prod table predates the column: `ensure` must ALTER it in, and the
    old rows must default to metered (an unlabeled dollar counts as real)."""
    spend._ready = False
    conn = await asyncpg.connect(DSN, timeout=10)
    await conn.execute("DROP TABLE IF EXISTS aire_spend")
    await conn.execute(
        "CREATE TABLE aire_spend ("
        " seq bigserial PRIMARY KEY, at timestamptz NOT NULL DEFAULT now(),"
        " door text NOT NULL, project text, session text, holder text,"
        " usd double precision NOT NULL)")
    await conn.execute(
        "INSERT INTO aire_spend (door, usd) VALUES ('engine', 0.09)")
    await conn.close()

    await spend.bank("engine", "canary", "s1", None, 0.01, metered=False)

    assert await spend.month_to_date() == pytest.approx(0.09), \
        "the pre-migration row lost its default-metered dollars"


@pytest.mark.asyncio
async def test_a_turn_persists_its_cache_breakdown() -> None:
    """The efficiency columns (2026-09-15): a banked turn stores cache_read /
    cache_creation / input_tokens so the cache ratio is queryable over time."""
    await _clean()
    await spend.bank("engine", "canary", "s1", None, 0.01,
                     tokens={"cache_read": 90000, "cache_creation": 1200, "input_tokens": 40})
    conn = await asyncpg.connect(DSN, timeout=10)
    row = await conn.fetchrow(
        "SELECT cache_read, cache_creation, input_tokens FROM aire_spend LIMIT 1")
    await conn.close()
    assert (row["cache_read"], row["cache_creation"], row["input_tokens"]) == (90000, 1200, 40)


@pytest.mark.asyncio
async def test_the_token_columns_migrate_onto_a_pre_existing_table() -> None:
    """The prod table predates the token columns: `ensure` ALTERs them in and a
    turn with no breakdown leaves them null, never a fake zero."""
    spend._ready = False
    conn = await asyncpg.connect(DSN, timeout=10)
    await conn.execute("DROP TABLE IF EXISTS aire_spend")
    await conn.execute(
        "CREATE TABLE aire_spend ("
        " seq bigserial PRIMARY KEY, at timestamptz NOT NULL DEFAULT now(),"
        " door text NOT NULL, project text, session text, holder text,"
        " usd double precision NOT NULL, metered boolean NOT NULL DEFAULT true)")
    await conn.close()

    await spend.bank("gateway", None, None, "someone", 0.02)  # no tokens

    conn = await asyncpg.connect(DSN, timeout=10)
    row = await conn.fetchrow("SELECT cache_read FROM aire_spend LIMIT 1")
    await conn.close()
    assert row["cache_read"] is None, "a turn with no breakdown leaves the column null"
