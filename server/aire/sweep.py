"""AIRE — the broom. The pillar nobody else builds.

The SDK's own docstring delegates retention to the adapter, in writing: *"The SDK
never deletes from your store… Retention is the adapter's responsibility."* AIRE
calls that the cleanest gap in the field — so AIRE does not get to leave its OWN
logs growing forever. This is that promise, kept, on the chassis phase's log and
on the gateway door's mirror (backlog #6). Since #41 a request row no longer
stores the whole conversation the caller resent — it keeps the last message and
a fingerprint into ``aire_gateway_blob`` — but ``aire_gateway_log`` is still the
table here that grows with traffic and would outgrow the database unswept.

Deletes rows older than ``AIRE_RETENTION_DAYS`` (default 30); the gateway mirror
has its own knob, ``AIRE_GATEWAY_RETENTION_DAYS``, defaulting to the same value
— a named slot, so its window can move without touching ``aire_log``'s. Each
outcome is appended to the file log. Correcting is appending, never rewriting:
[[log-is-the-truth]] §3 explicitly sanctions retention as a ``DELETE ... WHERE
mtime < cutoff`` policy — mutating an entry is what it forbids. NOT swept:
``claude_session_store`` — that is the agent's resumable memory, and deleting it
breaks deathless sessions; its retention (per-project TTL, archiving) stays a
decision that is Bernard's.

**No waiter read here, by law.** [[write-only-daemon]]: this repo only appends
and deletes; every read that serves a VIEW lives in the front. The row count
comes from the DELETE tag, never from a `count(*)`. The blob sweep's `NOT EXISTS`
is the one read, and it is the kind the rule sanctions: it renders nothing and it
gates a delete — it is the delete asking what it is still allowed to remove.

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


async def _sweep_blobs(conn, days: int) -> int:
    """Orphaned deduped values only (#41). A blob still referenced by ANY row is
    untouchable: deleting it would turn that row into a dangling pointer, and the
    front that reads this log cannot repair one — it would render a reference
    where a system prompt used to be.

    The age floor is belt to the referential brace: a fingerprint whose rows all
    aged out is an orphan, but the daemon caches what it has already written
    (`gateway_store.BLOB_TTL_S`), so this waits out that cache too."""
    import asyncpg

    try:
        tag = await conn.execute(
            "DELETE FROM aire_gateway_blob b"
            " WHERE b.first_seen < now() - ($1::int * interval '1 day')"
            "   AND NOT EXISTS ("
            "     SELECT 1 FROM aire_gateway_log l,"
            "       LATERAL jsonb_each(coalesce(l.body -> '$elided', '{}'::jsonb)) e"
            "     WHERE jsonb_typeof(l.body) = 'object'"
            "       AND jsonb_typeof(e.value) = 'object'"
            "       AND e.value ->> '$ref' = b.fingerprint)",
            days,
        )
    except asyncpg.exceptions.UndefinedTableError:
        append(f"{_now()} - SWEEP aire_gateway_blob skipped (table does not exist yet)")
        return 0
    deleted = int(tag.rsplit(" ", 1)[-1])
    append(f"{_now()} - SWEEP aire_gateway_blob deleted={deleted} orphans older_than={days}d")
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
        # AFTER the log, never before: a row deleted above is a reference gone,
        # and this is what turns that into reclaimed space instead of a leak.
        total += await _sweep_blobs(conn, GATEWAY_RETENTION_DAYS)
        return total
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(sweep())
