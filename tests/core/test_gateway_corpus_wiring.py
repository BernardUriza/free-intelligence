"""Corpus en el turn path — los dos hallazgos del cruel-critic 2026-07-16.

#1: el invite path (EL path principal post-purga: el host rutea los turnos sin
mención) debe llevar el corpus de la persona, keyed por el reason del ruteo.
#2: orden es seguridad — corpus PRIMERO, guidance del guardián AL FINAL; el
overlay de usuario vulnerable jamás queda sepultado bajo erudición.

Mutator rule: positivos (invite lleva corpus; el orden corpus→guardián) +
resistencia (fault del corpus → turno vive sin bloque; sin corpus → guidance
intacta).
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


def _invite_channel():
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    channel.typing = MagicMock(return_value=_Typing())
    trigger = MagicMock()
    trigger.attachments = []
    channel.fetch_message = AsyncMock(return_value=trigger)
    return channel


_CORPUS_BLOCK = "REFERENCIAS DE TEORÍA CINEMATOGRÁFICA:\n- el plano como unidad moral"


async def _invite(client: PersonaClient, channel, reason: str) -> None:
    with patch.object(client, "get_channel", return_value=channel):
        await client.respond_to_invite(
            channel_id="1489180895264116736",
            guild_id="G1",
            channel_name="general",
            reason=reason,
            invited_by="host_router",
            trigger_message_id="42",
        )
        await asyncio.sleep(0)


async def test_invite_turn_carries_the_persona_corpus():
    """#1 positivo: el invite recupera corpus con el reason como query y lo
    manda como behavioral_guidance al runner."""
    client = _client()
    channel = _invite_channel()
    with patch(
        "persona_gateway.gateway.build_persona_corpus_block",
        new=AsyncMock(return_value=_CORPUS_BLOCK),
    ) as mock_corpus:
        await _invite(client, channel, reason="bernard2389: «que opinas de Mulholland Drive»")
    assert mock_corpus.await_args.kwargs["query"] == "bernard2389: «que opinas de Mulholland Drive»"
    guidance = client.agent_client.chat.await_args.kwargs["behavioral_guidance"]
    assert guidance == _CORPUS_BLOCK


async def test_invite_corpus_fault_ships_turn_without_block():
    """#1 resistencia: el corpus truena → el invite vive, guidance=None."""
    client = _client()
    channel = _invite_channel()
    with patch(
        "persona_gateway.gateway.build_persona_corpus_block",
        new=AsyncMock(side_effect=RuntimeError("pg caído")),
    ):
        await _invite(client, channel, reason="ven a opinar")
    client.agent_client.chat.assert_awaited_once()
    assert client.agent_client.chat.await_args.kwargs["behavioral_guidance"] is None


async def test_corpus_rides_before_guardian_guidance():
    """#2 positivo: corpus PRIMERO, overlay del guardián AL FINAL del bloque."""
    client = _client()
    with patch(
        "persona_gateway.gateway.build_persona_corpus_block",
        new=AsyncMock(return_value=_CORPUS_BLOCK),
    ):
        merged = await client._append_corpus_block("OVERLAY VULNERABLE: calidez y líneas de crisis", "ask")
    assert merged is not None
    assert merged.index(_CORPUS_BLOCK) < merged.index("OVERLAY VULNERABLE")
    assert merged.endswith("OVERLAY VULNERABLE: calidez y líneas de crisis")


async def test_no_corpus_leaves_guidance_untouched():
    """#2 resistencia: sin hit de corpus la guidance del guardián pasa intacta."""
    client = _client()
    with patch(
        "persona_gateway.gateway.build_persona_corpus_block",
        new=AsyncMock(return_value=None),
    ):
        merged = await client._append_corpus_block("OVERLAY", "ask")
    assert merged == "OVERLAY"
