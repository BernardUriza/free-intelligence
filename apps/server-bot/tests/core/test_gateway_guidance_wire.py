"""The guardian ON THE WIRE — the overlay must leave the process.

Building the guidance is worthless if nobody sends it. This is the contract test
for the seam the purge broke: `_handle` (a mention turn) must classify the user
against their facts and hand `behavioral_guidance` to `agent_client.chat`, which
forwards it to the runner (which injects it into the user message —
`persona_runner.engine.framing.frame_turn_text`).

Positive: a user with a clinical cluster → the kwarg on the runner call carries
the overlay. Resistance: a normal user → a turn with no overlay; a dead fact store
→ the turn STILL ships (unscored, no overlay) instead of going mute — AND acute
distress in the current message still activates the overlay on its own, so the
crisis safety net never depends on Postgres being up.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona

ALEX_FACTS = [
    {"id": 1, "fact": "fue diagnosticada con CPTSD por su psiquiatra", "category": "salud"},
    {"id": 2, "fact": "toma quetiapina cada noche", "category": "salud"},
]

OVERLAY_MARKERS = ("saptel", "línea de la vida", "medlineplus")


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _client(facts, *, facts_raise: bool = False) -> PersonaClient:
    persona = Persona(
        persona_id="insult",
        display_name="Insult",
        persona_file="insult.md",
        token_env="INSULT_DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_recent = AsyncMock(return_value=[])
    memory.get_facts = AsyncMock(side_effect=RuntimeError("pg down") if facts_raise else None, return_value=facts)
    memory.get_auto_facts = AsyncMock(return_value=[])
    memory.save_facts = AsyncMock()
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text="respuesta", model_used="claude"))
    judge = MagicMock()
    judge.utility_call = AsyncMock(return_value=SimpleNamespace(text="[]", stop_reason="end_turn"))
    return PersonaClient(
        persona,
        memory,
        agent_client,
        intents=discord.Intents.none(),
        judge_client=judge,
    )


def _message(text: str) -> MagicMock:
    msg = MagicMock()
    msg.id = 1526655478313127987
    msg.content = text
    msg.channel = MagicMock(spec=discord.TextChannel)
    msg.channel.id = 1489180895264116736
    msg.channel.send = AsyncMock()
    msg.channel.typing = MagicMock(return_value=_Typing())
    msg.author = MagicMock()
    msg.author.id = 1431300030823927999
    msg.author.display_name = "Alex"
    msg.author.bot = False
    msg.guild = None
    msg.attachments = []
    msg.flags.voice = False
    return msg


def _guidance_sent(client: PersonaClient) -> str | None:
    return client.agent_client.chat.await_args.kwargs.get("behavioral_guidance")


def _has_overlay(text: str | None) -> bool:
    low = (text or "").lower()
    return any(m in low for m in OVERLAY_MARKERS)


async def test_clinical_user_turn_carries_the_overlay_to_the_runner():
    client = _client(ALEX_FACTS)
    await client._handle(_message("ya no puedo con la ansiedad, llevo días sin dormir"))
    client.agent_client.chat.assert_awaited_once()
    guidance = _guidance_sent(client)
    assert guidance, "el gateway no mandó NINGUNA guidance"
    assert _has_overlay(guidance), "la guidance viajó SIN el overlay clínico"


async def test_normal_user_turn_carries_guidance_without_overlay():
    """RESISTANCE: the overlay is for clinical clusters, not for everyone."""
    client = _client([])
    await client._handle(_message("qué opinas del disco nuevo"))
    client.agent_client.chat.assert_awaited_once()
    assert not _has_overlay(_guidance_sent(client))


async def test_dead_fact_store_still_delivers_the_turn_unscored():
    """RESISTANCE: a fact-store fault costs the SCORE, never the turn. The bot
    answering unscored is bad; the bot going MUTE is worse. Guidance still
    renders (the persona's normal register) — it just carries no overlay,
    because with no facts there is no cluster to detect."""
    client = _client([], facts_raise=True)
    await client._handle(_message("hola"))
    client.agent_client.chat.assert_awaited_once()
    assert not _has_overlay(_guidance_sent(client))
    client.memory.store.assert_awaited()


async def test_acute_crisis_reaches_the_overlay_even_with_a_dead_fact_store():
    """THE SAFETY NET THAT MUST NEVER DEPEND ON POSTGRES: acute distress in the
    CURRENT message activates the overlay on its own (priority 0 of the
    classifier), so a user in crisis is protected even when the fact store — and
    therefore the chronic-vulnerability score — is unavailable."""
    client = _client([], facts_raise=True)
    await client._handle(_message("ya no puedo más, quiero desaparecer"))
    guidance = _guidance_sent(client)
    assert guidance and _has_overlay(guidance)
