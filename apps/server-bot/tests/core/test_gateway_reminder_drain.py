"""Gateway reminder drain — the persisted [REMIND:] row finally FIRES.

THE BUG this locks out: `[REMIND:]` parsed and persisted (4cdd0d8) but NOTHING
delivered it — the row sat mute in Postgres forever and "te lo recuerdo a las 8"
was a lie. This suite drives `PersonaClient._reminder_drain` directly.

Positive (a due reminder lands in its channel and is retired) + resistance: it
does NOT fire twice, a future one is untouched, a send that explodes doesn't stop
the batch, and a sibling's reminder is never this persona's to deliver.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona


def _persona(persona_id: str = "vultur") -> Persona:
    return Persona(
        persona_id=persona_id,
        display_name=persona_id.capitalize(),
        persona_file=f"{persona_id}.md",
        token_env=f"{persona_id.upper()}_DISCORD_TOKEN",
    )


def _reminder(**over) -> dict:
    base = {
        "id": 7,
        "channel_id": "1489180895264116736",
        "guild_id": "G1",
        "created_by": "907264175246569543",
        "description": "sacar la ropa de la lavadora",
        "remind_at": time.time() - 60,
        "mention_user_ids": "907264175246569543",
        "recurring": "none",
        "requires_ack": False,
        "persona_id": "vultur",
    }
    base.update(over)
    return base


def _client(pending: list[dict], *, persona_id: str = "vultur", reply: str = "Tu ropa lleva 20 minutos pudriéndose."):
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.mark_reminder_delivered = AsyncMock()
    memory.update_reminder_time = AsyncMock()

    async def _get_pending(now, persona_id=None):
        return [r for r in pending if r["remind_at"] <= now and (persona_id is None or r["persona_id"] == persona_id)]

    memory.get_pending_reminders = AsyncMock(side_effect=_get_pending)

    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply, model_used="claude"))

    client = PersonaClient(_persona(persona_id), memory, agent_client, intents=discord.Intents.none())
    channel = MagicMock()
    channel.send = AsyncMock()
    client.get_channel = MagicMock(return_value=channel)
    return client, memory, channel


def _sent(channel) -> str:
    return " ".join(str(c) for c in channel.send.call_args_list)


async def test_due_reminder_is_delivered_and_marked_delivered():
    client, memory, channel = _client([_reminder()])

    await client._reminder_drain()

    assert channel.send.await_count >= 1
    assert "pudriéndose" in _sent(channel)
    assert "<@907264175246569543>" in _sent(channel)
    memory.mark_reminder_delivered.assert_awaited_once_with(7)


async def test_delivered_reminder_is_not_redelivered_next_tick():
    """RESISTENCIA: the retired row must never fire twice."""
    pending = [_reminder()]
    client, memory, channel = _client(pending)

    await client._reminder_drain()
    first = channel.send.await_count

    # The repo no longer returns it once delivered=1 — model that.
    pending.clear()
    await client._reminder_drain()

    assert channel.send.await_count == first
    assert memory.mark_reminder_delivered.await_count == 1


async def test_future_reminder_is_not_touched():
    """RESISTENCIA: not due yet → no send, no state change."""
    client, memory, channel = _client([_reminder(remind_at=time.time() + 3600)])

    await client._reminder_drain()

    channel.send.assert_not_awaited()
    memory.mark_reminder_delivered.assert_not_awaited()


async def test_failing_send_does_not_break_the_rest_of_the_batch():
    """RESISTENCIA: a dead channel / revoked permission kills ONE reminder, not the loop."""
    client, memory, channel = _client([_reminder(id=1), _reminder(id=2)])
    ok_channel = MagicMock()
    ok_channel.send = AsyncMock()
    broken = MagicMock()
    broken.send = AsyncMock(side_effect=discord.HTTPException(MagicMock(status=403), "forbidden"))
    client.get_channel = MagicMock(side_effect=[broken, ok_channel])

    await client._reminder_drain()

    ok_channel.send.assert_awaited()
    # The exploding one stays pending (retried later); the healthy one is retired.
    memory.mark_reminder_delivered.assert_awaited_once_with(2)


async def test_sibling_reminder_is_never_delivered_by_this_persona():
    """RESISTENCIA: Vultur does NOT deliver the reminder Insult agendó."""
    client, memory, channel = _client([_reminder(id=9, persona_id="insult")], persona_id="vultur")

    await client._reminder_drain()

    memory.get_pending_reminders.assert_awaited_once()
    assert memory.get_pending_reminders.await_args.kwargs["persona_id"] == "vultur"
    channel.send.assert_not_awaited()
    memory.mark_reminder_delivered.assert_not_awaited()


async def test_recurring_reminder_is_rescheduled_not_retired():
    client, memory, channel = _client([_reminder(recurring="daily")])

    await client._reminder_drain()

    channel.send.assert_awaited()
    memory.mark_reminder_delivered.assert_not_awaited()
    memory.update_reminder_time.assert_awaited_once()
    reminder_id, next_at = memory.update_reminder_time.await_args.args
    assert reminder_id == 7
    assert next_at > time.time()


async def test_runner_failure_still_delivers_the_reminder_content():
    """A dead runner may not swallow the promise: the plain fallback still sends."""
    client, memory, channel = _client([_reminder()])
    client.agent_client.chat = AsyncMock(side_effect=RuntimeError("runner down"))

    await client._reminder_drain()

    assert "sacar la ropa de la lavadora" in _sent(channel)
    memory.mark_reminder_delivered.assert_awaited_once_with(7)
