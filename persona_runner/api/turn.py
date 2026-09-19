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
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel

from persona_runner.core.auth import check_auth
from persona_runner.core.schemas import TurnRequest, TurnResponse
from persona_runner.engine import aire_route, turn_jobs

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
    return await aire_route.turn_via_aire(req)


@router.post("/v1/turn/jobs", response_model=TurnJobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def submit_turn_job(req: TurnRequest, authorization: str | None = Header(default=None)) -> TurnJobAccepted:
    """Arranca el turno en background y devuelve su boleto."""
    check_auth(authorization)
    job = turn_jobs.submit(req, runner=aire_route.turn_via_aire)
    return TurnJobAccepted(job_id=job.ticket_id)


@router.get("/v1/turn/jobs/{job_id}", response_model=TurnJobStatus)
async def poll_turn_job(
    job_id: str,
    authorization: str | None = Header(default=None),
    wait_s: float = Query(default=turn_jobs.MAX_WAIT_S, ge=0.0),
) -> TurnJobStatus:
    """Long-poll acotado del boleto.

    404 = el trabajo no existe (o el runner se reinició con él adentro), que es
    la misma señal de "el cerebro se cayó" que el cliente ya sabe leer. Un fallo
    del turno sale con la misma forma que en el camino síncrono, porque la
    excepción se re-lanza aquí y la mapea el mismo handler.
    """
    check_auth(authorization)
    job = turn_jobs.JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"unknown turn job {job_id!r}")
    done, response = await turn_jobs.JOBS.wait(job, wait_s)
    if not done:
        return TurnJobStatus(job_id=job_id, status="running")
    turn_jobs.JOBS.drop(job_id)
    return TurnJobStatus(job_id=job_id, status="done", response=response)
