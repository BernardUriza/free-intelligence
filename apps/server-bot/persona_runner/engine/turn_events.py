"""Bitácora de eventos por boleto — los `tool_call` de un turno, en vivo y
reproducibles por cursor (OG118-EXTERNAL-TURN-1, 2026-10-15).

AIRE ya emite cada herramienta en el instante en que el SDK entrega su
`ToolUseBlock`; fi-runner la traduce al contrato; `_run_turn` la drenaba en un
solo `TurnResponse` y el consumidor sólo veía pings. Aquí cada frame se anexa
con un `id` secuencial y `GET /v1/turn/jobs/{id}/events` lo sirve como SSE desde
el cursor que el cliente traiga (`Last-Event-ID`), siguiendo en vivo hasta que
el turno cierra la bitácora.

Vive en RAM, igual que el boleto (`persona_core.tickets`): la fila del ledger es
el handoff del RESULTADO entre procesos; un job reanudado en otra réplica se
re-corre y abre bitácora nueva. Con `maxReplicas: 1` es el mismo proceso. Una
bitácora cerrada sobrevive `DONE_TTL_S`, el mismo plazo que su boleto.

Fase 1: sólo `tool_call`. El texto sigue llegando completo en el resultado,
porque el post-proceso de marcadores (`[REACT:]`, GIFs) opera sobre el final.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Any

from persona_core.tickets import DONE_TTL_S

__all__ = ["PING_S", "TurnEventLog", "clear", "close_log", "emit", "get_log", "open_log"]

PING_S = 15.0


class TurnEventLog:
    def __init__(self) -> None:
        self._frames: list[dict[str, Any]] = []
        self._changed = asyncio.Event()
        self.closed = False
        self.closed_at: float | None = None

    def __len__(self) -> int:
        return len(self._frames)

    def append(self, frame: dict[str, Any]) -> int:
        seq = len(self._frames) + 1
        self._frames.append({"id": seq, **frame})
        self._changed.set()
        return seq

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.closed_at = time.monotonic()
        self._changed.set()

    async def tail(self, after: int = 0, *, ping_s: float = PING_S) -> AsyncIterator[dict[str, Any] | None]:
        """Los frames después de `after`, luego los nuevos conforme lleguen.
        Rinde `None` cada `ping_s` de silencio para que el transporte dé señal de
        vida. Termina cuando la bitácora se cierra y todo quedó servido."""
        cursor = max(0, after)
        while True:
            while cursor < len(self._frames):
                yield self._frames[cursor]
                cursor += 1
            if self.closed:
                return
            waiter = self._changed
            try:
                await asyncio.wait_for(waiter.wait(), timeout=ping_s)
            except TimeoutError:
                yield None
                continue
            if waiter is self._changed:
                self._changed = asyncio.Event()


_LOGS: dict[str, TurnEventLog] = {}


def _reap() -> None:
    now = time.monotonic()
    for job_id, log in list(_LOGS.items()):
        if log.closed_at is not None and now - log.closed_at > DONE_TTL_S:
            del _LOGS[job_id]


def open_log(job_id: str) -> TurnEventLog:
    _reap()
    log = _LOGS.get(job_id)
    if log is None or log.closed:
        log = TurnEventLog()
        _LOGS[job_id] = log
    return log


def get_log(job_id: str) -> TurnEventLog | None:
    _reap()
    return _LOGS.get(job_id)


def emit(job_id: str | None, frame: dict[str, Any]) -> None:
    """Anexa si hay bitácora abierta para el job; el camino síncrono legacy
    (sin `job_id`) no tiene bitácora y aquí no pasa nada."""
    if not job_id:
        return
    log = _LOGS.get(job_id)
    if log is not None and not log.closed:
        log.append(frame)


def close_log(job_id: str | None) -> None:
    if job_id and (log := _LOGS.get(job_id)) is not None:
        log.close()


def clear() -> None:
    _LOGS.clear()
