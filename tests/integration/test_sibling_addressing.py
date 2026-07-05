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


def test_opens_addressing_insult_overrides_sibling_alias():
    """The 2026-07-04 prod case: 'insult, invita a alice' is a request TO Insult
    that names a sibling — it must reach Insult (invoke_alice can fire)."""
    assert addressed_to_sibling(_msg("insult, invita a alice al canal — quiero su lectura")) is False


def test_opens_addressing_insult_case_insensitive_with_at():
    assert addressed_to_sibling(_msg("@Insult llama a amix porfa")) is False


def test_opens_addressing_insult_own_mention_pill():
    """A leading @Insult mention pill also heads the message to the host."""
    m = _msg("<@111222333> invita a alice")
    m.guild = SimpleNamespace(roles=[], me=SimpleNamespace(id=111222333))
    assert addressed_to_sibling(m) is False


def test_opens_addressing_sibling_still_suppresses():
    """RESISTANCE: opening with the sibling's alias keeps Insult silent even if
    'insult' appears later — the head of the message wins in both directions."""
    assert addressed_to_sibling(_msg("alice, dile a insult que se calme")) is True


def test_insultante_prefix_does_not_unmute():
    """RESISTANCE: 'insultante…' is not an address to Insult (word boundary);
    the sibling alias later still suppresses."""
    assert addressed_to_sibling(_msg("insultante lo de ayer, alice qué opinas")) is True
