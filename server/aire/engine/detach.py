"""Fire-and-forget turns — backlog #22a. A turn launched with `background: true`
runs as a task DECOUPLED from the HTTP request, so a long book does not die when
the socket drops. Ockham: the session IS the handle (no jobs table) — its
transcript is the progress, its artifacts (#22b) are the result.

The running task is held by a STRONG ref here so the GC cannot reap it mid-turn
(Art. 5 — never lose in-flight work). One turn per session at a time: a second
launch while one runs is refused, mirroring the per-client lock upstream.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable


class Detached:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    def running(self, key: str) -> bool:
        task = self._tasks.get(key)
        return task is not None and not task.done()

    def launch(self, key: str, make_coro: Callable[[], Awaitable[Any]]) -> None:
        if self.running(key):
            raise RuntimeError(f"a turn is already running on {key}")
        task = asyncio.create_task(make_coro())
        self._tasks[key] = task
        task.add_done_callback(lambda _t: self._tasks.pop(key, None))
