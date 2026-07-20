"""The pen's drain loop: connect, insert batches, reconnect with backoff."""

import asyncio

from ..config import DB_TIMEOUT_S
from .batches import insert, next_batch
from .state import Pen

SCHEMA = ("CREATE TABLE IF NOT EXISTS aire_log (seq bigserial PRIMARY KEY, "
          "at timestamptz NOT NULL DEFAULT now(), line text NOT NULL);")


async def run(pen: Pen) -> None:
    import asyncpg
    delay, pending = 2, []
    while True:
        try:
            conn = await asyncpg.connect(pen.dsn, timeout=DB_TIMEOUT_S)
            await conn.execute(SCHEMA)
            pen.mark(healthy=True)
            delay = 2
            while True:
                pending = await next_batch(pen.queue, pending)
                pending = await insert(conn, pending)
        except Exception as exc:
            pen.mark(healthy=False, detail=repr(exc))
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
