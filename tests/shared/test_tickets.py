"""`khimeras_shared.tickets` — un trabajo largo detrás de requests cortas.

Positiva: un trabajo que tarda más que un poll sigue vivo entre polls y entrega
su resultado al que pregunta después. Resistencia: la excepción del trabajo
llega tal cual al que pregunta (no se traga ni se disfraza), un id desconocido
es None, y un trabajo recogido se puede borrar sin tumbar a los demás.
"""

from __future__ import annotations

import asyncio

import pytest

from khimeras_shared import tickets
from khimeras_shared.tickets import TicketRegistry


async def _slow(value: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return value


async def _boom() -> str:
    await asyncio.sleep(0)
    raise RuntimeError("el turno tronó")


@pytest.mark.asyncio
async def test_a_job_longer_than_one_poll_survives_between_polls():
    registry: TicketRegistry[str] = TicketRegistry("t")
    ticket = registry.submit(_slow("respuesta", 0.15), label="c1")

    done, result = await registry.wait(ticket, wait_s=0.02)
    assert (done, result) == (False, None)
    assert registry.get(ticket.ticket_id) is ticket  # sigue ahí, sigue corriendo

    done, result = await registry.wait(ticket, wait_s=1.0)
    assert (done, result) == (True, "respuesta")


@pytest.mark.asyncio
async def test_the_jobs_exception_reaches_the_poller_unchanged():
    registry: TicketRegistry[str] = TicketRegistry("t")
    ticket = registry.submit(_boom(), label="c1")
    with pytest.raises(RuntimeError, match="tronó"):
        await registry.wait(ticket, wait_s=1.0)


@pytest.mark.asyncio
async def test_unknown_and_dropped_ids_are_none():
    registry: TicketRegistry[str] = TicketRegistry("t")
    assert registry.get("nope") is None
    ticket = registry.submit(_slow("x", 0), label="c1")
    await registry.wait(ticket, wait_s=1.0)
    registry.drop(ticket.ticket_id)
    assert registry.get(ticket.ticket_id) is None
    assert registry.open() == 0


@pytest.mark.asyncio
async def test_a_finished_job_nobody_collected_is_reaped_after_the_ttl(monkeypatch):
    registry: TicketRegistry[str] = TicketRegistry("t")
    ticket = registry.submit(_slow("x", 0), label="c1")
    await registry.wait(ticket, wait_s=1.0)
    assert registry.open() == 1
    monkeypatch.setattr(tickets, "DONE_TTL_S", 0.0)
    await asyncio.sleep(0.01)
    assert registry.open() == 0


@pytest.mark.asyncio
async def test_a_single_poll_never_waits_longer_than_the_cap():
    registry: TicketRegistry[str] = TicketRegistry("t")
    ticket = registry.submit(_slow("x", 5.0), label="c1")
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    done, _ = await registry.wait(ticket, wait_s=0.05)
    assert done is False
    assert loop.time() - t0 < 1.0
    ticket.task.cancel()
