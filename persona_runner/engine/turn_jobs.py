"""Turnos con boleto en el runner — `khimeras_shared.tickets` aplicado a `/v1/turn`.

El porqué vive en ese módulo (el ingress corta a los 240 s; un turno de Vultur
tardó 326.9 s y se tiró). Aquí solo se nombra el registro y se fija el tipo.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from khimeras_shared.tickets import MAX_WAIT_S, Ticket, TicketRegistry
from persona_runner.core.schemas import TurnRequest, TurnResponse

__all__ = ["JOBS", "MAX_WAIT_S", "TurnJob", "submit"]

type TurnJob = Ticket[TurnResponse]

JOBS: TicketRegistry[TurnResponse] = TicketRegistry("turn-job")


def submit(req: TurnRequest, *, runner: Callable[[TurnRequest], Awaitable[TurnResponse]]) -> TurnJob:
    """Arranca el turno en background y devuelve su boleto.

    `runner` es la corrutina que corre el turno (`aire_route.turn_via_aire`),
    inyectada para que las pruebas no tengan que levantar AIRE.
    """
    label = f"{req.persona_id or 'insult'}:{req.channel_id}"
    return JOBS.submit(runner(req), label=label, ticket_id=req.job_id)
