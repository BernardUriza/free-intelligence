"""Turnos con boleto en el runner — `khimeras_shared.tickets` aplicado a `/v1/turn`.

El porqué vive en ese módulo (el ingress corta a los 240 s; un turno de Vultur
tardó 326.9 s y se tiró). Aquí se nombra el registro, se fija el tipo y se le
da su fila (`engine/turn_ledger`, 2026-09-23): un runner que muere a media
generación deja la fila `running` con el latido viejo; la réplica que la
encuentra la reclama y RE-CORRE el turno bajo el mismo `job_id` — hasta la
fase B (AIRE `background:true` + reattach) reanudar es re-preguntar, con la
historia sin volver a plegar y la nota de reintento en la guía. Eso aplica sólo
si el intento anterior CRUZÓ a AIRE (`aire_sent_at`); si murió antes, el job
corre como turno nuevo (`crossed_to_aire`).

Los adjuntos no se persisten (base64 de varios MB): un job con adjuntos es
no-reanudable — la fila queda `failed` con `not_resumable`, el gateway lo lee
como cerebro caído y el host reintenta con un id nuevo, re-ingiriendo la imagen
de Discord.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

import structlog

from khimeras_shared import tickets
from khimeras_shared.tickets import MAX_WAIT_S, LedgerRow, Ticket, TicketRegistry
from persona_runner.core import config
from persona_runner.core.schemas import TurnRequest, TurnResponse
from persona_runner.engine.turn_ledger import PgTurnLedger

__all__ = [
    "JOBS",
    "MAX_WAIT_S",
    "NotResumableError",
    "TurnJob",
    "drain_for_shutdown",
    "lookup",
    "resume_stale_at_boot",
    "submit",
]

log = structlog.get_logger()

type TurnJob = Ticket[TurnResponse]
type Runner = Callable[[TurnRequest], Awaitable[TurnResponse]]

LEDGER = PgTurnLedger()
JOBS: TicketRegistry[TurnResponse] = TicketRegistry(
    "turn-job",
    ledger=LEDGER,
    encode=lambda response: response.model_dump(mode="json"),
    decode=TurnResponse.model_validate,
)

BOOT_RESUME_LIMIT = 10


class NotResumableError(RuntimeError):
    """El job no se puede re-correr desde su fila (adjuntos no persistidos)."""


def _label(req: TurnRequest) -> str:
    return f"{req.persona_id or 'insult'}:{req.channel_id}"


def _payload(req: TurnRequest) -> dict[str, Any]:
    data = req.model_dump(mode="json", exclude={"attachments", "resumed"})
    data["has_attachments"] = bool(req.attachments)
    return data


def _request_from(payload: dict[str, Any], *, resumed: bool) -> TurnRequest:
    data = {key: value for key, value in payload.items() if key != "has_attachments"}
    data["resumed"] = resumed
    return TurnRequest.model_validate(data)


def crossed_to_aire(row: LedgerRow) -> bool:
    """¿El intento anterior de este job llegó a mandarle el mensaje a AIRE?

    Lo dice `aire_sent_at` (`aire_route` lo marca justo antes del POST a la
    puerta). Sólo un job que CRUZÓ puede haber dejado el mensaje del usuario en
    el transcript de AIRE; uno que murió antes (topic, ruteo, facts) es un turno
    que AIRE nunca vio, y reanudarlo como "reintento" le quitaba la historia al
    tópico y le metía al modelo una nota sobre un corte que no le pasó.

    Una fila sin el dato (un ledger que no lo reporta) se lee como CRUZADA: es
    el contrato de la fase A, y equivocarse hacia ahí cuesta una nota de más;
    equivocarse hacia el otro lado pliega la historia DOS veces en la sesión.
    """
    return bool(row.extra.get("aire_sent", True))


def _resumer(runner: Runner) -> Callable[[LedgerRow], Coroutine[Any, Any, TurnResponse]]:
    async def resume(row: LedgerRow) -> TurnResponse:
        if row.payload.get("has_attachments"):
            raise NotResumableError("not_resumable: attachments are not persisted")
        crossed = crossed_to_aire(row)
        if not crossed:
            # Nada que duplicar: el turno corre como si fuera la primera vez.
            # Un `aire_route_turn_resumed` queda así reservado a los que SÍ
            # mandan el mensaje por segunda vez — la cifra que la fase B
            # (reattach) tiene que llevar a cero.
            log.info("agent_runner_job_resumed_before_aire", job_id=row.ticket_id, attempts=row.attempts)
        return await runner(_request_from(row.payload, resumed=crossed))

    return resume


async def submit(req: TurnRequest, *, runner: Runner) -> TurnJob | LedgerRow:
    """Alta idempotente por `job_id`. Devuelve el boleto en RAM si este proceso
    lo corre, o la fila cuando otro ya lo terminó o lo sigue corriendo."""
    job_id = req.job_id or uuid.uuid4().hex

    # La corrida en vivo usa el request ORIGINAL, nunca el payload de la fila: la
    # fila no guarda los adjuntos, y reconstruir desde ella tiraba cada imagen en
    # el alta (P0 2026-09-25, regresión de c74dbf4). La fila sólo sirve para
    # reanudar, y reanudar un job con adjuntos ya es `not_resumable`.
    async def run(_payload: dict[str, Any]) -> TurnResponse:
        return await runner(req.model_copy(update={"resumed": False}))

    return await JOBS.open_durable(
        _payload(req),
        run,
        ticket_id=job_id,
        label=_label(req),
        deadline_s=config.RUNNER_JOB_DEADLINE_S,
        resume=_resumer(runner),
    )


async def lookup(job_id: str, *, runner: Runner) -> TurnJob | LedgerRow | None:
    return await JOBS.lookup(job_id, resume=_resumer(runner))


async def resume_stale_at_boot(runner: Runner) -> int:
    """Reclama las filas huérfanas que dejó la réplica anterior. Acotado y
    best-effort: un ledger caído devuelve 0 y el boot sigue."""
    ids = await LEDGER.stale_ids(stale_s=tickets.STALE_S, max_attempts=tickets.MAX_ATTEMPTS, limit=BOOT_RESUME_LIMIT)
    if not ids:
        return 0
    resumed = 0
    for job_id in ids:
        got = await lookup(job_id, runner=runner)
        if isinstance(got, Ticket):
            resumed += 1
    log.info("agent_runner_boot_resumed_jobs", found=len(ids), resumed=resumed)
    return resumed


async def drain_for_shutdown(timeout_s: float) -> int:
    """Espera a que los jobs abiertos terminen; al vencer, suelta sus filas para
    que la réplica sucesora las reanude sin esperar STALE_S. Devuelve cuántas se
    soltaron."""
    open_ids = JOBS.running_ids()
    if not open_ids:
        return 0
    log.warning("agent_runner_shutdown_waiting_jobs", open=len(open_ids), timeout_s=timeout_s)
    deadline = time.monotonic() + timeout_s
    while JOBS.running_ids() and (left_s := deadline - time.monotonic()) > 0:
        await asyncio.sleep(min(1.0, left_s))
    left = JOBS.running_ids()
    if not left:
        log.info("agent_runner_shutdown_jobs_drained", drained=len(open_ids))
        return 0
    released = await JOBS.release_open()
    log.error("agent_runner_shutdown_jobs_abandoned", abandoned=len(left), released=released)
    return released
