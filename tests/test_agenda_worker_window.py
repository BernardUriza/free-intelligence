"""`AgendaWorker.drain` respects waking hours — an unprompted poke at 03:00 is a defect.

Vultur's agenda #1 asked, in its own goal, for "horario diurno razonable, no en
madrugada", then posted at 02:39 CDMX (2026-07-25) and 02:57 CDMX (2026-07-27).
`cadence_hours` alone can never fix that: a 24h cadence first due at 03:00 stays
at 03:00 forever.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from persona_gateway.workers import agenda as agenda_worker
from shared.time_context import MEXICO_CITY_TZ

pytestmark = pytest.mark.asyncio


def _worker(memory) -> agenda_worker.AgendaWorker:
    return agenda_worker.AgendaWorker(
        persona=SimpleNamespace(persona_id="vultur", display_name="Vultur"),
        memory=memory,
        agent_client=AsyncMock(),
    )


def _clock(monkeypatch, hour: int) -> None:
    monkeypatch.setattr(
        agenda_worker,
        "now_in_mexico_city",
        lambda: datetime(2026, 7, 27, hour, 57, tzinfo=MEXICO_CITY_TZ),
    )


async def test_the_three_am_wake_never_even_reaches_the_database(monkeypatch):
    memory = SimpleNamespace(get_due_agendas=AsyncMock(return_value=[]))
    _clock(monkeypatch, 2)

    await _worker(memory).drain(host=SimpleNamespace())

    memory.get_due_agendas.assert_not_awaited()


async def test_a_daytime_cycle_still_checks_what_is_due(monkeypatch):
    memory = SimpleNamespace(get_due_agendas=AsyncMock(return_value=[]))
    _clock(monkeypatch, 13)

    await _worker(memory).drain(host=SimpleNamespace())

    memory.get_due_agendas.assert_awaited_once()


async def test_a_blocked_cycle_leaves_the_agenda_due_for_the_morning(monkeypatch):
    """RESISTANCE: the quiet window must DEFER the agenda, never consume it."""
    memory = SimpleNamespace(
        get_due_agendas=AsyncMock(return_value=[]),
        mark_agenda_ran=AsyncMock(),
    )
    _clock(monkeypatch, 4)

    await _worker(memory).drain(host=SimpleNamespace())

    memory.mark_agenda_ran.assert_not_awaited()
