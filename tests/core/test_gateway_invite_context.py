"""El invite path recibe el MISMO turn assembly que `_handle`.

El agujero 2026-07-19 (tercera aparición de la clase c0-r9): guardián,
reminders, relevant, other-people, fact extraction y vision estaban cableados
SOLO al path de @mención — que el cutover del host acababa de dejar sin
tráfico. El path primario (invite) corría con corpus y nada más, y pasaba el
id del BOT como user_id, así que el runner reconstruía facts de nadie.

Regla del mutador: positivo (trigger humano → guardián con SU user_id,
relevant cargado, other_people en el wire, extracción y visión disparadas) +
resistencia (trigger de bot o sin trigger → cero guardián, cero crash, el
turno entrega igual que antes).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona

SUBJECT_ID = 907264175246569543
BOT_ID = 1503983124982534284


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _client(reply_text: str = "Aquí estoy.") -> PersonaClient:
    persona = Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[{"user_name": "alex", "content": "hola", "role": "user"}])
    memory.search = AsyncMock(return_value=[])
    memory.build_context = MagicMock(side_effect=lambda recent, **kw: list(recent))
    memory.search_facts_semantic = AsyncMock(return_value=[])
    memory.list_pending_reminders = AsyncMock(return_value=[])
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply_text, model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


def _invite_channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    channel.typing = MagicMock(return_value=_Typing())
    channel.fetch_message = AsyncMock()
    return channel


def _human_trigger(content: str = "me siento fatal hoy"):
    trigger = MagicMock()
    trigger.id = 1527198401375113227
    trigger.content = content
    trigger.attachments = []
    trigger.flags = MagicMock(voice=False)
    trigger.author = SimpleNamespace(id=SUBJECT_ID, bot=False, display_name="bernard2389")
    return trigger


async def _invite(client: PersonaClient, channel, *, trigger_message_id="1527198401375113227"):
    with patch.object(client, "get_channel", return_value=channel):
        await client.respond_to_invite(
            channel_id="1489180895264116736",
            guild_id="G1",
            channel_name="general",
            reason="bernard2389 suena mal; espejo empático",
            invited_by="host",
            trigger_message_id=trigger_message_id,
        )
        await asyncio.sleep(0)


async def test_invite_runs_guardian_for_the_trigger_author():
    client = _client()
    channel = _invite_channel()
    channel.fetch_message.return_value = _human_trigger()
    with patch(
        "persona_core.turn.context.guidance_for_turn", new=AsyncMock(return_value="OVERLAY VULNERABLE")
    ) as guardian:
        await _invite(client, channel)
    guardian.assert_awaited_once()
    kwargs = guardian.await_args.kwargs
    assert kwargs["user_id"] == str(SUBJECT_ID)
    assert kwargs["current_message"] == "me siento fatal hoy"
    sent_guidance = client.agent_client.chat.await_args.kwargs["behavioral_guidance"]
    assert "OVERLAY VULNERABLE" in sent_guidance


async def test_invite_forwards_the_subject_user_id_not_the_bots():
    client = _client()
    channel = _invite_channel()
    channel.fetch_message.return_value = _human_trigger()
    await _invite(client, channel)
    assert client.agent_client.chat.await_args.kwargs["user_id"] == str(SUBJECT_ID)


async def test_invite_loads_relevant_and_merges_context():
    client = _client()
    channel = _invite_channel()
    channel.fetch_message.return_value = _human_trigger()
    await _invite(client, channel)
    client.memory.search.assert_awaited_once()
    assert client.memory.search.await_args.args[1] == "me siento fatal hoy"
    client.memory.build_context.assert_called_once()


async def test_invite_ships_other_people_on_the_wire():
    client = _client()
    channel = _invite_channel()
    channel.fetch_message.return_value = _human_trigger()
    with patch(
        "persona_core.turn.context.other_people_block_for_turn", new=AsyncMock(return_value="OTROS: alex…")
    ) as block:
        await _invite(client, channel)
    assert block.await_args.kwargs["exclude_user_id"] == str(SUBJECT_ID)
    assert client.agent_client.chat.await_args.kwargs["other_people"] == "OTROS: alex…"


async def test_invite_spawns_fact_extraction_for_the_subject():
    client = _client()
    channel = _invite_channel()
    channel.fetch_message.return_value = _human_trigger()
    with patch.object(client, "_spawn_fact_extraction") as spawn:
        await _invite(client, channel)
    spawn.assert_called_once()
    assert spawn.call_args.args[0] == str(SUBJECT_ID)
    assert spawn.call_args.args[2][-1]["content"] == "me siento fatal hoy"


async def test_bot_trigger_author_never_runs_the_guardian():
    client = _client()
    channel = _invite_channel()
    trigger = _human_trigger()
    trigger.author = SimpleNamespace(id=999, bot=True, display_name="Vultur")
    channel.fetch_message.return_value = trigger
    with (
        patch("persona_core.turn.context.guidance_for_turn", new=AsyncMock()) as guardian,
        patch.object(client, "_spawn_fact_extraction") as spawn,
    ):
        await _invite(client, channel)
    guardian.assert_not_awaited()
    spawn.assert_not_called()
    assert client.agent_client.chat.await_args.kwargs["user_id"] != "999"


async def test_invite_without_trigger_still_delivers_without_guardian():
    client = _client("Llego sin trigger.")
    channel = _invite_channel()
    with patch("persona_core.turn.context.guidance_for_turn", new=AsyncMock()) as guardian:
        await _invite(client, channel, trigger_message_id=None)
    guardian.assert_not_awaited()
    sent = " ".join(str(c) for c in channel.send.call_args_list)
    assert "Llego sin trigger." in sent
