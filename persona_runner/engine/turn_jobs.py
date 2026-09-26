"""Turnos con boleto en el runner — `khimeras_shared.tickets` aplicado a `/v1/turn`.

El porqué vive en ese módulo (el ingress corta a los 240 s; un turno de Vultur
tardó 326.9 s y se tiró). Aquí se nombra el registro, se fija el tipo y se le
da su fila (`engine/turn_ledger`, 2026-09-23): un runner que muere a media
generación deja la fila `running` con el latido viejo; la réplica que la
encuentra la reclama y RE-CORRE el turno bajo el mismo `job_id` — hasta la
fase B (AIRE `background:true` + reattach) reanudar es re-preguntar, con la
historia sin volver a plegar y la nota de reintento en la guía.

Las imágenes SÍ se persisten desde aire-server #50: viajan como referencia (la
URL firmada del CDN de Discord, unos cientos de bytes), así que la fila las
guarda y un job reanudado las trae por construcción. La firma dura 24 h: si al
reanudar ya venció, el job es `not_resumable` en voz alta, nunca un turno sin
la imagen. Lo que sigue sin persistirse son los adjuntos INLINE (texto y PDFs en
base64): un job con ellos sigue siendo no-reanudable y el host reintenta con un
id nuevo, re-ingiriendo el mensaje de Discord.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable, Coroutine
from typing import Any
from urllib.parse import parse_qs, urlsplit

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


def _is_reference(block: dict) -> bool:
    source = (block or {}).get("source") or {}
    return block.get("type") in ("image", "document") and source.get("type") == "url" and bool(source.get("url"))


def _payload(req: TurnRequest) -> dict[str, Any]:
    data = req.model_dump(mode="json", exclude={"attachments", "resumed"})
    blocks = req.attachments or []
    if blocks and all(_is_reference(b) for b in blocks):
        data["attachments"] = blocks  # referencias: la fila las carga (#50)
    data["has_attachments"] = bool(blocks) and "attachments" not in data
    return data


def _expired(blocks: list[dict] | None, *, margin_s: float = 60.0) -> bool:
    """¿Alguna URL firmada de Discord ya venció? `ex` es el epoch en hex."""
    for block in blocks or []:
        ex = parse_qs(urlsplit(block["source"]["url"]).query).get("ex", [""])[0]
        try:
            if int(ex, 16) < time.time() + margin_s:
                return True
        except ValueError:
            continue
    return False


def _request_from(payload: dict[str, Any], *, resumed: bool) -> TurnRequest:
    data = {key: value for key, value in payload.items() if key != "has_attachments"}
    data["resumed"] = resumed
    return TurnRequest.model_validate(data)


def _resumer(runner: Runner) -> Callable[[LedgerRow], Coroutine[Any, Any, TurnResponse]]:
    async def resume(row: LedgerRow) -> TurnResponse:
        if row.payload.get("has_attachments"):
            raise NotResumableError("not_resumable: attachments are not persisted")
        if _expired(row.payload.get("attachments")):
            raise NotResumableError("not_resumable: image references expired")
        return await runner(_request_from(row.payload, resumed=True))

    return resume


async def submit(req: TurnRequest, *, runner: Runner) -> TurnJob | LedgerRow:
    """Alta idempotente por `job_id`. Devuelve el boleto en RAM si este proceso
    lo corre, o la fila cuando otro ya lo terminó o lo sigue corriendo."""
    job_id = req.job_id or uuid.uuid4().hex

    # La corrida en vivo usa el request ORIGINAL, nunca el payload de la fila:
    # reconstruir desde ella tiraba cada imagen en el alta (P0 2026-09-25,
    # regresión de c74dbf4). La fila sólo sirve para reanudar.
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
