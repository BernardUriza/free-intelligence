"""Periodic poller — keeps the bot's view of the consolidator fresh.

Why a poller instead of a per-message metadata fetch: every chat turn
already does ~7 I/O hops; adding an Azure HEAD on each one would push
typical latency past the typing-indicator threshold. A 30s tick on the
side gives sub-minute reactivity for "go silent" without any per-turn
cost. The bot only pays one Azure HEAD every 30s regardless of chat
volume.

The poller exposes a thread-/coroutine-safe ``get()`` that returns the
last known snapshot. Hot-path consumers (chat handler, presence updater)
read this and never block on Azure.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

import structlog

from insult.core.siesta.coordination.pg_state import read_snapshot
from insult.core.siesta.state import AWAKE, SiestaSnapshot

log = structlog.get_logger()

DEFAULT_INTERVAL_SECONDS = 30.0
SiestaListener = Callable[[SiestaSnapshot, SiestaSnapshot], Awaitable[None]]


class SiestaPoller:
    """Holds the cached snapshot + a list of edge-trigger listeners.

    Listeners fire only on phase transitions (e.g. AWAKE→LIGHT, REM→AWAKE)
    so subscribers like the presence updater don't re-render on every
    progress tick. Per-progress changes are visible via ``get()``.
    """

    def __init__(self, *, interval_seconds: float = DEFAULT_INTERVAL_SECONDS) -> None:
        self._interval = interval_seconds
        self._snapshot: SiestaSnapshot = AWAKE
        self._task: asyncio.Task[None] | None = None
        self._listeners: list[SiestaListener] = []
        self._lock = asyncio.Lock()

    def get(self) -> SiestaSnapshot:
        """Return the most recent snapshot — non-blocking, no I/O."""
        return self._snapshot

    def is_active(self) -> bool:
        """Convenience: True iff the consolidator is currently working."""
        return self._snapshot.is_active

    def add_listener(self, listener: SiestaListener) -> None:
        """Register a callback fired on every phase transition."""
        self._listeners.append(listener)

    async def tick(self) -> SiestaSnapshot:
        """Fetch one fresh snapshot and dispatch listeners on phase change."""
        new_snapshot = await read_snapshot()
        async with self._lock:
            previous = self._snapshot
            self._snapshot = new_snapshot
        if previous.phase != new_snapshot.phase:
            log.info(
                "siesta_phase_transition",
                old=previous.phase.value,
                new=new_snapshot.phase.value,
                processed=new_snapshot.processed_users,
                total=new_snapshot.total_users,
            )
            await self._notify(previous, new_snapshot)
        return new_snapshot

    async def _notify(self, previous: SiestaSnapshot, current: SiestaSnapshot) -> None:
        for listener in self._listeners:
            try:
                await listener(previous, current)
            except Exception:
                log.exception("siesta_listener_failed")

    def start(self) -> None:
        """Kick off the background polling task."""
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop(), name="siesta-poller")

    async def stop(self) -> None:
        """Cancel the polling task; safe to call when not running."""
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _loop(self) -> None:
        while True:
            try:
                await self.tick()
            except Exception:
                log.exception("siesta_tick_failed")
            await asyncio.sleep(self._interval)
