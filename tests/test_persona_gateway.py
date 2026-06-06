"""Khimeras persona gateway — activation gate + text helpers.

The gateway is mention-gated and must never auto-invoke or answer another bot
(prevents Insult ↔ Vultur loops). Mutator rule: positive (mention from a human
fires) + resistance (no mention / bot author / not-ready all stay silent).
"""

from __future__ import annotations

from types import SimpleNamespace

from persona_gateway.gateway import chunk, clean_mention, format_context, should_respond


def _user(uid: int):
    return SimpleNamespace(id=uid)


def _msg(*, author_bot: bool, mentions: list, content: str = ""):
    return SimpleNamespace(author=SimpleNamespace(bot=author_bot), mentions=mentions, content=content)


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


def test_ignores_bot_author_even_if_mentioned():
    # RESISTANCE: another bot @mentions Vultur → must NOT answer (no loops).
    bot = _user(123)
    msg = _msg(author_bot=True, mentions=[bot])
    assert should_respond(msg, bot) is False


def test_ignores_when_not_ready():
    # RESISTANCE: before on_ready, self.user is None.
    msg = _msg(author_bot=False, mentions=[])
    assert should_respond(msg, None) is False


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
