"""Every dollar the daemon spends, in a row that outlives the process.

The engine's ``Ledger`` counts spend in RAM over the process lifetime, born at
``0.0`` and reset on every deploy (14× on 2026-08-23) — a ceiling that counted
from zero several times a day while ``arming.py`` reported it armed. This is the
ledger it never was: an append-only row per paid turn in the owned Postgres, so
"what did AIRE spend this month" survives a restart, a re-provision, and the box.

**It does not refuse anything** (Bernard, 2026-08-23): a hard monthly cap can
take og118 and Fénix down at 3am over an accounting threshold, and the
per-process backstop already stops a runaway session. The month is REPORTED on
``/health``'s gated half where costwatch reads it and goes red; the refusal
stays put. The read feeds a watchdog's threshold, which is the [[write-only-daemon]]
criterion, not the exception list.
"""

from __future__ import annotations

import asyncio
import os

from . import db

# Accounting runs INSIDE the turn's result seam, holding that session's lock and
# one of the pool's two RAM slots. So a slow database does not merely delay a
# row: it stalls the SSE stream after the answer and starves the pool, until a
# third turn waits out SLOT_WAIT_S and gets a 503. The docstring above promises
# the accounting never costs the caller the answer; this bound is what makes the
# promise true. It wraps the WHOLE call because a statement timeout governs a
# query and not the wait for a free connection, which is the half that hangs.
BANK_TIMEOUT_S = float(os.environ.get("AIRE_SPEND_TIMEOUT_S", "5"))
STATEMENT_TIMEOUT_MS = int(BANK_TIMEOUT_S * 1000)

DDL = (
    "CREATE TABLE IF NOT EXISTS aire_spend ("
    " seq bigserial PRIMARY KEY,"
    " at timestamptz NOT NULL DEFAULT now(),"
    " door text NOT NULL,"
    " project text,"
    " session text,"
    " holder text,"
    " usd double precision NOT NULL,"
    " metered boolean NOT NULL DEFAULT true,"
    " cache_read bigint, cache_creation bigint, input_tokens bigint)"
)
# `metered` (2026-08-26): whether the row's dollars are REAL. An OAuth turn's
# `total_cost_usd` is nominal — the Max subscription already paid — and summing
# it into `month_to_date` put costwatch permanently red over money nobody was
# billed. Default true: an unlabeled dollar counts as real (a card alarm).
# The token columns (2026-09-15) record cache efficiency: cache_read ≫
# cache_creation means the pool rides warm cache; the inverse burns the weekly
# pool re-caching cold. Nullable — old rows and the gateway path carry none.
MIGRATE = (
    "ALTER TABLE aire_spend ADD COLUMN IF NOT EXISTS metered boolean NOT NULL DEFAULT true",
    "ALTER TABLE aire_spend ADD COLUMN IF NOT EXISTS cache_read bigint",
    "ALTER TABLE aire_spend ADD COLUMN IF NOT EXISTS cache_creation bigint",
    "ALTER TABLE aire_spend ADD COLUMN IF NOT EXISTS input_tokens bigint",
)
INDEX = "CREATE INDEX IF NOT EXISTS aire_spend_at ON aire_spend (at)"

_ready = False
_lock = asyncio.Lock()


async def ensure() -> None:
    """The table, committed and VISIBLE to other connections, before anything
    inserts. Called at startup (`server.lifespan`) and by every writer first.

    The lazy version ran the DDL on the CALLER's connection, which `db.acquire`
    wraps in a transaction: `_ready` flipped while the CREATE was uncommitted, so
    concurrent first turns inserted against a table they couldn't see (8 turns
    measured: three lost their row to `UndefinedTableError`, after a deploy). So
    the DDL takes its OWN autocommit connection and `_ready` flips only once it is
    committed; the lock holds no connection, so callers cannot deadlock the pool."""
    global _ready
    if _ready or not db.dsn():
        return
    async with _lock:
        if _ready:
            return
        async with db.acquire() as conn:
            await conn.execute(DDL)
            for stmt in MIGRATE:
                await conn.execute(stmt)
            await conn.execute(INDEX)
        _ready = True


async def bank(door: str, project: str | None, session: str | None,
               holder: str | None, usd: float, metered: bool = True,
               tokens: dict[str, int] | None = None) -> None:
    """One paid turn, appended. Never raises into a turn: a dead database must
    cost the accounting, never the answer the caller is waiting for — the same
    law the gateway mirror runs under. It is LOUD, because a turn that spent
    money and left no row is the exact silence this module exists to end.
    `tokens` carries the cache breakdown when the caller has it (engine turns);
    the gateway path passes none and the columns stay null."""
    if usd <= 0 or not db.dsn():
        return
    try:
        await asyncio.wait_for(_insert(door, project, session, holder, usd, metered, tokens),
                               timeout=BANK_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 — accounting never kills a turn
        print(f"SPEND append failed (${usd:.4f} on {door}): "
              f"{type(exc).__name__}: {exc}", flush=True)


async def _insert(door: str, project: str | None, session: str | None, holder: str | None,
                  usd: float, metered: bool, tokens: dict[str, int] | None) -> None:
    await ensure()
    t = tokens or {}
    async with db.acquire(STATEMENT_TIMEOUT_MS) as conn:
        await conn.execute(
            "INSERT INTO aire_spend (door, project, session, holder, usd, metered,"
            " cache_read, cache_creation, input_tokens)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            door, project, session, holder, usd, metered,
            t.get("cache_read"), t.get("cache_creation"), t.get("input_tokens"))


async def month_to_date() -> float:
    """What this daemon has spent since the first of the month, across every
    process that ran in it. Returns -1.0 when the figure is unavailable, which
    a caller must not confuse with zero — an unreadable ledger is not a cheap
    month, and reporting 0.0 for it would be the fake-green in miniature."""
    if not db.dsn():
        return -1.0
    try:
        return await asyncio.wait_for(_sum_month(), timeout=BANK_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001
        print(f"SPEND month read failed: {type(exc).__name__}: {exc}", flush=True)
        return -1.0


async def _sum_month() -> float:
    """The month's total, bounded like the insert: `/health` is what a watchdog
    polls, and a health endpoint that HANGS is worse than one that answers
    degraded — the watchdog waits instead of alarming."""
    await ensure()
    async with db.acquire(STATEMENT_TIMEOUT_MS) as conn:
        total = await conn.fetchval(
            "SELECT coalesce(sum(usd), 0) FROM aire_spend"
            " WHERE metered AND at >= date_trunc('month', now())")
    return round(float(total), 4)
