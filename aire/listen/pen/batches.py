"""Batch fill + insert. A failed batch is HELD and retried first on reconnect —
never re-queued to the tail (the front reads ORDER BY seq; order must match)."""

import asyncio

from .poison import mirror_line_by_line


async def next_batch(queue: asyncio.Queue, pending: list[str]) -> list[str]:
    if pending:
        return pending
    batch = [await queue.get()]
    while len(batch) < 500:
        try:
            batch.append(queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    return batch


async def insert(conn, batch: list[str]) -> list[str]:
    import asyncpg
    try:
        await conn.executemany(
            "INSERT INTO aire_log (line) VALUES ($1)", [(ln,) for ln in batch]
        )
        return []
    except asyncpg.DataError:
        await mirror_line_by_line(conn, batch)
        return []
