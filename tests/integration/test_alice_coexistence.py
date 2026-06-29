"""Insult ↔ ALICE coexistence: Insult stays silent when a message DIRECTLY
addresses ALICE, so the two bots don't double-reply (v4.7.0).

Post-PR-4c, ALICE is suppressed through the SAME registry-driven gate as every
other sibling (`addressed_to_sibling`) — her id + text aliases live in
`shared/personas/registry.py`, no hardcoded special case in Insult. These tests
lock the positive cases (suppress) AND the resistance cases (do NOT suppress an
ordinary message or a shared-context clinical keyword) per the mutator rule in
.claude/rules/robustness.md.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from personas.insult.cogs.chat.batch import addressed_to_sibling

# ALICE's registered bot user id (shared/personas/registry.py).
ALICE_ID = "1503983124982534284"


def _msg(content="", *, mention_ids=(), roles=None):
    m = MagicMock()
    m.content = content
    m.mentions = [SimpleNamespace(id=int(i)) for i in mention_ids]
    if roles is None:
        m.guild = None
    else:
        m.guild = SimpleNamespace(roles=roles)
    return m


def _role(role_id, bot_id):
    return SimpleNamespace(id=int(role_id), tags=SimpleNamespace(bot_id=int(bot_id)))


# --- positive: suppress (ALICE is being addressed) ------------------------


def test_user_mention_via_mentions_list():
    assert addressed_to_sibling(_msg("sigues viva?", mention_ids=[ALICE_ID])) is True


def test_user_mention_via_raw_pill_in_content():
    # The raw <@id> pill also lands in message.mentions for a real Discord event.
    assert addressed_to_sibling(_msg(f"<@{ALICE_ID}> sigues viva?", mention_ids=[ALICE_ID])) is True


def test_role_mention_to_alice_managed_role():
    roles = [_role("999", bot_id=ALICE_ID)]  # ALICE's managed role
    assert addressed_to_sibling(_msg("<@&999> sigues viva?", roles=roles)) is True


def test_text_alias_amix():
    assert addressed_to_sibling(_msg("amix, ¿ya quedaste?")) is True


def test_text_word_alice():
    assert addressed_to_sibling(_msg("oye alice qué opinas")) is True


# --- resistance: do NOT suppress (Insult should still answer) --------------


def test_unrelated_message_not_suppressed():
    assert addressed_to_sibling(_msg("¿quién ganó el partido?")) is False


def test_clinical_keyword_alone_not_suppressed():
    """Shared-context word like 'terapeuta' must NOT silence Insult — that's
    not direct address, and ALICE's intrusive mode (not mirrored here) owns it."""
    assert addressed_to_sibling(_msg("mi terapeuta me dijo algo raro")) is False


def test_other_bot_mention_not_suppressed():
    """A mention of some OTHER user/bot must not trip sibling suppression."""
    assert addressed_to_sibling(_msg("<@111111> ayuda", mention_ids=["111111"])) is False


def test_alias_substring_does_not_false_positive():
    """'ali' is word-bounded — 'realidad' / 'natalia' must not match."""
    assert addressed_to_sibling(_msg("la realidad es complicada, Natalia")) is False
