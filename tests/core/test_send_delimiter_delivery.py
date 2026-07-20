"""[SEND] multi-message delivery — el delimitador divide y pacea, nunca se entrega.

Regresión 2026-07-20: la DNA de Insult enseña `[SEND]` como delimitador
multi-mensaje, pero la purga dejó a `split_response` sin consumidor vivo y el
delimitador salía LITERAL en Discord ("…la hizo bien.[SEND]Tu turno…").
Mutator rule: positivo (el delimitador produce mensajes separados y jamás llega
al canal, ni a memoria, ni al 🔊) + resistencia (texto sin delimitador queda
intacto, un solo mensaje).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from persona_gateway import delivery
from persona_gateway.delivery import full_text_for, send_chunked
from persona_gateway.gateway import PersonaClient
from shared.personas import Persona


@pytest.fixture(autouse=True)
def _clean_registry():
    delivery._full_texts.clear()
    yield
    delivery._full_texts.clear()


@pytest.fixture
def _no_pacing(monkeypatch):
    monkeypatch.setattr(delivery, "_pacing_delay", lambda part: 0.0)


def _channel_with_ids(start: int = 100):
    channel = MagicMock()
    counter = {"next": start}

    async def _send(piece):
        message = MagicMock()
        message.id = counter["next"]
        counter["next"] += 1
        return message

    channel.send = AsyncMock(side_effect=_send)
    return channel


async def test_send_parts_arrive_as_separate_messages(_no_pacing):
    channel = _channel_with_ids()
    sent = await send_chunked(channel, "A ver...[SEND]No.[SEND]Definitivamente no.")
    assert len(sent) == 3
    delivered = [c.args[0] for c in channel.send.call_args_list]
    assert delivered[0] == "A ver..."
    assert delivered[1] == "No."
    assert delivered[2].startswith("Definitivamente no.")
    for piece in delivered:
        assert "[SEND]" not in piece
    assert "-# ᵛ" not in delivered[0]
    assert "-# ᵛ" not in delivered[1]
    assert "-# ᵛ" in delivered[2]


async def test_full_text_registered_without_delimiter(_no_pacing):
    channel = _channel_with_ids()
    sent = await send_chunked(channel, "A ver...[SEND]No mames.")
    expected = "A ver...\nNo mames."
    for message in sent:
        assert full_text_for(message.id) == expected


async def test_text_without_delimiter_stays_one_message(_no_pacing):
    channel = _channel_with_ids()
    sent = await send_chunked(channel, "Reseña normal sin delimitador.")
    assert len(sent) == 1
    assert channel.send.call_args_list[0].args[0].startswith("Reseña normal sin delimitador.")


async def test_delimiter_only_reply_sends_nothing(_no_pacing):
    channel = _channel_with_ids()
    sent = await send_chunked(channel, "[SEND]")
    assert sent == []
    channel.send.assert_not_called()


def test_pacing_delay_is_typing_paced_and_capped():
    assert delivery._pacing_delay("x" * 10) == pytest.approx(10 * delivery._PACING_SECONDS_PER_CHAR)
    assert delivery._pacing_delay("x" * 10_000) == delivery._PACING_CAP_SECONDS


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _client(reply_text: str) -> PersonaClient:
    persona = Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text=reply_text, model_used="claude"))
    return PersonaClient(persona, memory, agent_client, intents=discord.Intents.none())


async def test_turn_path_stores_delivered_text_without_delimiter(_no_pacing):
    client = _client("Primera parte.[SEND]Segunda parte.")
    channel = _channel_with_ids()
    channel.typing = MagicMock(return_value=_Typing())
    await client._run_and_deliver(
        channel=channel,
        channel_id="C1",
        user_id="U1",
        guild_id="G1",
        channel_name="general",
        messages=[{"role": "user", "content": "hola"}],
    )
    assert channel.send.call_count == 2
    stored_text = client.memory.store.call_args.args[4]
    assert "[SEND]" not in stored_text
    assert stored_text == "Primera parte.\nSegunda parte."
