"""The invite path is guarded — a fault never leaves the persona mute.

2026-07-23: `/invite` scheduled `respond_to_invite` as a bare `create_task`, so
a runner 422 died as "Task exception was never retrieved" and the user's voice
note got NO reply at all. `_dispatch` had guarded the @mention path since day
one; the path the host cutover made THE path had nothing.

Mutator rule: positive (a turn fault still sends the neutral "…") + resistance
(a healthy invite is untouched, and a channel that can't be resolved does not
raise out of the guard).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona

CHANNEL_ID = "1489180895264116736"


def _client() -> PersonaClient:
    persona = Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[])
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text="ok", model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


def _channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    return channel


async def _dispatch(client: PersonaClient) -> None:
    await client.dispatch_invite(
        channel_id=CHANNEL_ID,
        guild_id="G1",
        channel_name="general",
        reason="bernard2389: «[adjuntó: voice-message.ogg]»",
        invited_by="host",
        trigger_message_id="1527198401375113227",
    )


async def test_invite_fault_sends_the_neutral_recovery():
    client = _client()
    channel = _channel()
    with (
        patch.object(
            PersonaClient,
            "respond_to_invite",
            new=AsyncMock(side_effect=RuntimeError("runner 422: string_too_long")),
        ),
        patch("persona_gateway.gateway.resolve_messageable", new=AsyncMock(return_value=channel)),
    ):
        await _dispatch(client)
    channel.send.assert_awaited_once_with("…")


async def test_healthy_invite_sends_no_recovery():
    client = _client()
    channel = _channel()
    with (
        patch.object(PersonaClient, "respond_to_invite", new=AsyncMock(return_value=None)),
        patch("persona_gateway.gateway.resolve_messageable", new=AsyncMock(return_value=channel)),
    ):
        await _dispatch(client)
    channel.send.assert_not_awaited()


async def test_invite_fault_with_unresolvable_channel_does_not_raise():
    client = _client()
    with (
        patch.object(PersonaClient, "respond_to_invite", new=AsyncMock(side_effect=RuntimeError("boom"))),
        patch("persona_gateway.gateway.resolve_messageable", new=AsyncMock(return_value=None)),
    ):
        await _dispatch(client)
