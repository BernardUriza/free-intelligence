"""Gateway agenda drain — the standing agenda wakes, pursues, and posts UNPROMPTED.

Drives `PersonaClient._agenda_check` directly, mirroring the reminder-drain
canonical suite. The fake repo models cadence state (a ran agenda stops being
due), so breaking `mark_agenda_ran` in the worker turns the no-re-run test red
instead of passing on a hand-cleared list.

Positive (a due agenda is pursued and the finding lands in its channel) +
resistance: it does NOT re-run once marked ran, the NADA sentinel keeps the
persona quiet, a runner failure does NOT advance the cadence, a delivery
failure doesn't kill the batch, and a sibling's agenda is never pursued.
"""

from __future__ import annotations

import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from persona_gateway.config import CONFIG
from persona_gateway.gateway import PersonaClient
from persona_gateway.workers import agenda as agenda_worker
from shared.personas import Persona
from shared.time_context import MEXICO_CITY_TZ


@pytest.fixture(autouse=True)
def _daytime_clock(monkeypatch):
    """Freeze the worker's clock inside the waking window for EVERY test here.

    `AgendaWorker.drain` gained a daytime gate (Vultur poking at 02:39 CDMX) and
    reads the real wall clock, so this whole suite silently became time-of-day
    dependent: run it after `agenda_daytime_end` and all 11 tests fail on
    `agenda_outside_daytime_window`, having never reached the code they assert
    on. CI stayed green only because it happened to run during the day — a red
    that waits for nightfall is worse than a red you can see. The window itself
    is covered by `tests/test_agenda_worker_window.py`; here it must never be
    the variable, so the clock is pinned (same monkeypatch shape as that suite).
    """
    monkeypatch.setattr(
        agenda_worker,
        "now_in_mexico_city",
        lambda: datetime(2026, 7, 27, 13, 0, tzinfo=MEXICO_CITY_TZ),
    )


def _persona(persona_id: str = "vultur") -> Persona:
    return Persona(
        persona_id=persona_id,
        display_name=persona_id.capitalize(),
        persona_file=f"{persona_id}.md",
        token_env=f"{persona_id.upper()}_DISCORD_TOKEN",
    )


def _agenda(**over) -> dict:
    base = {
        "id": 3,
        "channel_id": "1489180895264116736",
        "guild_id": "G1",
        "created_by": "907264175246569543",
        "goal": "vigilar estrenos de A24 dignos de mención",
        "due_at": time.time() - 60,
        "persona_id": "vultur",
    }
    base.update(over)
    return base


def _client(
    pending: list[dict],
    *,
    persona_id: str = "vultur",
    reply: str = "A24 anunció una nueva de Ari Aster y sí importa.",
):
    memory = MagicMock()
    ran: set[int] = set()

    async def _mark_ran(agenda_id, ts):
        ran.add(agenda_id)

    async def _get_due(now, limit, persona_id=None):
        rows = [a for a in pending if a["id"] not in ran and a["due_at"] <= now and a["persona_id"] == persona_id]
        return rows[:limit]

    memory.store = AsyncMock()
    memory.mark_agenda_ran = AsyncMock(side_effect=_mark_ran)
    memory.get_due_agendas = AsyncMock(side_effect=_get_due)

    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply, model_used="claude"))

    client = PersonaClient(_persona(persona_id), memory, agent_client, intents=discord.Intents.none())
    channel = MagicMock()
    channel.send = AsyncMock()
    client.get_channel = MagicMock(return_value=channel)
    return client, memory, channel


def _sent(channel) -> str:
    return " ".join(str(c) for c in channel.send.call_args_list)


async def test_due_agenda_is_pursued_and_finding_posted():
    client, memory, channel = _client([_agenda()])

    await client._agenda_check()

    assert channel.send.await_count >= 1
    assert "A24" in _sent(channel)
    agenda_id, ts = memory.mark_agenda_ran.await_args.args
    assert agenda_id == 3
    assert ts <= time.time()
    memory.store.assert_awaited_once()


