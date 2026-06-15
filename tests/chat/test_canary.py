"""Canary ingress probe — the live liveness contract /debug/health couldn't prove.

A dedicated canary bot posts `CANARY insult <uuid>` in #canary; Insult must echo
`CANARY_OK <uuid>` deterministically (no LLM, no batch, no pipeline). The bypass
of the `author.bot` guard is limited to exactly the triple (CANARY_CHANNEL_ID,
CANARY_BOT_USER_ID, "CANARY insult " prefix) — anything else falls through to the
normal pipeline (where the bot guard drops it).

Mutator rule: positive (valid probe answered) + resistance (wrong channel / wrong
author / wrong prefix / human imitator all ignored).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from personas.insult.cogs.chat.canary import (
    is_canary_message,
    parse_canary,
    parse_canary_ok,
    try_handle_canary,
)

CANARY_CHANNEL_ID = "1490000000000000001"
CANARY_BOT_USER_ID = "1490000000000000002"


def _settings(*, channel=CANARY_CHANNEL_ID, author=CANARY_BOT_USER_ID):
    return SimpleNamespace(canary_channel_id=channel, canary_bot_user_id=author)


def _msg(content: str, *, channel_id=CANARY_CHANNEL_ID, author_id=CANARY_BOT_USER_ID, is_bot=True):
    channel = MagicMock()
    channel.id = int(channel_id)
    channel.send = AsyncMock()
    author = SimpleNamespace(id=int(author_id), bot=is_bot)
    return SimpleNamespace(content=content, channel=channel, author=author)


def test_parse_canary_extracts_nonce():
    assert parse_canary("CANARY insult abc-123") == "abc-123"
    assert parse_canary("  CANARY insult deadbeef  ") == "deadbeef"


def test_parse_canary_rejects_non_canary():
    assert parse_canary("hello there") is None
    assert parse_canary("CANARY alice abc-123") is None
    assert parse_canary("CANARY insult") is None
    assert parse_canary("") is None


def test_is_canary_message_requires_full_triple():
    s = _settings()
    assert is_canary_message(_msg("CANARY insult n1"), s) == "n1"
    assert is_canary_message(_msg("CANARY insult n1", channel_id="999"), s) is None
    assert is_canary_message(_msg("CANARY insult n1", author_id="999"), s) is None
    assert is_canary_message(_msg("not a canary"), s) is None


def test_is_canary_message_disabled_when_unconfigured():
    assert is_canary_message(_msg("CANARY insult n1"), _settings(channel="")) is None
    assert is_canary_message(_msg("CANARY insult n1"), _settings(author="")) is None


def test_parse_canary_ok_roundtrips_the_nonce():
    assert parse_canary_ok("CANARY_OK abc-123") == "abc-123"
    assert parse_canary_ok("  CANARY_OK deadbeef  ") == "deadbeef"
    assert parse_canary_ok("CANARY_OK") is None
    assert parse_canary_ok("CANARY insult abc-123") is None
    assert parse_canary_ok("ok") is None


@pytest.mark.asyncio
async def test_valid_probe_echoes_canary_ok():
    m = _msg("CANARY insult nonce-xyz")
    handled = await try_handle_canary(m, _settings())
    assert handled is True
    m.channel.send.assert_awaited_once_with("CANARY_OK nonce-xyz")


@pytest.mark.asyncio
async def test_wrong_channel_not_handled():
    m = _msg("CANARY insult nonce-xyz", channel_id="999")
    handled = await try_handle_canary(m, _settings())
    assert handled is False
    m.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_wrong_author_not_handled():
    m = _msg("CANARY insult nonce-xyz", author_id="999")
    handled = await try_handle_canary(m, _settings())
    assert handled is False
    m.channel.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_human_imitator_in_canary_channel_not_handled():
    """A human typing the magic words is NOT the canary bot — author ID gate."""
    m = _msg("CANARY insult nonce-xyz", author_id="555", is_bot=False)
    handled = await try_handle_canary(m, _settings())
    assert handled is False
    m.channel.send.assert_not_awaited()
