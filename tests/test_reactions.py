"""Tests for emoji reaction system — parsing, stripping, and async execution."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from insult.cogs.chat import ChatCog
from insult.core.llm import LLMResponse
from insult.core.reactions import add_reactions, parse_reactions, strip_reactions

# --- parse_reactions ---


class TestParseReactions:
    def test_single_emoji(self):
        assert parse_reactions("Eso estuvo bien.[REACT:💀]") == ["💀"]

    def test_multiple_emojis(self):
        assert parse_reactions("Jaja[REACT:💀,🔥,😂]") == ["💀", "🔥", "😂"]

    def test_no_reaction_marker(self):
        assert parse_reactions("Respuesta normal sin reacciones.") == []

    def test_empty_react_marker(self):
        assert parse_reactions("Algo[REACT:]") == []

    def test_max_reactions_enforced(self):
        result = parse_reactions("[REACT:💀,🔥,😂,🫠,👀,🦷,🪬,🧿,🌀,🦴]")
        assert len(result) == 8  # MAX_REACTIONS = 8

    def test_react_only_no_text(self):
        assert parse_reactions("[REACT:👀]") == ["👀"]

    def test_react_with_send_delimiter(self):
        result = parse_reactions("A ver...[SEND]No mames.[REACT:💀,🫠]")
        assert result == ["💀", "🫠"]

    def test_case_insensitive(self):
        assert parse_reactions("[react:💀]") == ["💀"]
        assert parse_reactions("[React:🔥]") == ["🔥"]

    def test_whitespace_in_emojis(self):
        assert parse_reactions("[REACT: 💀 , 🔥 ]") == ["💀", "🔥"]

    def test_react_in_middle_of_text(self):
        assert parse_reactions("Hola[REACT:💀]mundo") == ["💀"]

    def test_multiple_react_markers_uses_first(self):
        # Only first match is used
        result = parse_reactions("[REACT:💀][REACT:🔥]")
        assert result == ["💀"]

    def test_concatenated_emojis_without_commas_are_split(self):
        # Regression: LLM sometimes emits emojis glued without commas (real prod log:
        # [REACT:🦷🪬🫧🧿🪸🦠]) — Discord rejects the single multi-emoji "token" with
        # 400 Unknown Emoji. Parser must split concatenated graphemes.
        result = parse_reactions("[REACT:🦷🪬🫧🧿🪸🦠]")
        assert result == ["🦷", "🪬", "🫧", "🧿", "🪸", "🦠"]

    def test_mixed_commas_and_concatenation(self):
        result = parse_reactions("[REACT:💀🔥,😂]")
        assert result == ["💀", "🔥", "😂"]


# --- strip_reactions ---


class TestStripReactions:
    def test_strips_single_react(self):
        assert strip_reactions("Hola[REACT:💀]") == "Hola"

    def test_strips_multiple_emojis(self):
        assert strip_reactions("Ok[REACT:💀,🔥]") == "Ok"

    def test_strips_react_only(self):
        assert strip_reactions("[REACT:👀]") == ""

    def test_no_react_unchanged(self):
        assert strip_reactions("Normal response") == "Normal response"

    def test_strips_with_send(self):
        result = strip_reactions("Hola[SEND]Mundo[REACT:💀]")
        assert result == "Hola[SEND]Mundo"

    def test_strips_all_react_markers(self):
        result = strip_reactions("[REACT:💀]Hola[REACT:🔥]")
        assert "REACT" not in result


# --- add_reactions (standalone async function) ---


class TestAddReactions:
    @pytest.fixture
    def mock_message(self):
        msg = MagicMock()
        msg.id = 12345
        msg.add_reaction = AsyncMock()
        return msg

    @patch("insult.core.reactions.asyncio.sleep", new_callable=AsyncMock)
    async def test_adds_single_reaction(self, mock_sleep, mock_message):
        await add_reactions(mock_message, ["💀"])
        mock_message.add_reaction.assert_called_once_with("💀")

    @patch("insult.core.reactions.asyncio.sleep", new_callable=AsyncMock)
    async def test_adds_multiple_reactions(self, mock_sleep, mock_message):
        await add_reactions(mock_message, ["💀", "🔥"])
        assert mock_message.add_reaction.call_count == 2
        mock_message.add_reaction.assert_any_call("💀")
        mock_message.add_reaction.assert_any_call("🔥")

    @patch("insult.core.reactions.asyncio.sleep", new_callable=AsyncMock)
    async def test_stops_on_http_error(self, mock_sleep, mock_message):
        import discord

        mock_message.add_reaction = AsyncMock(side_effect=discord.HTTPException(MagicMock(status=400), "Bad emoji"))
        # Should not raise — error is caught internally
        await add_reactions(mock_message, ["invalid", "💀"])
        # Stops after first failure, doesn't try second
        assert mock_message.add_reaction.call_count == 1

    @patch("insult.core.reactions.asyncio.sleep", new_callable=AsyncMock)
    async def test_has_initial_delay(self, mock_sleep, mock_message):
        await add_reactions(mock_message, ["💀"])
        # First sleep call is the initial human-like delay
        first_sleep = mock_sleep.call_args_list[0]
        delay = first_sleep[0][0]
        assert 0.5 <= delay <= 2.0


# --- Integration: response with reactions goes through _respond ---


class TestReactionIntegration:
    @pytest.fixture
    def cog(self, mock_container):
        return ChatCog(mock_container)

    async def test_response_with_reaction_sends_text_and_reacts(self, cog, mock_ctx):
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="Eso estuvo bien.[REACT:💀]"))
        await cog.chat.callback(cog, mock_ctx, message="hola")
        # Text should be sent without [REACT:] marker
        sent_text = " ".join(str(c) for c in mock_ctx.message.channel.send.call_args_list)
        assert "Eso estuvo bien." in sent_text
        assert "REACT" not in sent_text

    async def test_reaction_only_response_no_text_sent(self, cog, mock_ctx):
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="[REACT:👀]"))
        await cog.chat.callback(cog, mock_ctx, message="hola")
        # No text message should be sent (reaction-only)
        mock_ctx.message.channel.send.assert_not_called()

    async def test_no_reaction_marker_works_normally(self, cog, mock_ctx):
        cog.agent_client.chat = AsyncMock(return_value=LLMResponse(text="Respuesta normal"))
        await cog.chat.callback(cog, mock_ctx, message="hola")
        sent_text = " ".join(str(c) for c in mock_ctx.message.channel.send.call_args_list)
        assert "Respuesta normal" in sent_text
