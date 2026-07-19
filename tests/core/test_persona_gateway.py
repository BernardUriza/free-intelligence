"""Khimeras persona gateway — activation gate + text helpers.

The gateway is mention-gated and must never auto-invoke or answer another bot
(prevents Insult ↔ Vultur loops). Mutator rule: positive (mention from a human
fires) + resistance (no mention / bot author / not-ready all stay silent).
"""

from __future__ import annotations

from types import SimpleNamespace

from persona_gateway.gateway import chunk, clean_mention, edit_summons, format_context, should_respond


def _user(uid: int):
    return SimpleNamespace(id=uid)


def _role(rid: int):
    return SimpleNamespace(id=rid)


def _guild(gid: int, bot_role_ids: list[int]):
    """A guild whose `me` (the bot member) carries `bot_role_ids` plus @everyone
    (whose role id equals the guild id, by Discord convention)."""
    me = SimpleNamespace(roles=[_role(gid), *(_role(r) for r in bot_role_ids)])
    return SimpleNamespace(id=gid, me=me)


def _msg(
    *,
    author_bot: bool,
    mentions: list,
    content: str = "",
    role_mentions: list | None = None,
    guild=None,
    reply_to=None,
):
    """`reply_to` is the resolved author of the message being replied to (or None
    for a non-reply) — mirrors `message.reference.resolved.author`."""
    reference = None
    if reply_to is not None:
        reference = SimpleNamespace(resolved=SimpleNamespace(author=reply_to), cached_message=None)
    return SimpleNamespace(
        author=SimpleNamespace(bot=author_bot),
        mentions=mentions,
        content=content,
        role_mentions=role_mentions or [],
        guild=guild,
        reference=reference,
    )


# --- should_respond ---------------------------------------------------------


def test_responds_to_mention_from_human():
    bot = _user(123)
    msg = _msg(author_bot=False, mentions=[bot])
    assert should_respond(msg, bot) is True


def test_ignores_message_without_mention():
    # RESISTANCE: not mentioned → silent (opt-in by design).
    bot = _user(123)
    msg = _msg(author_bot=False, mentions=[_user(999)])
    assert should_respond(msg, bot) is False


def test_responds_to_reply_to_this_bot():
    # POSITIVE: a REPLY to this bot's message addresses it — the only channel a
    # voice note has (audio carries no text and can't @mention). 2026-07-18.
    bot = _user(123)
    msg = _msg(author_bot=False, mentions=[], reply_to=bot)
    assert should_respond(msg, bot) is True


def test_reply_to_another_author_does_not_fire():
    # RESISTANCE: a reply to SOMEONE ELSE's message (a human, or a sibling bot)
    # must NOT summon this bot — only a reply to ITS OWN message does.
    bot = _user(123)
    msg = _msg(author_bot=False, mentions=[], reply_to=_user(999))
    assert should_respond(msg, bot) is False


def test_reply_by_bot_author_still_ignored():
    # RESISTANCE: even a reply to this bot, if AUTHORED by a bot, stays silent —
    # the author.bot guard (no Insult↔Vultur loops) outranks the reply channel.
    bot = _user(123)
    msg = _msg(author_bot=True, mentions=[], reply_to=bot)
    assert should_respond(msg, bot) is False


def test_ignores_bot_author_even_if_mentioned():
    # RESISTANCE: another bot @mentions Vultur → must NOT answer (no loops).
    bot = _user(123)
    msg = _msg(author_bot=True, mentions=[bot])
    assert should_respond(msg, bot) is False


def test_host_owns_reception_makes_persona_invite_only():
    # CUTOVER (#6): when the host owns reception, a DIRECT mention that would
    # normally fire must NOT self-answer — the host routes + summons via /invite,
    # so self-answering here is the double-answer ("dos bots peleando").
    bot = _user(123)
    msg = _msg(author_bot=False, mentions=[bot])
    assert should_respond(msg, bot, host_owns_reception=True) is False


def test_host_owns_reception_default_false_preserves_self_answer():
    # RESISTANCE: the flag defaults False (pre-cutover), so the SAME mention that
    # is muted above still fires normally — the switch changes nothing until flipped.
    bot = _user(123)
    msg = _msg(author_bot=False, mentions=[bot])
    assert should_respond(msg, bot) is True
    assert should_respond(msg, bot, host_owns_reception=False) is True


def test_ignores_when_not_ready():
    # RESISTANCE: before on_ready, self.user is None.
    msg = _msg(author_bot=False, mentions=[])
    assert should_respond(msg, None) is False


def test_responds_to_own_role_mention():
    # POSITIVE: pinging the bot's OWN role (the classic "I pinged the bot's role
    # expecting it to ping the bot" gotcha) summons it, same as a user mention.
    bot = _user(123)
    bot_role = _role(456)
    guild = _guild(gid=789, bot_role_ids=[456])
    msg = _msg(author_bot=False, mentions=[], role_mentions=[bot_role], guild=guild)
    assert should_respond(msg, bot) is True


def test_ignores_everyone_role_mention():
    # RESISTANCE: @everyone has role id == guild id; it must NEVER summon the bot
    # even though the bot trivially "has" @everyone (mass-ping safe).
    bot = _user(123)
    everyone = _role(789)
    guild = _guild(gid=789, bot_role_ids=[456])
    msg = _msg(author_bot=False, mentions=[], role_mentions=[everyone], guild=guild)
    assert should_respond(msg, bot) is False


