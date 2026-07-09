"""Insult must stay silent when a message addresses a sibling persona (Vultur).

Root cause, 2026-06-21 ("cuando le hablo a vultur, insult viene de metiche"):
the persona_gateway summons a sibling on its OWN role mention (v4.21.91), but
`addressed_to_sibling` only checked user @mentions — so a role-mention to Vultur
slipped past the guard and Insult answered too. This pins BOTH addressing forms,
plus the resistance cases that must NOT suppress Insult.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

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


def test_alias_behind_object_marker_does_not_suppress():
    """The founding P0 case (2026-07-06 17:24Z): Bernard → Alex, 'dile a frugi
    que tienes ahorita…' — talking ABOUT frugi, not TO frugi. The bare alias scan
    muted Insult and (gateway being mention-only then) NOBODY answered for 5
    minutes. An object-marked alias must NOT suppress."""
    assert (
        addressed_to_sibling(
            _msg(
                "ayer me falto mandarte la otra parte de la alacena bb, si quieres "
                "dile a frugi que tienes ahorita para que no alucine que ya te ha "
                "llegado el tahini"
            )
        )
        is False
    )


def test_talking_about_sibling_with_de_does_not_suppress():
    assert addressed_to_sibling(_msg("hablando de frugi, está medio loco no?")) is False


def test_vocative_alias_still_suppresses():
    """RESISTANCE: a real vocative ('frugi, qué opinas…') IS an address — Insult
    stays silent and the gateway (same shared predicate) answers."""
    assert addressed_to_sibling(_msg("frugi, qué opinas de mi lista de alimentos?")) is True


def test_trailing_vocative_alias_still_suppresses():
    assert addressed_to_sibling(_msg("gracias frugi")) is True


def test_object_then_vocative_occurrence_suppresses():
    """Occurrence-wise: object first, vocative second → still an address."""
    assert addressed_to_sibling(_msg("no le hablo a frugi… bueno ya, frugi ayúdame")) is True


# --- what actually keeps the router off an addressed turn -------------------
#
# `_stage_llm_router_cutover` opens with `if ctx.persona_id is not None: return`,
# which reads like the protection. It is not: the prefix was the ONLY thing that
# ever set `persona_id`, and it died with the strangler-fig (88481c9), so that
# guard is unreachable today. The real gate is HERE — `handle_incoming` returns
# before the turn is ever queued, so the pipeline (and the router with it) never
# runs on a message addressed to a sibling. Pin the gate that actually holds.


def _discord_msg(content, *, mention_ids=(), author_bot=False):
    author = SimpleNamespace(id=222, bot=author_bot, display_name="tester")
    channel = SimpleNamespace(id=111, name="general")
    return SimpleNamespace(
        content=content,
        mentions=[SimpleNamespace(id=int(i)) for i in mention_ids],
        guild=None,
        author=author,
        channel=channel,
        id=999,
        attachments=[],
        flags=SimpleNamespace(voice=False),
    )


@pytest.mark.asyncio
async def test_turn_addressed_to_sibling_never_reaches_the_pipeline():
    """A message addressed to a sibling is PERSISTED but never queued, so the LLM
    router stage cannot fire a second summons on top of the sibling's own reply."""
    from personas.insult.cogs.chat.batch import BatchManager

    manager = BatchManager()
    memory = AsyncMock()
    await manager.handle_incoming(
        _discord_msg("frugi, qué ceno hoy?"),
        settings=SimpleNamespace(command_prefix="!"),
        memory=memory,
        bot=SimpleNamespace(),
        flush_callback=AsyncMock(),
        transcribe_voice=AsyncMock(return_value=None),
    )
    assert manager._pending == {}, "an addressed turn must never enter the pipeline"
    memory.store.assert_awaited_once()  # still stored: Insult is the storage gateway


@pytest.mark.asyncio
async def test_unaddressed_turn_does_reach_the_pipeline():
    """RESISTANCE: without the gate firing, the turn queues normally — otherwise the
    test above would pass on a batcher that drops everything."""
    from personas.insult.cogs.chat.batch import BatchManager

    manager = BatchManager()
    await manager.handle_incoming(
        _discord_msg("hoy sentí mucha presión en el trabajo"),
        settings=SimpleNamespace(command_prefix="!"),
        memory=AsyncMock(),
        bot=SimpleNamespace(),
        flush_callback=AsyncMock(),
        transcribe_voice=AsyncMock(return_value=None),
    )
    assert manager._pending, "an unaddressed turn must be queued for the pipeline"
