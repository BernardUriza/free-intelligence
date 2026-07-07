"""Integration tests — [REACT:] responses through Insult's chat cog.

The pure parse/strip/execute suite lives with the shared module in
tests/shared/test_reactions.py; this file only covers the ChatCog wiring.
"""

from unittest.mock import AsyncMock

from personas.insult.cogs.chat import ChatCog
from personas.insult.core.llm import LLMResponse


class TestReactionIntegration:
    async def test_response_with_reaction_sends_text_and_reacts(self, mock_container, mock_ctx):
        cog = ChatCog(mock_container)
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="Eso estuvo bien.[REACT:💀]"))
        await cog.chat.callback(cog, mock_ctx, message="hola")
        # Text should be sent without [REACT:] marker
        sent_text = " ".join(str(c) for c in mock_ctx.message.channel.send.call_args_list)
        assert "Eso estuvo bien." in sent_text
        assert "REACT" not in sent_text

    async def test_reaction_only_response_no_text_sent(self, mock_container, mock_ctx):
        cog = ChatCog(mock_container)
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="[REACT:👀]"))
        await cog.chat.callback(cog, mock_ctx, message="hola")
        # No text message should be sent (reaction-only)
        mock_ctx.message.channel.send.assert_not_called()

    async def test_no_reaction_marker_works_normally(self, mock_container, mock_ctx):
        cog = ChatCog(mock_container)
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="Respuesta normal"))
        await cog.chat.callback(cog, mock_ctx, message="hola")
        sent_text = " ".join(str(c) for c in mock_ctx.message.channel.send.call_args_list)
        assert "Respuesta normal" in sent_text
