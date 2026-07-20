"""The pen's state: a cheap queue put; overflow drops FOR THE MIRROR ONLY (the
file already holds every line). Health flips are logged on state change only."""

import asyncio

from ..applog import _now, append_file


class Pen:
    def __init__(self, dsn: str, maxsize: int = 10_000) -> None:
        self.dsn = dsn
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=maxsize)
        self.healthy = False

    def write(self, line: str) -> None:
        try:
            self.queue.put_nowait(line)
        except asyncio.QueueFull:
            pass

    def mark(self, healthy: bool, detail: str = "") -> None:
        if healthy and not self.healthy:
            append_file(f"{_now()} - PEN-UP mirroring to postgres")
        elif not healthy and self.healthy:
            append_file(f"{_now()} - PEN-DOWN {detail}")
        self.healthy = healthy
