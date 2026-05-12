"""Tests for the `!sync-token` Discord command.

Covers the issuance/revocation flow without spinning up a real bot:

- Default action mints a fresh token, revokes prior, DMs the user.
- `revoke` action wipes live tokens without minting anything.
- The plaintext token is NEVER echoed to the channel (security invariant).
- When DMs are disabled, the channel gets a fallback message — but still
  no plaintext leak.
- Bad action arguments produce a helpful in-character usage message.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from insult.cogs.utility import UtilityCog


@pytest.fixture
def cog(mock_container):
    return UtilityCog(mock_container)


@pytest.fixture
def ctx_with_dms():
    """ctx where DMs are open (author.send succeeds)."""
    ctx = MagicMock()
    ctx.author.id = 1431300030823927999
    ctx.author.display_name = "Alex"
    ctx.author.send = AsyncMock()  # DM succeeds
    ctx.send = AsyncMock()
    return ctx


@pytest.fixture
def ctx_dms_closed():
    """ctx where author.send raises Forbidden (DMs disabled)."""
    ctx = MagicMock()
    ctx.author.id = 1431300030823927999
    ctx.author.display_name = "Alex"
    err = discord.Forbidden(MagicMock(status=403, reason="Forbidden"), "DMs closed")
    ctx.author.send = AsyncMock(side_effect=err)
    ctx.send = AsyncMock()
    return ctx


# --- show / default action ---


@pytest.mark.asyncio
async def test_default_action_mints_token_and_dms_user(cog, ctx_with_dms):
    await cog.sync_token.callback(cog, ctx_with_dms, "show")
    # Prior tokens revoked (returns 0 by default fixture).
    cog.memory.revoke_sync_tokens.assert_awaited_once_with("1431300030823927999")
    # New token stored.
    cog.memory.create_sync_token.assert_awaited_once()
    args, _ = cog.memory.create_sync_token.call_args
    assert args[0] == "1431300030823927999"
    minted_token = args[1]
    # secrets.token_urlsafe(32) → ~43 url-safe chars.
    assert len(minted_token) >= 32

    # DM sent with the token, channel got only the confirmation.
    ctx_with_dms.author.send.assert_awaited_once()
    dm_body = ctx_with_dms.author.send.call_args.args[0]
    assert minted_token in dm_body
    assert "INSULT_SYNC_TOKEN" in dm_body
    assert "INSULT_SYNC_URL" in dm_body

    ctx_with_dms.send.assert_awaited_once()
    channel_msg = ctx_with_dms.send.call_args.args[0]
    assert minted_token not in channel_msg  # PLAINTEXT MUST NOT leak to channel
    assert "DM" in channel_msg


@pytest.mark.asyncio
async def test_no_action_defaults_to_show(cog, ctx_with_dms):
    """`!sync-token` (no arg) and `!sync-token show` behave identically."""
    await cog.sync_token.callback(cog, ctx_with_dms)
    cog.memory.create_sync_token.assert_awaited_once()


# --- revoke action ---


@pytest.mark.asyncio
async def test_revoke_action_revokes_and_does_not_mint(cog, ctx_with_dms):
    cog.memory.revoke_sync_tokens = AsyncMock(return_value=3)
    await cog.sync_token.callback(cog, ctx_with_dms, "revoke")
    cog.memory.revoke_sync_tokens.assert_awaited_once_with("1431300030823927999")
    cog.memory.create_sync_token.assert_not_awaited()
    ctx_with_dms.send.assert_awaited_once()
    msg = ctx_with_dms.send.call_args.args[0]
    assert "3" in msg


# --- DMs closed fallback ---


@pytest.mark.asyncio
async def test_dms_closed_does_not_leak_plaintext_to_channel(cog, ctx_dms_closed):
    """When DMs are disabled the channel must NOT receive the plaintext.
    The user gets a generic "abre tus DMs" instruction so they can retry."""
    await cog.sync_token.callback(cog, ctx_dms_closed, "show")
    # Token still minted server-side (the user can use !sync-token revoke later).
    cog.memory.create_sync_token.assert_awaited_once()
    minted_token = cog.memory.create_sync_token.call_args.args[1]

    # Channel received the fallback notice, NO plaintext.
    ctx_dms_closed.send.assert_awaited_once()
    fallback_msg = ctx_dms_closed.send.call_args.args[0]
    assert minted_token not in fallback_msg
    assert "DM" in fallback_msg.upper() or "DMs" in fallback_msg


# --- bad arguments ---


@pytest.mark.asyncio
async def test_unknown_action_returns_usage(cog, ctx_with_dms):
    await cog.sync_token.callback(cog, ctx_with_dms, "weird-action")
    cog.memory.create_sync_token.assert_not_awaited()
    cog.memory.revoke_sync_tokens.assert_not_awaited()
    ctx_with_dms.send.assert_awaited_once()
    msg = ctx_with_dms.send.call_args.args[0]
    assert "!sync-token" in msg
