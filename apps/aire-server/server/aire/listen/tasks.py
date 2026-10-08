"""Strong task refs: the event loop keeps only WEAK references to tasks (python
docs on create_task: "save a reference"), so an unreferenced background task can
be garbage-collected MID-FLIGHT — for the pen that means the mirror dies with no
PEN-DOWN, no traceback, no signal at all. Every long-lived task is spawned here."""

import asyncio
from typing import Coroutine

_TASKS: set[asyncio.Task] = set()


def spawn(coro: Coroutine) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    return task
