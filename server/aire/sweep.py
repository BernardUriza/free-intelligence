"""AIRE — the broom. The pillar nobody else builds.

The SDK's own docstring delegates retention to the adapter, in writing: *"The SDK
never deletes from your store… Retention is the adapter's responsibility."* AIRE
calls that the cleanest gap in the field — so AIRE does not get to leave its OWN
log growing forever. This is that promise, kept, on the chassis phase's log.

Deletes `aire_log` rows older than ``AIRE_RETENTION_DAYS`` (default 30) and
appends the outcome to the file log. Correcting is appending, never rewriting:
[[log-is-the-truth]] §3 explicitly sanctions retention as a ``DELETE ... WHERE
mtime < cutoff`` policy — mutating an entry is what it forbids.

**No SELECT here, by law.** [[write-only-daemon]]: this repo only appends and
deletes; every read lives in the front repo. The row count comes from the DELETE
command tag, not from a query.

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


async def sweep() -> int:
    if not DSN:
        append(f"{_now()} - SWEEP skipped (no AIRE_DATABASE_URL, file-only mode)")
        return 0

    import asyncpg

    conn = await asyncpg.connect(DSN)
    try:
        tag = await conn.execute(
            "DELETE FROM aire_log WHERE at < now() - ($1::int * interval '1 day')",
            RETENTION_DAYS,
        )
        deleted = int(tag.rsplit(" ", 1)[-1])  # asyncpg returns the tag "DELETE <n>"
        append(f"{_now()} - SWEEP deleted={deleted} older_than={RETENTION_DAYS}d")
        return deleted
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(sweep())
