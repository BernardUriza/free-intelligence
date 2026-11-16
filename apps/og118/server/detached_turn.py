"""OG118-TURN-SURVIVES-1 — a turn outlives the connection that asked for it.

A phone that leaves the foreground drops its socket. The turn used to die with
it, and the retry paid for a second one. A client that asks for it
(`survive_disconnect`) gets a turn whose runner keeps going when the stream is
abandoned; its answer lands in the conversation record the same way a late
external answer does. An explicit stop is a different act: `cancel` ends it."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable

log = logging.getLogger(__name__)

LateDelivery = Callable[[list[dict]], Awaitable[None]]
TurnKey = tuple[str, str]

_RUNNING: dict[TurnKey, asyncio.Task] = {}
_LATE_TASKS: set[asyncio.Task] = set()
_DONE = object()


async def surviving(events: AsyncIterator[dict], *, key: TurnKey, deliver_late: LateDelivery) -> AsyncIterator[dict]:
    queue: asyncio.Queue = asyncio.Queue()
    seen: list[dict] = []

    async def pump() -> None:
        try:
            async for event in events:
                seen.append(event)
                await queue.put(event)
        except Exception as exc:
            failure = {"type": "error", "message": str(exc)}
            seen.append(failure)
            await queue.put(failure)
        finally:
            await queue.put(_DONE)

    task = asyncio.create_task(pump())
    _RUNNING[key] = task
    task.add_done_callback(lambda done: _forget(key, done))
    delivered_live = False
    try:
        while True:
            item = await queue.get()
            if item is _DONE:
                delivered_live = True
                return
            yield item
    finally:
        if not delivered_live:
            _deliver_when_done(task, seen, deliver_late)


def cancel(key: TurnKey) -> bool:
    task = _RUNNING.get(key)
    if task is None or task.done():
        return False
    task.cancel()
    return True


def _forget(key: TurnKey, task: asyncio.Task) -> None:
    if _RUNNING.get(key) is task:
        del _RUNNING[key]


def _answered(seen: list[dict]) -> bool:
    return any(e.get("type") == "result" for e in seen) and not any(e.get("type") == "error" for e in seen)


def _deliver_when_done(task: asyncio.Task, seen: list[dict], deliver_late: LateDelivery) -> None:
    async def finish() -> None:
        try:
            await task
        except asyncio.CancelledError:
            return
        if not _answered(seen):
            return
        try:
            await deliver_late(seen)
        except Exception:
            log.exception("abandoned turn was not delivered")

    late = asyncio.create_task(finish())
    _LATE_TASKS.add(late)
    late.add_done_callback(_LATE_TASKS.discard)
