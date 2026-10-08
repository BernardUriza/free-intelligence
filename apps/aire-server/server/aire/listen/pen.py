"""The pen: mirrors appended lines to the owner's Postgres ([[log-is-the-truth]]).

`write()` is a cheap queue put; `run()` drains in batches and reconnects with
backoff. Postgres unreachable → the queue buffers; overflow drops FOR THE
MIRROR ONLY (the file already holds every line) and says so at both ends of the
gap, in the file and in the mirror. A failed batch is HELD and
retried first on reconnect — never re-queued to the tail: the front reads
ORDER BY seq, so order must match the events. Poison-pill cure in
`_mirror_line_by_line` (story: docs/listener-doctrine.md).
"""

import asyncio

from .applog import _now, append_file
from .config import DB_TIMEOUT_S

SCHEMA = ("CREATE TABLE IF NOT EXISTS aire_log (seq bigserial PRIMARY KEY, "
          "at timestamptz NOT NULL DEFAULT now(), line text NOT NULL);")


class Pen:
    def __init__(self, dsn: str, maxsize: int = 10_000) -> None:
        self.dsn = dsn
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=maxsize)
        self.healthy = False
        self.dropped = 0

    def write(self, line: str) -> None:
        try:
            self.queue.put_nowait(line)
        except asyncio.QueueFull:
            # The file keeps this line; the MIRROR is what loses it, and the
            # front reads the mirror — so an unmarked drop is two memories
            # diverging in silence. The gap gets both ends written down: this
            # line the moment it opens, and a counted one when it closes.
            if not self.dropped:
                append_file(f"{_now()} - PEN-OVERFLOW mirror queue full, dropping")
            self.dropped += 1

    def mark(self, healthy: bool, detail: str = "") -> None:
        if healthy and not self.healthy:
            append_file(f"{_now()} - PEN-UP mirroring to postgres")
        elif not healthy and self.healthy:
            append_file(f"{_now()} - PEN-DOWN {detail}")
        self.healthy = healthy

    async def run(self) -> None:
        import asyncpg

        delay, pending = 2, []
        while True:
            try:
                conn = await asyncpg.connect(self.dsn, timeout=DB_TIMEOUT_S)
                await conn.execute(SCHEMA)
                self.mark(healthy=True)
                delay = 2
                while True:
                    pending = await self._next_batch(pending)
                    pending = await self._insert(conn, pending)
            except Exception as exc:
                self.mark(healthy=False, detail=repr(exc))
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

    async def _next_batch(self, pending: list[str]) -> list[str]:
        if pending:
            return pending
        batch = [await self.queue.get()]
        while len(batch) < 500:
            try:
                batch.append(self.queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return batch + self._overflow_marker()

    def _overflow_marker(self) -> list[str]:
        """Closes an open gap. It goes to BOTH memories on purpose: the file
        already had its opening line, and the mirror needs the whole marker or
        an outage reads there as a quiet stretch instead of a hole."""
        if not self.dropped:
            return []
        line = f"{_now()} - PEN-OVERFLOW {self.dropped} lines never reached postgres"
        self.dropped = 0
        append_file(line)
        return [line]

    async def _insert(self, conn, batch: list[str]) -> list[str]:
        import asyncpg

        try:
            await conn.executemany(
                "INSERT INTO aire_log (line) VALUES ($1)", [(ln,) for ln in batch]
            )
            return []
        except asyncpg.DataError:
            await self._mirror_line_by_line(conn, batch)
            return []

    async def _mirror_line_by_line(self, conn, pending: list[str]) -> None:
        """DataError (SQLSTATE 22xxx): an identical retry can NEVER succeed, and
        holding the batch wedges the mirror — the 6-day NUL poison pill.
        pop-as-committed so a drop mid-fallback retries only the remainder."""
        import asyncpg

        while pending:
            try:
                await conn.execute("INSERT INTO aire_log (line) VALUES ($1)",
                                   pending[0].replace("\x00", "�"))
            except asyncpg.DataError as exc:
                await conn.execute(
                    "INSERT INTO aire_log (line) VALUES ($1)",
                    f"{_now()} - PEN-POISON unstorable line dropped ({exc!r})")
            pending.pop(0)
