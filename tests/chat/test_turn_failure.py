"""Tests for the typed-failure helpers in insult/cogs/chat/_failure.py (PR 2).

Covers:
- ``classify_discord_exception`` mapping of Discord HTTPException codes.
- ``emit_typing_safe`` swallows HTTPException and never re-raises.
- ``send_with_reaction_fallback`` falls through text → reaction → silent.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from personas.insult.cogs.chat._failure import (
    FailureClass,
    classify_discord_exception,
    emit_typing_safe,
    send_with_reaction_fallback,
)


def _mk_http_exc(status: int, code: int | None = None) -> discord.HTTPException:
    """Build a discord.HTTPException with the given status/code."""
    response = MagicMock()
    response.status = status
    exc = discord.HTTPException(response, {"code": code, "message": "test"} if code else "test")
    # discord.py sets these on the instance from the response/body.
    exc.status = status
    if code is not None:
        exc.code = code
    return exc


class TestClassifyDiscordException:
    def test_429_status_is_throttled(self):
        assert classify_discord_exception(_mk_http_exc(429)) == FailureClass.DISCORD_THROTTLED

    def test_code_40062_is_throttled_even_with_other_status(self):
        # Discord can return 40062 as a body code on a 429 response or
        # sometimes coupled with different HTTP status codes.
        assert classify_discord_exception(_mk_http_exc(429, code=40062)) == FailureClass.DISCORD_THROTTLED

    def test_other_http_error_is_discord_http(self):
        assert classify_discord_exception(_mk_http_exc(500)) == FailureClass.DISCORD_HTTP
        assert classify_discord_exception(_mk_http_exc(403)) == FailureClass.DISCORD_HTTP

    def test_non_discord_exception_is_unexpected(self):
        assert classify_discord_exception(ValueError("oops")) == FailureClass.UNEXPECTED


class TestEmitTypingSafe:
    @pytest.mark.asyncio
    async def test_typing_swallows_http_exception(self):
        """When send_typing 429s, emit_typing_safe must NOT propagate —
        the LLM call depends on this contract."""
        channel = MagicMock()
        channel.id = 123
        channel._state.http.send_typing = AsyncMock(side_effect=_mk_http_exc(429, code=40062))

        # Must NOT raise.
        await emit_typing_safe(channel)

        channel._state.http.send_typing.assert_awaited_once_with(123)

    @pytest.mark.asyncio
    async def test_typing_swallows_unexpected_exception(self):
        """Any non-HTTP exception is also caught (defensive)."""
        channel = MagicMock()
        channel.id = 123
        channel._state.http.send_typing = AsyncMock(side_effect=RuntimeError("boom"))

        await emit_typing_safe(channel)
        channel._state.http.send_typing.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_typing_happy_path(self):
        channel = MagicMock()
        channel.id = 123
        channel._state.http.send_typing = AsyncMock(return_value=None)

        await emit_typing_safe(channel)
        channel._state.http.send_typing.assert_awaited_once_with(123)

    @pytest.mark.asyncio
    async def test_typing_handles_channel_without_state(self):
        """Some channel objects in tests don't have ._state — must not crash."""
        channel = MagicMock(spec=[])  # no attributes
        # Must not raise (and not call anything)
        await emit_typing_safe(channel)


class TestSendWithReactionFallback:
    @pytest.mark.asyncio
    async def test_text_path_succeeds(self):
        msg = MagicMock()
        msg.channel.send = AsyncMock(return_value=None)
        msg.channel.id = 123

        mode = await send_with_reaction_fallback(msg, "hola")
        assert mode == "text"
        msg.channel.send.assert_awaited_once_with("hola")

    @pytest.mark.asyncio
    async def test_falls_back_to_reaction_when_send_throttles(self):
        msg = MagicMock()
        msg.channel.send = AsyncMock(side_effect=_mk_http_exc(429, code=40062))
        msg.add_reaction = AsyncMock(return_value=None)
        msg.channel.id = 123

        mode = await send_with_reaction_fallback(msg, "hola")
        assert mode == "reaction"
        msg.add_reaction.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_silent_when_both_paths_fail(self):
        msg = MagicMock()
        msg.channel.send = AsyncMock(side_effect=_mk_http_exc(429, code=40062))
        msg.add_reaction = AsyncMock(side_effect=_mk_http_exc(429, code=40062))
        msg.channel.id = 123

        mode = await send_with_reaction_fallback(msg, "hola")
        assert mode == "silent"

    @pytest.mark.asyncio
    async def test_silent_when_reaction_raises_forbidden(self):
        msg = MagicMock()
        msg.channel.send = AsyncMock(side_effect=_mk_http_exc(429))
        # discord.Forbidden — different exception, must also fall through.
        msg.add_reaction = AsyncMock(side_effect=discord.Forbidden(MagicMock(), "no perms"))
        msg.channel.id = 123

        mode = await send_with_reaction_fallback(msg, "hola")
        assert mode == "silent"
