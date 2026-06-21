"""Insult must stay silent when a message addresses a sibling persona (Vultur).

Root cause, 2026-06-21 ("cuando le hablo a vultur, insult viene de metiche"):
the persona_gateway summons a sibling on its OWN role mention (v4.21.91), but
`addressed_to_sibling` only checked user @mentions — so a role-mention to Vultur
slipped past the guard and Insult answered too. This pins BOTH addressing forms,
plus the resistance cases that must NOT suppress Insult.
"""

from __future__ import annotations

from types import SimpleNamespace

from personas.insult.cogs.chat.batch import addressed_to_sibling
from shared.personas.registry import sibling_bot_user_ids

VULTUR_ID = next(iter(sibling_bot_user_ids()))  # a real registered sibling bot id


def _msg(content="", *, mention_ids=(), roles=None):
    m = SimpleNamespace()
    m.content = content
    m.mentions = [SimpleNamespace(id=int(i)) for i in mention_ids]
    m.guild = None if roles is None else SimpleNamespace(roles=roles)
    return m


def _role(role_id, bot_id):
    return SimpleNamespace(id=int(role_id), tags=SimpleNamespace(bot_id=int(bot_id)))


def test_user_mention_to_sibling_suppresses_insult():
    assert addressed_to_sibling(_msg("recomiéndame una peli", mention_ids=[VULTUR_ID])) is True


def test_role_mention_to_sibling_managed_role_suppresses_insult():
    """The metiche fix: Discord inserts the sibling's managed role pill."""
    roles = [_role("777", bot_id=VULTUR_ID)]
    assert addressed_to_sibling(_msg("<@&777> qué opinas de Dune", roles=roles)) is True


def test_role_mention_to_non_sibling_does_not_suppress():
    """RESISTANCE: a role pill for some OTHER bot/role must NOT silence Insult."""
    roles = [_role("888", bot_id=999999999999999999)]
    assert addressed_to_sibling(_msg("<@&888> hola", roles=roles)) is False


def test_plain_text_vultur_does_not_suppress():
    """RESISTANCE: the word 'vultur' in film talk is not an address — Insult answers."""
    assert addressed_to_sibling(_msg("vultur me cae bien como crítico")) is False


def test_no_mention_no_suppression():
    assert addressed_to_sibling(_msg("qué pedo con la peli")) is False
