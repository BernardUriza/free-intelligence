"""The NUL poison-pill cure (a wedged batch kept the pen down ~6 days, 2026-07).

Postgres answered and REJECTED the data (SQLSTATE 22xxx): an identical retry can
never succeed, and holding the batch wedges the mirror forever. Mirror line by
line instead; a line Postgres cannot hold even sanitized becomes a marker. The
file keeps the raw original; order is preserved. pop-as-committed so a drop
mid-fallback retries only the uncommitted remainder (no duplicates).
"""

from ..applog import _now


async def mirror_line_by_line(conn, pending: list[str]) -> None:
    import asyncpg

    while pending:
        try:
            await conn.execute(
                "INSERT INTO aire_log (line) VALUES ($1)",
                pending[0].replace("\x00", "�"),
            )
        except asyncpg.DataError as exc:
            await conn.execute(
                "INSERT INTO aire_log (line) VALUES ($1)",
                f"{_now()} - PEN-POISON unstorable line dropped ({exc!r})",
            )
        pending.pop(0)
