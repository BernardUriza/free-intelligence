"""How fast the memory is growing — the watch [[do-budget]] asked for and nobody built.

That rule states the blind spot in its own words:

    "Never watch only the cloud where the spend is frozen. The blind spot always
    opens over the thing that grows."

DigitalOcean is frozen at $4/mo and costwatch has checked it nightly for months.
The owner's Azure Postgres is the half that GROWS, and the only thing ever
watched there was whether the broom's TIMER was alive — never how much it was
sweeping against how much was arriving. A broom that runs perfectly while the
input rate climbs is a green light over a rising line, and #41 was found by a
review rather than by a watch.

Prints the size of the whole database and of each table, plus MB/day measured
over each table's own live window, and exits non-zero past a ceiling. Run from
costwatch's existing SSH block, beside `wall.py`.

Reading `pg_total_relation_size` is catalog metadata, not table content: it
renders nothing and it arms an alarm, the same kind of read the reader-wall
check is ([[write-only-daemon]]).
"""

from __future__ import annotations

import asyncio
import os
import sys

# table -> (the column that dates a row, whether it is a raw epoch number).
# TWO of these the broom deliberately never sweeps, so this is the only thing
# measuring them: `claude_session_store`, because deleting it breaks deathless
# sessions, and `aire_corpus_chunk`, because those are a consumer's uploaded
# documents and age is not a reason to delete somebody's files. Unbounded by
# design means watched on purpose — a table absent from this map is a table
# nobody is measuring at all.
TABLES = {
    "aire_corpus_chunk": ("at", False),
    "aire_gateway_log": ("ts", False),
    "aire_log": ("at", False),
    "claude_session_store": ("mtime", True),
    "aire_gateway_blob": ("first_seen", False),
    "aire_casita": ("ts", False),
    "aire_token": ("created_at", False),
    "aire_device": (None, False),
    "aire_access_request": ("requested_at", False),
}
CEILING_MB = float(os.environ.get("AIRE_DB_CEILING_MB", "250"))


def _span(lo: float, hi: float) -> float:
    """Days between two epochs, whichever unit the column happens to use — the
    SDK's `mtime` is seconds in some rows and millis in others."""
    scale = 1000.0 if max(abs(lo), abs(hi)) > 1e12 else 1.0
    return (hi / scale - lo / scale) / 86400


async def _rate(conn, table: str, column: str | None, epoch: bool) -> tuple[float, float]:
    """(days the table spans, MB/day). No date column, one row, or under half a
    day reports NO rate: a number invented from one sample is worse than none."""
    if column is None:
        return 0.0, 0.0
    row = await conn.fetchrow(
        f"SELECT min({column}) AS lo, max({column}) AS hi, count(*) AS n FROM {table}")  # noqa: S608
    if row["n"] < 2 or row["lo"] is None:
        return 0.0, 0.0
    days = (_span(float(row["lo"]), float(row["hi"])) if epoch
            else (row["hi"] - row["lo"]).total_seconds() / 86400)
    if days < 0.5:
        return days, 0.0
    size = await conn.fetchval("SELECT pg_total_relation_size($1)", table)
    return days, (size / 1048576) / days


async def main() -> int:
    import asyncpg

    dsn = os.environ.get("AIRE_DATABASE_URL", "")
    if not dsn:
        print("growth: AIRE_DATABASE_URL is empty — nothing to measure", file=sys.stderr)
        return 1
    conn = await asyncpg.connect(dsn, timeout=20)
    try:
        total = await conn.fetchval("SELECT pg_database_size(current_database())")
        print(f"database: {total / 1048576:.1f} MB (ceiling {CEILING_MB:.0f} MB)")
        for table, (column, epoch) in sorted(TABLES.items()):
            size = await conn.fetchval("SELECT pg_total_relation_size(to_regclass($1))", table)
            if size is None:
                print(f"  {table:24} (does not exist yet)")
                continue
            days, per_day = await _rate(conn, table, column, epoch)
            rate = f"{per_day:6.2f} MB/day over {days:5.1f}d" if per_day else "no rate yet"
            print(f"  {table:24} {size / 1048576:8.2f} MB   {rate}")
    finally:
        await conn.close()
    if total / 1048576 >= CEILING_MB:
        print(f"::error::the memory is {total / 1048576:.0f} MB, past the "
              f"{CEILING_MB:.0f} MB ceiling — the broom is losing to the input rate",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
