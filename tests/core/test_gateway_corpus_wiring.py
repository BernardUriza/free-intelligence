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


def _invite_channel(trigger_content: str | None = None):
    """`trigger_content` es lo que el HUMANO escribió en el mensaje que disparó
    el invite.

    Por default NO hay sujeto humano (autor bot), que es el escenario en el que
    el `reason` del router es lo único que queda y el que el resto de este
    archivo asume. Pasar un texto convierte al autor en humano — el caso normal
    post-cutover, y el único donde la query del corpus cambia.
    """
    channel = MagicMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    channel.typing = MagicMock(return_value=_Typing())
    trigger = MagicMock()
    trigger.attachments = []
    if trigger_content is None:
        trigger.author.bot = True
        trigger.content = ""  # un trigger sin texto usable: sólo queda el reason
    else:
        trigger.content = trigger_content
        trigger.author.bot = False
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
    """#1 positivo: el invite lleva el corpus al runner como behavioral_guidance,
    recuperado con LO QUE EL HUMANO DIJO.

    Corregido el 2026-09-09. Este test fijaba `query == reason` —el resumen del
    router— y así consagraba como correcto justo el defecto que
    `tests/arch/test_mention_invite_parity.py` llevaba marcado como
    `xfail(strict)`: la biblioteca de Vultur se recuperaba contra el resumen en
    vez de contra la pregunta, en el camino que lleva todo el tráfico. Dos
    arneses del mismo repo afirmando lo contrario; ganó el que medía el daño.
    """
    client = _client()
    channel = _invite_channel(trigger_content="que opinas de Mulholland Drive")
    with patch(
        "persona_gateway.turn_context.build_persona_corpus_block",
        new=AsyncMock(return_value=_CORPUS_BLOCK),
    ) as mock_corpus:
        await _invite(client, channel, reason="bernard2389 pregunta por una peli")
    assert mock_corpus.await_args.kwargs["query"] == "que opinas de Mulholland Drive"
    guidance = client.agent_client.chat.await_args.kwargs["behavioral_guidance"]
    assert guidance.startswith(_CORPUS_BLOCK), "el corpus dejó de encabezar la guidance del turno"


async def test_invite_falls_back_to_the_reason_when_there_is_no_human_text():
    """#1 resistencia: sin texto humano usable —trigger de bot, o no fetchable—
    el `reason` del router sigue siendo la query. El fix prioriza al humano; no
    lo vuelve un requisito."""
    client = _client()
    channel = _invite_channel()  # sin sujeto humano
    with patch(
        "persona_gateway.turn_context.build_persona_corpus_block",
        new=AsyncMock(return_value=_CORPUS_BLOCK),
    ) as mock_corpus:
        await _invite(client, channel, reason="bernard2389 pregunta por una peli")
    assert mock_corpus.await_args.kwargs["query"] == "bernard2389 pregunta por una peli"


async def test_invite_corpus_fault_ships_turn_without_block():
    """#1 resistencia: el corpus truena → el invite vive, guidance=None."""
    client = _client()
    channel = _invite_channel()
    with patch(
        "persona_gateway.turn_context.build_persona_corpus_block",
        new=AsyncMock(side_effect=RuntimeError("pg caído")),
    ):
        await _invite(client, channel, reason="ven a opinar")
    client.agent_client.chat.assert_awaited_once()
    assert client.agent_client.chat.await_args.kwargs["behavioral_guidance"] is None


async def test_corpus_rides_before_guardian_guidance():
    """#2 positivo: corpus PRIMERO, overlay del guardián AL FINAL del bloque."""
    client = _client()
    with patch(
        "persona_gateway.turn_context.build_persona_corpus_block",
        new=AsyncMock(return_value=_CORPUS_BLOCK),
    ):
        merged = await client._context.append_corpus_block("OVERLAY VULNERABLE: calidez y líneas de crisis", "ask")
    assert merged is not None
    assert merged.index(_CORPUS_BLOCK) < merged.index("OVERLAY VULNERABLE")
    assert merged.endswith("OVERLAY VULNERABLE: calidez y líneas de crisis")


async def test_no_corpus_leaves_guidance_untouched():
    """#2 resistencia: sin hit de corpus la guidance del guardián pasa intacta."""
    client = _client()
    with patch(
        "persona_gateway.turn_context.build_persona_corpus_block",
        new=AsyncMock(return_value=None),
    ):
        merged = await client._context.append_corpus_block("OVERLAY", "ask")
    assert merged == "OVERLAY"


async def test_merge_never_exceeds_runner_cap():
    """#1 (cruel-critic round 2): el merge corpus+guidance JAMÁS rebasa el cap
    del runner (max_length=16000) — si lo hiciera el runner responde 422 y el
    bot queda MUDO. El corpus se recorta; la guidance sobrevive completa."""
    from khimeras_shared.guidance import MAX_GUIDANCE_CHARS

    client = _client()
    big_corpus = "C" * 3000  # supera el _REF_MAX_CHARS real, fuerza el recorte
    near_cap_guidance = "G" * (MAX_GUIDANCE_CHARS - 500)  # deja hueco < corpus
    with patch(
        "persona_gateway.turn_context.build_persona_corpus_block",
        new=AsyncMock(return_value=big_corpus),
    ):
        merged = await client._context.append_corpus_block(near_cap_guidance, "ask")
    assert merged is not None
    assert len(merged) <= MAX_GUIDANCE_CHARS
    # la guidance (seguridad) sobrevive intacta; lo que cede es el corpus
    assert merged.endswith(near_cap_guidance)


async def test_corpus_dropped_when_guidance_fills_cap():
    """#1 resistencia: cuando la guidance sola llena el cap, el corpus se
    DESCARTA (no se recorta la guidance de seguridad) — turno vive, no 422."""
    from khimeras_shared.guidance import MAX_GUIDANCE_CHARS

    client = _client()
    full_guidance = "G" * MAX_GUIDANCE_CHARS
    with patch(
        "persona_gateway.turn_context.build_persona_corpus_block",
        new=AsyncMock(return_value="C" * 2000),
    ):
        merged = await client._context.append_corpus_block(full_guidance, "ask")
    assert merged == full_guidance
    assert len(merged) <= MAX_GUIDANCE_CHARS


async def test_corpus_only_turn_capped():
    """#1: el invite path (guidance=None) tampoco puede rebasar el cap."""
    from khimeras_shared.guidance import MAX_GUIDANCE_CHARS

    client = _client()
    with patch(
        "persona_gateway.turn_context.build_persona_corpus_block",
        new=AsyncMock(return_value="C" * (MAX_GUIDANCE_CHARS + 5000)),
    ):
        merged = await client._context.append_corpus_block(None, "ask")
    assert merged is not None
    assert len(merged) <= MAX_GUIDANCE_CHARS
