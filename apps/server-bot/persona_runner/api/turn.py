"""Turn surface — every persona turn rides AIRE's engine door.

The local Claude-Agent-SDK host this module used to run (a pooled
ClaudeSDKClient per channel, history folding, the `_drain` stream
accumulator) died when the AIRE flag flipped permanent — backlog
``aire-engine-stage2.md``, deletion step. The route itself (casitas, topics,
facts pre-fetch, error mapping) lives in ``engine/aire_route.py``.

Dos formas de pedir el mismo turno:

- ``POST /v1/turn`` — síncrono. Sirve mientras el turno quepa en los 240 s que
  el ingress de Container Apps concede a cualquier request.
- ``POST /v1/turn/jobs`` + ``GET /v1/turn/jobs/{job_id}`` — con boleto. El turno
  corre en una task del runner y el cliente pregunta en requests cortas, así que
  su duración deja de estar atada al tope del ingress (``engine/turn_jobs.py``).
  El boleto es durable (2026-09-23): un 404 ya sólo significa "id desconocido"
  o "Postgres inalcanzable"; un runner reiniciado contesta desde su fila.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from persona_core.tickets import LedgerRow
from persona_runner.api.turn_pipeline import serve_turn
from persona_runner.core.auth import check_auth
from persona_runner.core.schemas import TurnRequest, TurnResponse
from persona_runner.engine import principal_identity, turn_events, turn_jobs

router = APIRouter()


class TurnJobAccepted(BaseModel):
    job_id: str
    status: str = "running"


class TurnJobStatus(BaseModel):
    job_id: str
    status: str  # "running" | "done"
    response: TurnResponse | None = None


@router.post("/v1/turn", response_model=TurnResponse)
async def turn(req: TurnRequest, authorization: str | None = Header(default=None)) -> TurnResponse:
    """Run one persona turn through AIRE's engine door."""
    check_auth(authorization)
    req = await principal_identity.apply(req)
    return await serve_turn(req)


@router.post("/v1/turn/jobs", response_model=TurnJobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def submit_turn_job(req: TurnRequest, authorization: str | None = Header(default=None)) -> TurnJobAccepted:
    """Arranca el turno en background y devuelve su boleto. La misma alta dos
    veces (mismo `job_id`) es UN turno, aunque la segunda llegue a otra réplica.
    La identidad se resuelve ANTES de persistir el job: un job reanudado en otra
    réplica ya lleva el principal canónico, no vuelve a preguntar."""
    check_auth(authorization)
    req = await principal_identity.apply(req)
    job = await turn_jobs.submit(req, runner=serve_turn)
    return TurnJobAccepted(job_id=job.ticket_id)


def _sse(event: str | None, data: dict | None, event_id: int | None = None) -> str:
    head = (f"id: {event_id}\n" if event_id is not None else "") + (f"event: {event}\n" if event else "")
    return f"{head}data: {json.dumps(data or {}, ensure_ascii=False)}\n\n"


async def _job_events(log: turn_events.TurnEventLog | None, after: int) -> AsyncIterator[str]:
    if log is not None:
        async for frame in log.tail(after):
            if frame is None:
                yield ": ping\n\n"
                continue
            yield _sse(None, {k: v for k, v in frame.items() if k != "id"}, event_id=frame["id"])
    yield _sse("done", {})


@router.get("/v1/turn/jobs/{job_id}/events")
async def turn_job_events(
    job_id: str,
    authorization: str | None = Header(default=None),
    after: int = Query(default=0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    """La bitácora del boleto como SSE: cada `tool_call` del turno con su `id`
    secuencial, desde el cursor (`Last-Event-ID` o `?after=`) y luego en vivo;
    `: ping` cada 15 s de silencio; `event: done` cuando el turno cerró la
    bitácora (el RESULTADO se recoge con el poll del boleto, no aquí). Un job
    que este proceso conoce pero sin bitácora (terminó antes, o vive en la
    fila) cierra de inmediato; un id desconocido es 404 como en el poll."""
    check_auth(authorization)
    log = turn_events.get_log(job_id)
    if log is None and await turn_jobs.lookup(job_id, runner=serve_turn) is None:
        raise HTTPException(status_code=404, detail=f"unknown turn job {job_id!r}")
    cursor = int(last_event_id) if last_event_id and last_event_id.isdigit() else after
    return StreamingResponse(
        _job_events(log, cursor),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _from_row(job_id: str, row: LedgerRow) -> TurnJobStatus:
    if row.status == "done":
        return TurnJobStatus(job_id=job_id, status="done", response=turn_jobs.JOBS.decode_result(row))
    if row.terminal:
        raise HTTPException(status_code=502, detail=row.error or row.status)
    return TurnJobStatus(job_id=job_id, status="running")


@router.get("/v1/turn/jobs/{job_id}", response_model=TurnJobStatus)
async def poll_turn_job(
    job_id: str,
    authorization: str | None = Header(default=None),
    wait_s: float = Query(default=turn_jobs.MAX_WAIT_S, ge=0.0),
) -> TurnJobStatus:
    """Long-poll acotado del boleto.

    RAM primero; si este proceso no lo tiene, la fila: un resultado ya escrito
    se sirve tal cual; un job que otra réplica sigue corriendo se espera sobre la
    fila; uno huérfano se reanuda aquí. 404 = id desconocido (o Postgres
    inalcanzable tras un reinicio). Un fallo del turno sale con la misma forma
    que en el camino síncrono: la excepción se re-lanza y la mapea el mismo
    handler; un fallo registrado por otra réplica es un 502 con su `error`.
    """
    check_auth(authorization)
    got = await turn_jobs.lookup(job_id, runner=serve_turn)
    if got is None:
        raise HTTPException(status_code=404, detail=f"unknown turn job {job_id!r}")
    if isinstance(got, LedgerRow):
        if got.terminal:
            return _from_row(job_id, got)
        row = await turn_jobs.JOBS.wait_row(job_id, wait_s)
        if row is None:
            return TurnJobStatus(job_id=job_id, status="running")
        return _from_row(job_id, row)
    try:
        done, response = await turn_jobs.JOBS.wait(got, wait_s)
    except turn_jobs.NotResumableError as exc:
        # La fila ya quedó `failed`; el gateway lo lee como cerebro caído y el
        # host reintenta con un id nuevo, re-ingiriendo los adjuntos de Discord.
        turn_jobs.JOBS.drop(job_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not done:
        return TurnJobStatus(job_id=job_id, status="running")
    turn_jobs.JOBS.drop(job_id)
    return TurnJobStatus(job_id=job_id, status="done", response=response)