def test_ignores_role_the_bot_does_not_have():
    # RESISTANCE: pinging some OTHER role the bot isn't in → silent.
    bot = _user(123)
    other_role = _role(999)
    guild = _guild(gid=789, bot_role_ids=[456])
    msg = _msg(author_bot=False, mentions=[], role_mentions=[other_role], guild=guild)
    assert should_respond(msg, bot) is False


def test_responds_to_vocative_alias_without_mention():
    """P0 2026-07-06: Insult muted on the alias while the gateway needed a
    mention → nobody answered. The gateway now fires on a vocative alias of ITS
    persona — the complement of Insult's suppression gate."""
    bot = _user(1)
    msg = _msg(author_bot=False, mentions=[], content="frugi, qué opinas de mi lista?")
    assert should_respond(msg, bot, ["frugivoro", "frugi"]) is True


def test_ignores_alias_behind_object_marker():
    """RESISTANCE (the founding case): 'dile a frugi que…' talks ABOUT frugi to
    someone else — the gateway must NOT fire (Insult answers as usual)."""
    bot = _user(1)
    msg = _msg(
        author_bot=False,
        mentions=[],
        content="si quieres dile a frugi que tienes ahorita para que no alucine",
    )
    assert should_respond(msg, bot, ["frugivoro", "frugi"]) is False


def test_alias_never_summons_when_message_opens_addressing_insult():
    """Head-wins parity with Insult's gate: 'insult, pregúntale a frugi…' is a
    request TO Insult — even a vocative-looking alias later must not summon."""
    bot = _user(1)
    msg = _msg(author_bot=False, mentions=[], content="insult, frugi está exagerando?")
    assert should_respond(msg, bot, ["frugivoro", "frugi"]) is False


def test_ignores_vocative_alias_from_bot_author():
    """RESISTANCE: another bot saying the alias must never summon (loop guard)."""
    bot = _user(1)
    msg = _msg(author_bot=True, mentions=[], content="frugi, contesta tú")
    assert should_respond(msg, bot, ["frugivoro", "frugi"]) is False


def test_no_aliases_arg_keeps_mention_only_behavior():
    """RESISTANCE: callers not passing aliases (default) keep the old gate."""
    bot = _user(1)
    msg = _msg(author_bot=False, mentions=[], content="frugi, contesta")
    assert should_respond(msg, bot) is False


def test_ignores_own_role_mention_from_bot_author():
    # RESISTANCE: another bot pings Vultur's role → must NOT answer (no loops).
    bot = _user(123)
    bot_role = _role(456)
    guild = _guild(gid=789, bot_role_ids=[456])
    msg = _msg(author_bot=True, mentions=[], role_mentions=[bot_role], guild=guild)
    assert should_respond(msg, bot) is False


# --- edit_summons (P0 2026-07-06: mention edited in AFTER send) --------------


def test_edit_that_adds_mention_summons():
    """Alex sent his pantry list clean and edited in '@frugi' — on_message had
    already run on the clean content, so the mention summoned nobody."""
    bot = _user(1)
    before = _msg(author_bot=False, mentions=[], content="Avena, chía, zanahorias")
    after = _msg(author_bot=False, mentions=[bot], content="Avena, chía, zanahorias @frugi")
    assert edit_summons(before, after, bot, ["frugi"]) is True


def test_edit_of_already_addressed_message_never_retriggers():
    """RESISTANCE: fixing a typo in a message the persona already answered must
    not summon it twice."""
    bot = _user(1)
    before = _msg(author_bot=False, mentions=[bot], content="frugi qué opinas de la avena")
    after = _msg(author_bot=False, mentions=[bot], content="frugi qué opinas de la avena?")
    assert edit_summons(before, after, bot, ["frugi"]) is False


def test_edit_without_address_stays_silent():
    bot = _user(1)
    before = _msg(author_bot=False, mentions=[], content="hola")
    after = _msg(author_bot=False, mentions=[], content="hola a todos")
    assert edit_summons(before, after, bot, ["frugi"]) is False


# --- clean_mention ----------------------------------------------------------


def test_clean_strips_own_mention():
    assert clean_mention("<@123> reséñame Creep", 123) == "reséñame Creep"
    assert clean_mention("<@!123> reséñame Creep", 123) == "reséñame Creep"


def test_clean_keeps_other_mentions():
    # Only THIS bot's mention is removed; others are meaningful context.
    out = clean_mention("<@999> y <@123> opina", 123)
    assert "<@999>" in out
    assert "<@123>" not in out


def test_clean_bare_mention_is_empty():
    assert clean_mention("<@123>", 123) == ""


# --- format_context ---------------------------------------------------------


def test_format_prefixes_speaker_and_skips_empty():
    recent = [
        {"user_name": "Bernard", "content": "pon Creep"},
        {"user_name": "Alex", "content": ""},  # dropped
        {"user_name": "Insult", "content": "va"},
    ]
    out = format_context(recent)
    assert out == [
        {"role": "user", "content": "Bernard: pon Creep"},
        {"role": "user", "content": "Insult: va"},
    ]


# --- chunk ------------------------------------------------------------------


def test_chunk_short_single_piece():
    assert chunk("hola") == ["hola"]


def test_chunk_empty_is_no_pieces():
    assert chunk("") == []
    assert chunk("   ") == []


def test_chunk_long_splits_under_limit():
    text = ("palabra " * 600).strip()  # ~4800 chars
    pieces = chunk(text, limit=1990)
    assert len(pieces) >= 2
    assert all(len(p) <= 1990 for p in pieces)
    # no content lost (modulo whitespace joins)
    assert "".join(pieces).replace(" ", "") == text.replace(" ", "")
