"""Every dollar the daemon spends, in a row that outlives the process.

The engine's ``Ledger`` counts spend in RAM, over the process lifetime, and
that was the whole ceiling: ``AIRE_MAX_SPEND_USD`` refuses turns once the
counter passes it, and the counter is born at ``0.0``. The daemon restarts on
every deploy — fourteen times on 2026-08-23 alone — so a ceiling described as
cumulative was in practice counting from zero several times a day, while
``arming.py`` reported ``spend_backstop: armed`` and costwatch approved. A
number that resets under the operator's feet is not a ceiling; it is a
speed bump that reads like one.

This is the ledger the counter never was: an append-only row per paid turn,
in the same owned Postgres as the transcript, so "what did AIRE spend this
month" has an answer that survives a restart, a re-provision, and the box
itself ([[log-is-the-truth]]).

**It does not refuse anything.** Bernard's call, 2026-08-23: a hard monthly
cap can take og118 and Fénix down at 3am over an accounting threshold, and
the per-process backstop already stops a single runaway session. So the month
is REPORTED — on ``/health``'s gated half, where costwatch reads it and goes
red — and the refusal stays where it is. An alarm that wakes a human beats a
gate that silences a fleet.

The read here is not a waiter read: nobody renders these rows. It feeds a
watchdog's threshold — a check that arms an alarm, which is the criterion in
[[write-only-daemon]], not the exception list.
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
    " usd double precision NOT NULL)"
)
INDEX = "CREATE INDEX IF NOT EXISTS aire_spend_at ON aire_spend (at)"

_ready = False
_lock = asyncio.Lock()


async def ensure() -> None:
    """The table, committed and VISIBLE to other connections, before anything
    inserts. Called at startup (`server.lifespan`) the way `tokens.load()` is,
    and by every writer as its first step.

    Two things had to be true at once and only one was. The lazy version created
    the table on the first paid turn, so two concurrent first turns raced the
    DDL. Worse — and this is the part that only a concurrency test finds — it ran
    that DDL on the CALLER's connection, which `db.acquire(statement_timeout_ms)`
    wraps in an explicit transaction: the flag flipped to ready while the CREATE
    was still uncommitted, so every other coroutine skipped the DDL and inserted
    against a table its own connection could not see. Measured on 8 concurrent
    first turns: **three lost their row** to `UndefinedTableError`, swallowed and
    printed, on exactly the turns that follow a deploy.

    So the DDL takes its OWN connection with no surrounding transaction (asyncpg
    autocommits a lone statement), and `_ready` flips only after it is committed.
    The lock is taken with no connection in hand, so callers cannot deadlock the
    pool waiting for each other."""
    global _ready
    if _ready or not db.dsn():
        return
    async with _lock:
        if _ready:
            return
        async with db.acquire() as conn:
            await conn.execute(DDL)
            await conn.execute(INDEX)
        _ready = True


async def bank(door: str, project: str | None, session: str | None,
               holder: str | None, usd: float) -> None:
    """One paid turn, appended. Never raises into a turn: a dead database must
    cost the accounting, never the answer the caller is waiting for — the same
    law the gateway mirror runs under. It is LOUD, because a turn that spent
    money and left no row is the exact silence this module exists to end."""
    if usd <= 0 or not db.dsn():
        return
    try:
        await asyncio.wait_for(_insert(door, project, session, holder, usd),
                               timeout=BANK_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 — accounting never kills a turn
        print(f"SPEND append failed (${usd:.4f} on {door}): "
              f"{type(exc).__name__}: {exc}", flush=True)


async def _insert(door: str, project: str | None, session: str | None,
                  holder: str | None, usd: float) -> None:
    await ensure()
    async with db.acquire(STATEMENT_TIMEOUT_MS) as conn:
        await conn.execute(
            "INSERT INTO aire_spend (door, project, session, holder, usd)"
            " VALUES ($1, $2, $3, $4, $5)", door, project, session, holder, usd)


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
            " WHERE at >= date_trunc('month', now())")
    return round(float(total), 4)
