"""AIRE — the broom. The pillar nobody else builds.

The SDK's own docstring delegates retention to the adapter, in writing: *"The SDK
never deletes from your store… Retention is the adapter's responsibility."* AIRE
calls that the cleanest gap in the field — so AIRE does not get to leave its OWN
logs growing forever. This is that promise, kept, on the chassis phase's log and
on the gateway door's mirror (backlog #6): every request row stores the FULL
conversation the caller resent, so ``aire_gateway_log`` grows with the square of
a session's length — the one table here that can outgrow the database unswept.

Deletes rows older than ``AIRE_RETENTION_DAYS`` (default 30); the gateway mirror
has its own knob, ``AIRE_GATEWAY_RETENTION_DAYS``, defaulting to the same value
— a named slot, so its window can move without touching ``aire_log``'s. Each
outcome is appended to the file log. Correcting is appending, never rewriting:
[[log-is-the-truth]] §3 explicitly sanctions retention as a ``DELETE ... WHERE
mtime < cutoff`` policy — mutating an entry is what it forbids. NOT swept:
``claude_session_store`` — that is the agent's resumable memory, and deleting it
breaks deathless sessions; its retention (per-project TTL, archiving) stays a
decision that is Bernard's.

**No SELECT here, by law.** [[write-only-daemon]]: this repo only appends and
deletes; every read lives in the front. The row count comes from the DELETE tag.

No ``AIRE_DATABASE_URL`` → no-op (file-only mode has no table to sweep). The file
itself is swept by logrotate (``deploy/logrotate-aire``), not here.

Run by the `aire-sweep.timer` systemd unit, daily. Idempotent by construction.
"""

from __future__ import annotations

import asyncio
import os

from .listen.applog import _now, append
from .listen.config import DSN

RETENTION_DAYS = int(os.environ.get("AIRE_RETENTION_DAYS", "30"))
GATEWAY_RETENTION_DAYS = int(
    os.environ.get("AIRE_GATEWAY_RETENTION_DAYS", str(RETENTION_DAYS))
)
TABLES = (
    ("aire_log", "at", RETENTION_DAYS),
    ("aire_gateway_log", "ts", GATEWAY_RETENTION_DAYS),
)


async def _sweep_table(conn, table: str, column: str, days: int) -> int:
    """One table's cutoff. Identifiers come from TABLES above, never from input.
    A table that does not exist yet (a fresh box before its first gateway turn)
    is a skip worth logging, not a crash that silences the whole broom."""
    import asyncpg

    try:
        tag = await conn.execute(
            f"DELETE FROM {table} WHERE {column} < now() - ($1::int * interval '1 day')",
            days,
        )
    except asyncpg.exceptions.UndefinedTableError:
        append(f"{_now()} - SWEEP {table} skipped (table does not exist yet)")
        return 0
    deleted = int(tag.rsplit(" ", 1)[-1])  # asyncpg returns the tag "DELETE <n>"
    append(f"{_now()} - SWEEP {table} deleted={deleted} older_than={days}d")
    return deleted


async def sweep() -> int:
    if not DSN:
        append(f"{_now()} - SWEEP skipped (no AIRE_DATABASE_URL, file-only mode)")
        return 0

    import asyncpg

    conn = await asyncpg.connect(DSN)
    try:
        total = 0
        for table, column, days in TABLES:
            total += await _sweep_table(conn, table, column, days)
        return total
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(sweep())
