"""ALICE must not auto-invoke on a SIBLING BOT's loose triggers (v4.20.19).

Insult uses "amix"/"ali" as casual vocatives toward users and trips clinical
keywords inside its own replies. Before the guard, ALICE matched the alias on
Insult's message and barged into the conversation — "siempre se mete, persigue
a Alex" (KQL 2026-06-03: 8/8 "amix" messages in 8h were bot-authored).

Mutator rule (.claude/rules/robustness.md): positive case (bot alias is
suppressed) + resistance case (a human's identical alias still invokes her).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from personas.alice.cogs.chat import AliceChatCog

ALICE_ID = 1503983124982534284


def _make_cog():
    bot = MagicMock()
    bot.user = SimpleNamespace(id=ALICE_ID)
    cog = AliceChatCog(bot=bot, memory=MagicMock(), llm=MagicMock(), persona=MagicMock())
    cog._respond = AsyncMock(return_value="ok")
    return cog


def _msg(content: str, *, author_is_bot: bool):
    author = MagicMock()
    author.bot = author_is_bot
    author.id = 999
    # channel.typing() is an async context manager wrapping the respond cycle.
    typing_cm = MagicMock()
    typing_cm.__aenter__ = AsyncMock(return_value=None)
    typing_cm.__aexit__ = AsyncMock(return_value=None)
    channel = MagicMock()
    channel.id = 1489180895264116736
    channel.name = "general"
    channel.typing = MagicMock(return_value=typing_cm)
    m = MagicMock()
    m.author = author
    m.content = content
    m.mentions = []  # no explicit @-mention of ALICE
    m.guild = SimpleNamespace(id=1, roles=[])  # guild channel, no role mention
    m.channel = channel
    return m


@pytest.mark.asyncio
async def test_bot_saying_amix_does_not_invoke_alice():
    """Positive: Insult saying 'Amix,' to a user must NOT wake ALICE."""
    cog = _make_cog()
    await cog.on_message(_msg("Amix, hace nada me enlistaste tu vida entera", author_is_bot=True))
    cog._respond.assert_not_awaited()


@pytest.mark.asyncio
async def test_bot_clinical_keyword_does_not_invoke_alice():
    """Positive: a clinical keyword inside another bot's reply must NOT wake her."""
    cog = _make_cog()
    await cog.on_message(_msg("ya te dije lo del psiquiatra, no te hagas", author_is_bot=True))
    cog._respond.assert_not_awaited()


@pytest.mark.asyncio
async def test_human_saying_amix_still_invokes_alice():
    """Resistance: a human's 'amix' is a genuine address and must still work."""
    cog = _make_cog()
    await cog.on_message(_msg("amix, ¿ya quedaste?", author_is_bot=False))
    cog._respond.assert_awaited_once()
