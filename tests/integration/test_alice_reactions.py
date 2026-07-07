"""ALICE [REACT:] wiring — she reacts to the message that summoned her.

Mutator rule: positive (marker → reactions fired on the triggering message,
marker stripped from the visible + persisted text) + resistance (no marker →
text untouched, nothing fired; invite path with no triggering message → marker
still never leaks).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from personas.alice.cogs.chat import AliceChatCog


def _make_cog(reply_text: str) -> AliceChatCog:
    memory = MagicMock()
    memory.get_recent_messages = AsyncMock(return_value=[])
    memory.store_response = AsyncMock()
    llm = MagicMock()
    llm.chat = AsyncMock(
        return_value=SimpleNamespace(
            text=reply_text,
            model="gpt-4.1",
            input_tokens=10,
            output_tokens=10,
            latency_ms=5.0,
        )
    )
    persona = MagicMock()
    persona.load = MagicMock(return_value="Eres ALICE.")
    return AliceChatCog(bot=MagicMock(), memory=memory, llm=llm, persona=persona)


def _channel():
    channel = MagicMock()
    channel.send = AsyncMock()
    return channel


async def _respond(cog: AliceChatCog, channel, react_to=None) -> str:
    return await cog._respond(
        channel=channel,
        channel_id="C1",
        guild_id="G1",
        channel_name="general",
        user_msg="hola",
        react_to=react_to,
    )


async def test_marker_fires_reactions_and_strips_text():
    cog = _make_cog("Aquí estoy.[REACT:🤍]")
    channel = _channel()
    trigger = MagicMock()
    with patch("personas.alice.cogs.chat.add_reactions", new_callable=AsyncMock) as mock_add:
        text = await _respond(cog, channel, react_to=trigger)
        await asyncio.sleep(0)
    mock_add.assert_awaited_once_with(trigger, ["🤍"])
    sent = " ".join(str(c) for c in channel.send.call_args_list)
    assert "Aquí estoy." in sent
    assert "REACT" not in sent
    assert "REACT" not in text
    stored_text = cog.memory.store_response.call_args.kwargs["content"]
    assert "REACT" not in stored_text


async def test_reaction_only_reply_sends_no_text():
    cog = _make_cog("[REACT:🌊]")
    channel = _channel()
    trigger = MagicMock()
    with patch("personas.alice.cogs.chat.add_reactions", new_callable=AsyncMock) as mock_add:
        await _respond(cog, channel, react_to=trigger)
        await asyncio.sleep(0)
    mock_add.assert_awaited_once_with(trigger, ["🌊"])
    channel.send.assert_not_called()


async def test_no_marker_is_untouched_and_fires_nothing():
    cog = _make_cog("Respuesta normal sin reacciones.")
    channel = _channel()
    with patch("personas.alice.cogs.chat.add_reactions", new_callable=AsyncMock) as mock_add:
        await _respond(cog, channel, react_to=MagicMock())
        await asyncio.sleep(0)
    mock_add.assert_not_awaited()
    sent = " ".join(str(c) for c in channel.send.call_args_list)
    assert "Respuesta normal sin reacciones." in sent


async def test_invite_path_never_leaks_marker_without_trigger_message():
    cog = _make_cog("Llego al hilo.[REACT:🤍]")
    channel = _channel()
    with patch("personas.alice.cogs.chat.add_reactions", new_callable=AsyncMock) as mock_add:
        await _respond(cog, channel, react_to=None)
        await asyncio.sleep(0)
    mock_add.assert_not_awaited()
    sent = " ".join(str(c) for c in channel.send.call_args_list)
    assert "Llego al hilo." in sent
    assert "REACT" not in sent