async def test_agenda_runs_in_isolated_session_and_markers_are_stripped():
    """The pursuit must not pollute the live channel thread, and a [REACT:] in
    an unprompted post has no message to act on — it must never leak."""
    client, memory, channel = _client([_agenda()], reply="Hay estreno nuevo. [REACT:👀] Míralo.")

    await client._agenda_check()

    kwargs = client.agent_client.chat.await_args.kwargs
    assert kwargs["channel_id"] == "agenda-3"
    assert kwargs["persona_id"] == "vultur"
    assert kwargs["timeout_s"] == CONFIG.agenda_timeout_s
    assert "[REACT:" not in _sent(channel)
    assert "Hay estreno nuevo." in _sent(channel)


async def test_ran_agenda_is_not_rerun_next_tick():
    """RESISTENCIA: once marked ran, the cadence gate holds — no double pursuit."""
    client, memory, channel = _client([_agenda()])

    await client._agenda_check()
    first = channel.send.await_count

    await client._agenda_check()

    assert client.agent_client.chat.await_count == 1
    assert channel.send.await_count == first
    assert memory.mark_agenda_ran.await_count == 1


@pytest.mark.parametrize("reply", ["NADA", "nada.", '"NADA"', ""])
async def test_nothing_new_stays_quiet_but_cadence_advances(reply):
    """RESISTENCIA: the NADA sentinel gates the spam — no post, no store, yet
    the agenda is marked ran so it waits its full cadence."""
    client, memory, channel = _client([_agenda()], reply=reply)

    await client._agenda_check()

    channel.send.assert_not_awaited()
    memory.store.assert_not_awaited()
    memory.mark_agenda_ran.assert_awaited_once()


async def test_empty_queue_is_a_silent_noop():
    client, memory, channel = _client([])

    await client._agenda_check()

    client.agent_client.chat.assert_not_awaited()
    channel.send.assert_not_awaited()
    memory.mark_agenda_ran.assert_not_awaited()


async def test_not_due_agenda_is_untouched():
    """RESISTENCIA: not due yet → no pursuit, no state change."""
    client, memory, channel = _client([_agenda(due_at=time.time() + 3600)])

    await client._agenda_check()

    client.agent_client.chat.assert_not_awaited()
    channel.send.assert_not_awaited()
    memory.mark_agenda_ran.assert_not_awaited()


async def test_runner_failure_does_not_advance_cadence():
    """RESISTENCIA: a transport failure leaves the agenda due — retried next
    tick, never silently swallowed by an advanced cadence."""
    client, memory, channel = _client([_agenda()])
    client.agent_client.chat = AsyncMock(side_effect=RuntimeError("runner down"))

    await client._agenda_check()

    channel.send.assert_not_awaited()
    memory.mark_agenda_ran.assert_not_awaited()

    await client._agenda_check()

    assert client.agent_client.chat.await_count == 2


async def test_failing_delivery_does_not_break_the_batch():
    """RESISTENCIA: a dead channel kills ONE posting, not the loop."""
    client, memory, channel = _client([_agenda(id=1), _agenda(id=2)])
    broken = MagicMock()
    broken.send = AsyncMock(side_effect=discord.HTTPException(MagicMock(status=403), "forbidden"))
    ok_channel = MagicMock()
    ok_channel.send = AsyncMock()
    client.get_channel = MagicMock(side_effect=[broken, ok_channel])

    await client._agenda_check()

    ok_channel.send.assert_awaited()
    assert memory.mark_agenda_ran.await_count == 2


async def test_sibling_agenda_is_never_pursued_by_this_persona():
    """RESISTENCIA: Vultur does NOT pursue the agenda Insult registró."""
    client, memory, channel = _client([_agenda(id=9, persona_id="insult")], persona_id="vultur")

    await client._agenda_check()

    assert memory.get_due_agendas.await_args.kwargs["persona_id"] == "vultur"
    client.agent_client.chat.assert_not_awaited()
    channel.send.assert_not_awaited()
    memory.mark_agenda_ran.assert_not_awaited()


async def test_channel_gone_advances_cadence_without_running():
    client, memory, channel = _client([_agenda()])
    client.get_channel = MagicMock(return_value=None)

    await client._agenda_check()

    client.agent_client.chat.assert_not_awaited()
    agenda_id, _ = memory.mark_agenda_ran.await_args.args
    assert agenda_id == 3


async def test_fetch_failure_is_survived_silently():
    client, memory, channel = _client([_agenda()])
    memory.get_due_agendas = AsyncMock(side_effect=RuntimeError("pg down"))

    await client._agenda_check()

    client.agent_client.chat.assert_not_awaited()
    channel.send.assert_not_awaited()
