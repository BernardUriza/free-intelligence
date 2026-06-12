"""Tests for insult.core.actions — tool definitions, sanitization, and channel creation execution."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from personas.insult.core.actions import (
    CHANNEL_TOOLS,
    ToolCall,
    execute_create_channel,
    execute_edit_channel,
    execute_get_channel_info,
    sanitize_channel_name,
)

# --- CHANNEL_TOOLS schema ---


class TestChannelTools:
    def test_tools_exist(self):
        names = [t["name"] for t in CHANNEL_TOOLS]
        assert "create_channel" in names
        assert "get_channel_info" in names
        assert "edit_channel" in names

    def test_create_channel_required_fields(self):
        tool = next(t for t in CHANNEL_TOOLS if t["name"] == "create_channel")
        schema = tool["input_schema"]
        assert "name" in schema["properties"]
        assert "channel_type" in schema["properties"]
        assert schema["required"] == ["name", "channel_type"]
        assert schema["additionalProperties"] is False

    def test_get_channel_info_no_params(self):
        tool = next(t for t in CHANNEL_TOOLS if t["name"] == "get_channel_info")
        schema = tool["input_schema"]
        assert schema["properties"] == {}
        assert schema["required"] == []

    def test_edit_channel_optional_params(self):
        tool = next(t for t in CHANNEL_TOOLS if t["name"] == "edit_channel")
        schema = tool["input_schema"]
        assert "name" in schema["properties"]
        assert "topic" in schema["properties"]
        assert schema["required"] == []


class TestAllToolsConformance:
    """Validate ALL tool definitions conform to Anthropic API requirements."""

    def test_all_tools_have_required_fields(self):
        all_tools = list(CHANNEL_TOOLS)
        for tool in all_tools:
            assert "name" in tool, "Tool must have 'name'"
            assert "input_schema" in tool, "Tool must have 'input_schema'"
            assert isinstance(tool["name"], str)
            schema = tool["input_schema"]
            assert schema["type"] == "object"
            assert isinstance(schema.get("properties", {}), dict)
            assert "strict" not in tool, (
                f"Tool '{tool['name']}' has strict:true which is not supported on claude-sonnet-4. "
                "Remove it or gate it behind a model check."
            )


# --- sanitize_channel_name ---


class TestSanitizeChannelName:
    def test_basic_name(self):
        assert sanitize_channel_name("mi canal") == "mi-canal"

    def test_uppercase(self):
        assert sanitize_channel_name("ADHD Focus") == "adhd-focus"

    def test_special_chars(self):
        assert sanitize_channel_name("café & más!") == "caf-ms"

    def test_multiple_hyphens(self):
        assert sanitize_channel_name("a---b") == "a-b"

    def test_empty_fallback(self):
        assert sanitize_channel_name("!!!") == "nuevo-canal"

    def test_max_length(self):
        result = sanitize_channel_name("a" * 200)
        assert len(result) <= 100

    def test_leading_trailing_hyphens(self):
        assert sanitize_channel_name("-test-") == "test"


# --- execute_create_channel ---


class TestExecuteCreateChannel:
    @pytest.fixture
    def mock_guild(self):
        guild = MagicMock()
        guild.name = "TestGuild"
        guild.channels = [MagicMock() for _ in range(10)]

        bot_member = MagicMock()
        bot_member.guild_permissions = MagicMock()
        bot_member.guild_permissions.manage_channels = True
        guild.me = bot_member
        guild.default_role = MagicMock()

        created_channel = MagicMock()
        created_channel.mention = "#test-channel"
        guild.create_text_channel = AsyncMock(return_value=created_channel)
        guild.create_category = AsyncMock(return_value=created_channel)

        return guild

    @pytest.fixture
    def mock_user(self):
        user = MagicMock()
        user.display_name = "TestUser"
        return user

    @patch("personas.insult.core.actions.asyncio.sleep", new_callable=AsyncMock)
    async def test_creates_private_channel(self, _sleep, mock_guild, mock_user):
        tool_call = ToolCall(id="tc_1", name="create_channel", input={"name": "mi espacio", "channel_type": "private"})
        result = await execute_create_channel(mock_guild, tool_call, mock_user)
        assert result is not None
        mock_guild.create_text_channel.assert_called_once()
        call_kwargs = mock_guild.create_text_channel.call_args
        assert "overwrites" in call_kwargs.kwargs or len(call_kwargs.args) > 1

    @patch("personas.insult.core.actions.asyncio.sleep", new_callable=AsyncMock)
    async def test_creates_topic_channel(self, _sleep, mock_guild, mock_user):
        tool_call = ToolCall(id="tc_2", name="create_channel", input={"name": "adhd-focus", "channel_type": "topic"})
        result = await execute_create_channel(mock_guild, tool_call, mock_user)
        assert result is not None
        mock_guild.create_text_channel.assert_called_once_with("adhd-focus")

    @patch("personas.insult.core.actions.asyncio.sleep", new_callable=AsyncMock)
    async def test_creates_category(self, _sleep, mock_guild, mock_user):
        tool_call = ToolCall(id="tc_3", name="create_channel", input={"name": "bienestar", "channel_type": "category"})
        result = await execute_create_channel(mock_guild, tool_call, mock_user)
        assert result is not None
        mock_guild.create_category.assert_called_once_with("bienestar")

    @patch("personas.insult.core.actions.asyncio.sleep", new_callable=AsyncMock)
    async def test_missing_permissions_returns_none(self, _sleep, mock_guild, mock_user):
        mock_guild.me.guild_permissions.manage_channels = False
        tool_call = ToolCall(id="tc_4", name="create_channel", input={"name": "test", "channel_type": "private"})
        result = await execute_create_channel(mock_guild, tool_call, mock_user)
        assert result is None
        mock_guild.create_text_channel.assert_not_called()

    @patch("personas.insult.core.actions.asyncio.sleep", new_callable=AsyncMock)
    async def test_channel_limit_returns_none(self, _sleep, mock_guild, mock_user):
        mock_guild.channels = [MagicMock() for _ in range(460)]
        tool_call = ToolCall(id="tc_5", name="create_channel", input={"name": "test", "channel_type": "topic"})
        result = await execute_create_channel(mock_guild, tool_call, mock_user)
        assert result is None

    @patch("personas.insult.core.actions.asyncio.sleep", new_callable=AsyncMock)
    async def test_defaults_to_private_on_invalid_type(self, _sleep, mock_guild, mock_user):
        tool_call = ToolCall(id="tc_6", name="create_channel", input={"name": "test", "channel_type": "invalid"})
        result = await execute_create_channel(mock_guild, tool_call, mock_user)
        assert result is not None
        call_kwargs = mock_guild.create_text_channel.call_args
        assert "overwrites" in call_kwargs.kwargs or len(call_kwargs.args) > 1

    @patch("personas.insult.core.actions.asyncio.sleep", new_callable=AsyncMock)
    async def test_sanitizes_channel_name(self, _sleep, mock_guild, mock_user):
        tool_call = ToolCall(
            id="tc_7", name="create_channel", input={"name": "Mi Canal Especial!!!", "channel_type": "topic"}
        )
        await execute_create_channel(mock_guild, tool_call, mock_user)
        mock_guild.create_text_channel.assert_called_once_with("mi-canal-especial")


# --- execute_get_channel_info ---


class TestExecuteGetChannelInfo:
    def test_returns_name_and_topic(self):
        channel = MagicMock()
        channel.name = "general"
        channel.topic = "Un canal para hablar de todo"
        result = execute_get_channel_info(channel)
        assert result == {"name": "general", "topic": "Un canal para hablar de todo"}

    def test_empty_topic(self):
        channel = MagicMock()
        channel.name = "random"
        channel.topic = None
        result = execute_get_channel_info(channel)
        assert result == {"name": "random", "topic": ""}


# --- execute_edit_channel ---


class TestExecuteEditChannel:
    @pytest.fixture
    def mock_channel(self):
        channel = MagicMock()
        channel.name = "old-name"
        channel.guild.name = "TestGuild"
        channel.guild.me.guild_permissions.manage_channels = True
        channel.edit = AsyncMock()
        return channel

    async def test_edits_name(self, mock_channel):
        tool_call = ToolCall(id="tc_e1", name="edit_channel", input={"name": "new-name"})
        result = await execute_edit_channel(mock_channel, tool_call)
        assert result is True
        mock_channel.edit.assert_called_once_with(name="new-name")

    async def test_edits_topic(self, mock_channel):
        tool_call = ToolCall(id="tc_e2", name="edit_channel", input={"topic": "nueva descripcion"})
        result = await execute_edit_channel(mock_channel, tool_call)
        assert result is True
        mock_channel.edit.assert_called_once_with(topic="nueva descripcion")

    async def test_edits_both(self, mock_channel):
        tool_call = ToolCall(id="tc_e3", name="edit_channel", input={"name": "cool-channel", "topic": "lo mas cool"})
        result = await execute_edit_channel(mock_channel, tool_call)
        assert result is True
        mock_channel.edit.assert_called_once_with(name="cool-channel", topic="lo mas cool")

    async def test_no_changes_returns_false(self, mock_channel):
        tool_call = ToolCall(id="tc_e4", name="edit_channel", input={})
        result = await execute_edit_channel(mock_channel, tool_call)
        assert result is False
        mock_channel.edit.assert_not_called()

    async def test_missing_permissions_returns_false(self, mock_channel):
        mock_channel.guild.me.guild_permissions.manage_channels = False
        tool_call = ToolCall(id="tc_e5", name="edit_channel", input={"name": "test"})
        result = await execute_edit_channel(mock_channel, tool_call)
        assert result is False

    async def test_sanitizes_name(self, mock_channel):
        tool_call = ToolCall(id="tc_e6", name="edit_channel", input={"name": "Mi Canal Rudo!!!"})
        await execute_edit_channel(mock_channel, tool_call)
        mock_channel.edit.assert_called_once_with(name="mi-canal-rudo")

    async def test_truncates_long_topic(self, mock_channel):
        tool_call = ToolCall(id="tc_e7", name="edit_channel", input={"topic": "x" * 2000})
        await execute_edit_channel(mock_channel, tool_call)
        call_kwargs = mock_channel.edit.call_args.kwargs
        assert len(call_kwargs["topic"]) == 1024
