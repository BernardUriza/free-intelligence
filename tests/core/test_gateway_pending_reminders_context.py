"""Pending reminders ON THE WIRE — the persona can only list/cancel what it sees.

`TurnContextBuilder.append_pending_reminders` merges the asking user's pending rows (owned by THIS
persona) into the turn guidance. Contract mirrored from `TurnContextBuilder.append_corpus_block`:
the block rides BEFORE the guidance (the guardian overlay stays last), the merge
never crosses MAX_GUIDANCE_CHARS (the block is dropped whole), and every fault —
dead store, missing facade method — returns the guidance untouched, never a mute
turn. The `_handle` wire test proves the block actually leaves the process.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from persona_core.guidance import MAX_GUIDANCE_CHARS
from persona_gateway.gateway import PersonaClient
from persona_gateway.turn_context import PENDING_REMINDERS_MAX
from shared.personas import Persona

PENDING = [
    {"id": 7, "description": "sacar la ropa de la lavadora", "remind_at": 1900000000.0, "recurring": "none"},
    {"id": 9, "description": "tomar el ARV", "remind_at": 1900003600.0, "recurring": "daily"},
]


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _client(pending, *, raise_listing: bool = False) -> PersonaClient:
    persona = Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[])
    memory.get_facts = AsyncMock(return_value=[])
    memory.get_auto_facts = AsyncMock(return_value=[])
    memory.list_pending_reminders = AsyncMock(
        side_effect=RuntimeError("pg down") if raise_listing else None, return_value=pending
    )
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text="respuesta", model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


def _message(text: str) -> MagicMock:
    msg = MagicMock()
    msg.id = 1526655478313127987
    msg.content = text
    msg.channel = MagicMock(spec=discord.TextChannel)
    msg.channel.id = 1489180895264116736
    msg.channel.send = AsyncMock()
    msg.channel.typing = MagicMock(return_value=_Typing())
    msg.author = MagicMock()
    msg.author.id = 907264175246569543
    msg.author.display_name = "Bernard"
    msg.author.bot = False
    msg.guild = None
    msg.attachments = []
    msg.flags.voice = False
    return msg


# --------------------------------------------------------------------------
# append_pending_reminders — the merge contract
# --------------------------------------------------------------------------


async def test_block_lists_descriptions_and_rides_before_the_guidance():
    client = _client(PENDING)

    merged = await client._context.append_pending_reminders("OVERLAY VULNERABLE: calidez", "U1")

    assert merged is not None
    assert "sacar la ropa de la lavadora" in merged
    assert "tomar el ARV" in merged and "(daily)" in merged
    assert "[REMIND_CANCEL:" in merged  # the persona learns HOW to cancel
    assert merged.endswith("OVERLAY VULNERABLE: calidez")  # safety stays last
    client.memory.list_pending_reminders.assert_awaited_once_with("U1", "vultur")


async def test_no_pending_rows_leaves_guidance_untouched():
    client = _client([])

    assert await client._context.append_pending_reminders("GUIDANCE", "U1") == "GUIDANCE"


async def test_block_alone_when_there_is_no_guidance():
    client = _client(PENDING)

    merged = await client._context.append_pending_reminders(None, "U1")

    assert merged and "sacar la ropa" in merged


async def test_dead_store_returns_guidance_untouched():
    """RESISTANCE: the listing is a nicety; the turn (and its safety guidance)
    must survive a dead reminders table without noticing."""
    client = _client(PENDING, raise_listing=True)

    assert await client._context.append_pending_reminders("GUIDANCE", "U1") == "GUIDANCE"


async def test_near_cap_guidance_drops_the_block_whole():
    """CAP IS SAFETY: the merge must never push guidance past the runner's 422
    threshold — the block yields, the guidance survives byte-identical."""
    client = _client(PENDING)
    near_cap = "G" * (MAX_GUIDANCE_CHARS - 10)

    assert await client._context.append_pending_reminders(near_cap, "U1") == near_cap


async def test_row_count_is_capped():
    many = [
        {"id": i, "description": f"pendiente {i}", "remind_at": 1900000000.0 + i, "recurring": "none"}
        for i in range(PENDING_REMINDERS_MAX + 5)
    ]
    client = _client(many)

    merged = await client._context.append_pending_reminders(None, "U1")

    assert merged is not None
    assert f"pendiente {PENDING_REMINDERS_MAX - 1}" in merged
    assert f"pendiente {PENDING_REMINDERS_MAX}" not in merged


# --------------------------------------------------------------------------
# _handle — the block leaves the process
# --------------------------------------------------------------------------


async def test_handle_ships_the_pending_block_in_behavioral_guidance():
    client = _client(PENDING)

    await client._handle(_message("qué recordatorios tengo?"))

    client.agent_client.chat.assert_awaited_once()
    guidance = client.agent_client.chat.await_args.kwargs.get("behavioral_guidance")
    assert guidance and "sacar la ropa de la lavadora" in guidance


async def test_handle_survives_a_dead_listing_and_still_ships_the_turn():
    client = _client(PENDING, raise_listing=True)

    await client._handle(_message("hola"))

    client.agent_client.chat.assert_awaited_once()
    guidance = client.agent_client.chat.await_args.kwargs.get("behavioral_guidance")
    assert not guidance or "sacar la ropa" not in guidance
