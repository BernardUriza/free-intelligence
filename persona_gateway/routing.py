"""Pure reception predicates for the persona gateway.

Discord-message-in → decision/text-out, no I/O and no persona state: whether a
bot answers (`should_respond`), whether an edit newly summons it (`edit_summons`),
and stripping its own mention (`clean_mention`). Kept pure so they unit-test
without a live bot. Context framing is `khimeras_shared.memory.context` — the
one canonical framer.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

import discord

from shared.personas.addressing import any_alias_is_addressee, opens_addressing_insult


def clean_mention(content: str, bot_id: int) -> str:
    """Strip this bot's @mention(s) from the message text, leaving the ask.

    Discord renders mentions as `<@id>` / `<@!id>`. We remove only THIS bot's
    mention so "@Vultur reséñame Creep" → "reséñame Creep". Other mentions are
    left intact (they may be meaningful context).
    """
    cleaned = re.sub(rf"<@!?{bot_id}>", "", content)
    return cleaned.strip()


def should_respond(
    message: discord.Message,
    bot_user: discord.abc.User | None,
    aliases: Iterable[str] = (),
    *,
    host_owns_reception: bool = False,
) -> bool:
    """A persona-bot answers iff a NON-bot author addressed it.

    - `host_owns_reception` (cutover, #6): when the omnipresent host owns reception
      it routes EVERY message and summons the persona via /invite, so the persona
      must NOT also self-answer its own @mention (that is the double-answer, the
      "ventana de dos bots peleando"). When True, this gate always returns False —
      the persona is invite-only and responds solely to the host's /invite.

    - `author.bot` guard: never auto-invoke, never answer another bot (prevents
      Insult ↔ Vultur loops — same fix as Insult/ALICE v4.20.19).
    - mention-gated: opt-in by design. Post-purga (2026-07-14) this applies to
      EVERY persona incl. Insult (`aliases=[]` → @mention-only): no persona answers
      unaddressed chatter today. Insult's omnipresence returns only when the demux_ai
      host owns reception. A DIRECT user mention (`bot_user in message.mentions`) fires.
    - ROLE mention of the bot's OWN role also fires: pinging the bot's
      integration role (or a custom role assigned to the bot) is the classic "I
      pinged the bot's role expecting it to ping the bot" gotcha — `<@&roleid>`,
      not `<@userid>`, so it never landed in `message.mentions`. We honor it IFF
      the mentioned role is one THIS bot actually carries, and NEVER @everyone
      (its role id equals the guild id), so it stays mass-ping safe.
    - VOCATIVE text alias of THIS persona also fires ("frugi, qué opinas") — the
      complement of Insult's suppression gate. Both sides evaluate the SAME
      predicate (``shared.personas.addressing``): before this, Insult muted on
      any alias occurrence while the gateway needed a mention, so "dile a frugi
      que…" got NO answer from anyone for 5 minutes (P0 2026-07-06 17:24Z). A
      message that OPENS addressing Insult never alias-summons a sibling — the
      head of the message wins, same as Insult's gate.
    """
    if host_owns_reception:
        return False
    if bot_user is None or message.author.bot:
        return False
    if bot_user in message.mentions:
        return True
    # REPLY to one of THIS bot's messages is addressing too — the only
    # addressing channel a voice note has. A voice message carries no text
    # (`content` is empty) and cannot embed an @mention, so a bare audio never
    # fired `should_respond` and its (working) STT transcription never ran. A
    # Discord reply resolves to `message.reference.resolved`; when that resolved
    # message's author is this bot, the user is continuing the conversation with
    # this persona — by voice or by text. `cached_message` avoids an API fetch;
    # an uncached reference degrades to the mention/alias gates below.
    ref = getattr(message, "reference", None)
    resolved = getattr(ref, "resolved", None) or getattr(ref, "cached_message", None)
    if resolved is not None and getattr(resolved, "author", None) == bot_user:
        return True
    guild = getattr(message, "guild", None)
    if guild is not None:
        own_role_ids = {r.id for r in getattr(guild.me, "roles", [])}
        own_role_ids.discard(guild.id)  # @everyone — never a summon
        if any(role.id in own_role_ids for role in getattr(message, "role_mentions", [])):
            return True
    content = message.content or ""
    return not opens_addressing_insult(content) and any_alias_is_addressee(aliases, content)


def edit_summons(
    before: discord.Message,
    after: discord.Message,
    bot_user: discord.abc.User | None,
    aliases: Iterable[str] = (),
) -> bool:
    """True when an edit ADDS an address to this persona (not-addressed →
    addressed transition). An edit to a message the persona already answered
    (addressed before AND after) never re-triggers it."""
    return not should_respond(before, bot_user, aliases) and should_respond(after, bot_user, aliases)
