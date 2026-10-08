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
from collections.abc import AsyncIterator
from typing import Any, Awaitable, Callable

from .contract import CostSink
from .drain import turn_cost


async def drain_detached(events: AsyncIterator[dict[str, Any]], key: str,
                         on_cost: CostSink | None = None) -> None:
    """Consume a detached turn's stream to the end, with nobody listening.

    `on_cost` is what a per-caller ceiling hangs on: the socket is gone, so a
    turn nobody watches must still bill whoever launched it. Without it a capped
    key (#32d) bought unlimited turns by adding one flag to the body. Errors are
    printed because there is no client left to tell.
    """
    try:
        async for ev in events:
            if on_cost is not None and ev.get("type") == "result":
                await on_cost(turn_cost(ev))
            if ev.get("type") == "error":
                print(f"DETACHED {key} {ev.get('error')}: {ev.get('detail', '')}")
    except Exception as exc:  # noqa: BLE001 — no client to tell; log for the operator
        print(f"DETACHED {key} failed: {type(exc).__name__}: {exc}")


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
