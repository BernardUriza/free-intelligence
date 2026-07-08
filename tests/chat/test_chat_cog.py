"""Tests for insult.cogs.chat — ChatCog with mocked dependencies.

We call the underlying callback directly (cog.chat.callback) to bypass
discord.py's command decorator machinery which expects a real Context.
The _respond() method uses message.channel.send, not ctx.send.
"""

from unittest.mock import AsyncMock

import pytest

from personas.insult.cogs.chat import MAX_MESSAGE_LENGTH, ChatCog
from personas.insult.core.llm import LLMResponse


class TestChatCog:
    @pytest.fixture
    def cog(self, mock_container):
        return ChatCog(mock_container)

    async def _call_chat(self, cog, ctx, message: str):
        """Call the chat command's underlying callback, bypassing the decorator."""
        await cog.chat.callback(cog, ctx, message=message)

    def _channel_send(self, mock_ctx):
        """Get the send mock from the message's channel."""
        return mock_ctx.message.channel.send

    async def test_too_long_via_chat_command_still_processes(self, cog, mock_ctx):
        """!chat delegates to _respond which processes regardless of length.
        Length validation is in on_message listener, not in the !chat command."""
        long_msg = "x" * (MAX_MESSAGE_LENGTH + 1)
        await self._call_chat(cog, mock_ctx, long_msg)
        # _respond processes the message (no length check in !chat path)
        cog.agent_client.chat.assert_called_once()

    async def test_stores_user_message(self, cog, mock_ctx):
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="respuesta"))
        await self._call_chat(cog, mock_ctx, "hola wey")
        # Verify user message was stored (with guild_id and channel_name kwargs)
        store_calls = cog.memory.store.call_args_list
        user_calls = [c for c in store_calls if c.args[3] == "user"]
        assert len(user_calls) >= 1
        call = user_calls[0]
        assert call.args[:5] == (
            str(mock_ctx.message.channel.id),
            str(mock_ctx.author.id),
            mock_ctx.author.display_name,
            "user",
            "hola wey",
        )

    async def test_updates_user_profile(self, cog, mock_ctx):
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="respuesta"))
        await self._call_chat(cog, mock_ctx, "hola wey")
        cog.memory.update_profile.assert_called_once_with(str(mock_ctx.author.id), "hola wey")

    async def test_sends_llm_response(self, cog, mock_ctx):
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="Eres un pendejo."))
        await self._call_chat(cog, mock_ctx, "ayudame")
        sent_text = " ".join(str(c) for c in self._channel_send(mock_ctx).call_args_list)
        assert "Eres un pendejo." in sent_text

    async def test_stores_assistant_response(self, cog, mock_ctx):
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="respuesta del bot"))
        await self._call_chat(cog, mock_ctx, "hola")
        # Verify assistant response was stored (with guild_id and channel_name kwargs)
        store_calls = cog.memory.store.call_args_list
        assistant_calls = [c for c in store_calls if c.args[3] == "assistant"]
        assert len(assistant_calls) >= 1
        call = assistant_calls[0]
        assert call.args[:5] == (
            str(mock_ctx.message.channel.id),
            str(cog.bot.user.id),
            cog.bot.user.name,
            "assistant",
            "respuesta del bot",
        )
        assert call.kwargs.get("for_user_id") == str(mock_ctx.author.id)

    async def test_handles_llm_error_gracefully(self, cog, mock_ctx):
        cog.agent_client.chat = AsyncMock(side_effect=RuntimeError("something broke"))
        await self._call_chat(cog, mock_ctx, "hola")
        self._channel_send(mock_ctx).assert_called()

    async def test_handles_context_failure(self, cog, mock_ctx):
        cog.memory.get_recent = AsyncMock(side_effect=Exception("DB error"))
        await self._call_chat(cog, mock_ctx, "hola")
        self._channel_send(mock_ctx).assert_called()
        cog.agent_client.chat.assert_not_called()

    async def test_handles_profile_failure_gracefully(self, cog, mock_ctx):
        """Profile update failure should NOT block the chat flow."""
        cog.memory.update_profile = AsyncMock(side_effect=Exception("DB error"))
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="sigo funcionando"))
        await self._call_chat(cog, mock_ctx, "hola")
        cog.agent_client.chat.assert_called_once()

    async def test_chunks_long_responses(self, cog, mock_ctx):
        long_response = "A" * 4000
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text=long_response))
        await self._call_chat(cog, mock_ctx, "hola")
        send_calls = self._channel_send(mock_ctx).call_args_list
        assert len(send_calls) >= 2
