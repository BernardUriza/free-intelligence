"""El invite path persiste el turno HUMANO — hallazgo 2026-07-19.

Post-cutover el invite es EL path (el host rutea todo #general), pero heredó el
supuesto del /invite proactivo original: "no hay mensaje de usuario que guardar".
Resultado medido en prod: CERO user rows en #general desde el cutover (07-15) —
la memoria longitudinal solo registraba la mitad de las personas, y el append de
vision (keyed por discord_message_id del mensaje del user) no tenía fila donde
aterrizar.

Mutator rule: positivo (el trigger humano se guarda como role=user con su
discord_message_id) + resistencia (trigger de un BOT no se guarda; un store
caído no mata el turno; trigger vacío no genera fila).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _client(reply_text: str = "Dictamen.") -> PersonaClient:
    persona = Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[])
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply_text, model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


def _invite_channel(*, author_is_bot: bool = False, content: str = "que opinas de Hereditary?"):
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    channel.typing = MagicMock(return_value=_Typing())
    trigger = MagicMock()
    trigger.id = 4242
    trigger.content = content
    trigger.attachments = []
    trigger.author = MagicMock()
    trigger.author.id = 907
    trigger.author.bot = author_is_bot
    trigger.author.display_name = "bernard2389"
    channel.fetch_message = AsyncMock(return_value=trigger)
    return channel


async def _invite(client: PersonaClient, channel, reason: str = "bernard2389: «opina»") -> None:
    with patch.object(client, "get_channel", return_value=channel):
        await client.respond_to_invite(
            channel_id="1489180895264116736",
            guild_id="G1",
            channel_name="general",
            reason=reason,
            invited_by="host_router",
            trigger_message_id="4242",
        )
        await asyncio.sleep(0)


def _user_stores(client: PersonaClient) -> list:
    return [c for c in client.memory.store.await_args_list if c.args[3] == "user"]


async def test_invite_stores_the_human_trigger_as_user_turn():
    client = _client()
    channel = _invite_channel()

    await _invite(client, channel)

    stores = _user_stores(client)
    assert len(stores) == 1
    call = stores[0]
    assert call.args[0] == "1489180895264116736"
    assert call.args[1] == "907"
    assert call.args[2] == "bernard2389"
    assert call.args[4] == "que opinas de Hereditary?"
    assert call.kwargs["discord_message_id"] == "4242"


async def test_invite_user_store_lands_before_the_assistant_store():
    """La fila del user debe existir cuando vision/el assistant store corran —
    el orden es el contrato que hace aterrizar el append por discord_message_id."""
    client = _client()
    channel = _invite_channel()

    await _invite(client, channel)

    roles = [c.args[3] for c in client.memory.store.await_args_list]
    assert roles.index("user") < roles.index("assistant")


async def test_bot_trigger_is_not_stored_as_user_turn():
    """RESISTENCIA: un trigger escrito por otro bot no es memoria de usuario."""
    client = _client()
    channel = _invite_channel(author_is_bot=True)

    await _invite(client, channel)

    assert _user_stores(client) == []


async def test_empty_trigger_is_not_stored():
    """RESISTENCIA: sin texto y sin attachments no hay nada que recordar."""
    client = _client()
    channel = _invite_channel(content="")

    await _invite(client, channel)

    assert _user_stores(client) == []


async def test_user_store_failure_never_kills_the_turn():
    """RESISTENCIA: Postgres caído en el store del user → el turno vive y la
    respuesta sale igual (fail-safe del path principal)."""
    client = _client()
    channel = _invite_channel()

    async def _store(*args, **kwargs):
        if args[3] == "user":
            raise RuntimeError("pg down")
        return None

    client.memory.store = AsyncMock(side_effect=_store)

    await _invite(client, channel)

    client.agent_client.chat.assert_awaited_once()
    channel.send.assert_awaited()
