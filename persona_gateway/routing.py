"""Pure reception predicates + context framing for the persona gateway.

Discord-message-in → decision/text-out, no I/O and no persona state: whether a
bot answers (`should_respond`), whether an edit newly summons it (`edit_summons`),
stripping its own mention (`clean_mention`), and framing stored rows for the
runner (`format_context`). Kept pure so they unit-test without a live bot.
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
) -> bool:
    """A persona-bot answers iff a NON-bot author addressed it.

    - `author.bot` guard: never auto-invoke, never answer another bot (prevents
      Insult ↔ Vultur loops — same fix as Insult/ALICE v4.20.19).
    - mention-gated: opt-in by design; the host (Insult) is the only omnipresent
      one. A DIRECT user mention (`bot_user in message.mentions`) fires.
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
    if bot_user is None or message.author.bot:
        return False
    if bot_user in message.mentions:
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


def format_context(recent: list[dict]) -> list[dict]:
    """Turn stored rows into speaker-prefixed message dicts for the runner.

    Mirrors how the Insult plumbing frames context: each line is
    "Name: text" so the runner can attribute who said what. Role is kept as a
    plain "user" turn — the runner reads it as channel context, not as its own
    history (the persona-bot's own past replies are stored as role='assistant'
    but here we only need the readable transcript)."""
    out: list[dict] = []
    for m in recent:
        name = m.get("user_name") or "?"
        content = (m.get("content") or "").strip()
        if content:
            out.append({"role": "user", "content": f"{name}: {content}"})
    return out
