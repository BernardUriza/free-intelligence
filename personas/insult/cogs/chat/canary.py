"""Canary ingress probe — the live liveness contract /debug/health couldn't prove.

A dedicated canary bot posts ``CANARY insult <uuid>`` in #canary; Insult must echo
``CANARY_OK <uuid>`` deterministically — NO LLM, NO batch, NO pipeline. This proves
real Discord ingress/egress + live routing, the thing ``/debug/health`` failed at
(it returned ``is_ready:true`` while the bot was a zombie answering no one).

Brutally simple by design: the bypass of the ``author.bot`` guard is limited to
exactly the triple (CANARY_CHANNEL_ID, CANARY_BOT_USER_ID, ``CANARY insult `` prefix).
Anything else returns ``False`` and falls through to the normal pipeline, where the
bot guard drops it. Identity is gated by ID, never by message content alone.
"""

from __future__ import annotations

import re

import discord
import structlog

log = structlog.get_logger()

CANARY_PREFIX = "CANARY insult "
CANARY_OK_PREFIX = "CANARY_OK "
_NONCE_RE = re.compile(r"^CANARY insult (?P<nonce>[A-Za-z0-9-]{1,64})$")
_OK_RE = re.compile(r"^CANARY_OK (?P<nonce>[A-Za-z0-9-]{1,64})$")


def parse_canary(content: str) -> str | None:
    """Return the nonce iff ``content`` is exactly ``CANARY insult <nonce>``."""
    match = _NONCE_RE.match((content or "").strip())
    return match.group("nonce") if match else None


def parse_canary_ok(content: str) -> str | None:
    """Return the nonce iff ``content`` is exactly ``CANARY_OK <nonce>``.

    The runner side: a reply only counts when it carries the SAME nonce the
    probe posted, AND (checked by the runner) comes from the Insult bot's user
    ID in the canary channel — author verified by ID, never by content alone.
    """
    match = _OK_RE.match((content or "").strip())
    return match.group("nonce") if match else None


def is_canary_message(message: discord.Message, settings) -> str | None:
    """Return the nonce iff this message is a valid canary probe, else ``None``.

    Triple gate, all required: configured channel ID, configured canary bot
    user ID, and the exact prefix. Unconfigured (empty id) → disabled → ``None``.
    """
    channel_id = str(getattr(settings, "canary_channel_id", "") or "")
    bot_user_id = str(getattr(settings, "canary_bot_user_id", "") or "")
    if not channel_id or not bot_user_id:
        return None
    if str(message.channel.id) != channel_id:
        return None
    if str(message.author.id) != bot_user_id:
        return None
    return parse_canary(message.content)


async def try_handle_canary(message: discord.Message, settings) -> bool:
    """Reply ``CANARY_OK <nonce>`` and return ``True`` for a valid probe.

    Returns ``False`` for everything else so the caller continues to the normal
    pipeline. The reply is a bare echo — no persona, no model — so the canary
    measures Discord ingress/egress and live routing, not model quality.
    """
    nonce = is_canary_message(message, settings)
    if nonce is None:
        return False
    await message.channel.send(f"CANARY_OK {nonce}")
    log.info("canary_ok", nonce=nonce, channel_id=str(message.channel.id))
    return True
