"""Gateway fact-extraction wiring — longitudinal memory grows again.

THE BUG this locks out (P0 2026-07-14): post-castigo NO writer of user-facts
survived — `merge_facts_additive` died with `personas/` and nothing replaced it,
so the `source='auto'` tier stopped growing entirely. The bot's longitudinal
memory was read-only.

THE GUARD: the gateway mines a mention turn in the background and persists the
extractor's output UNIONED onto the full live auto set — never the raw subset
(`save_facts(subset)` is a DELETE-all-and-reinsert in disguise).

Mutator rule: positive (mention → extract → additive save) + resistance (a dead
judge, a failing save, or no new facts must never break the delivered turn).
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import httpx

from persona_gateway.gateway import PersonaClient
from shared.personas import Persona


def _client(judge_text: str = "[]", judge_client=None) -> PersonaClient:
    persona = Persona(
        persona_id="vultur",
        display_name="Vultur Analytica",
        persona_file="vultur.md",
        token_env="VULTUR_DISCORD_TOKEN",
    )
    memory = MagicMock()
    memory.store = AsyncMock()
    memory.get_facts = AsyncMock(return_value=[])
    memory.get_auto_facts = AsyncMock(return_value=[])
    memory.save_facts = AsyncMock()
    agent_client = MagicMock()
    agent_client.chat = AsyncMock(return_value=SimpleNamespace(text="ok", model_used="claude"))
    if judge_client is None:
        judge_client = MagicMock()
        judge_client.utility_call = AsyncMock(
            return_value=SimpleNamespace(text=judge_text, stop_reason="end_turn"),
        )
    return PersonaClient(
        persona,
        memory,
        agent_client,
        intents=discord.Intents.none(),
        judge_client=judge_client,
    )


async def _extract(client: PersonaClient, recent=None) -> None:
    """Drive the background extraction the way `_handle` spawns it."""
    client._spawn_fact_extraction(
        "U1",
        "Bernard",
        recent if recent is not None else [{"user_name": "Bernard", "content": "vivo en GDL"}],
    )
    await asyncio.gather(*list(client._bg_tasks))


async def test_extraction_saves_the_superset_not_the_extractor_subset():
    """THE guard: `get_auto_facts` holds 4 facts; the extractor (which only saw a
    subset) returns 2 + 1 new. `save_facts` must receive all 4 + the new one = 5,
    NOT the extractor's 3 — anything less is a per-turn hard delete."""
    client = _client(judge_text='[{"fact": "A", "category": "personal"}, {"fact": "E nuevo", "category": "personal"}]')
    client.memory.get_auto_facts = AsyncMock(
        return_value=[
            {"id": 1, "fact": "A", "category": "personal"},
            {"id": 2, "fact": "B", "category": "personal"},
            {"id": 3, "fact": "C", "category": "personal"},
            {"id": 4, "fact": "D", "category": "personal"},
        ]
    )

    await _extract(client)

    client.memory.save_facts.assert_awaited_once()
    saved = client.memory.save_facts.await_args.args[1]
    assert {f["fact"] for f in saved} == {"A", "B", "C", "D", "E nuevo"}


async def test_extraction_skips_the_save_when_nothing_is_new():
    """No genuinely-new fact → no save at all (no needless snapshot churn)."""
    client = _client(judge_text='[{"fact": "A", "category": "personal"}]')
    client.memory.get_auto_facts = AsyncMock(return_value=[{"id": 1, "fact": "A", "category": "personal"}])

    await _extract(client)

    client.memory.save_facts.assert_not_awaited()


async def test_extraction_persists_a_brand_new_user_first_fact():
    client = _client(judge_text='[{"fact": "Vive en GDL", "category": "location"}]')

    await _extract(client)

    saved = client.memory.save_facts.await_args.args[1]
    assert saved == [{"fact": "Vive en GDL", "category": "location"}]


async def test_a_dead_judge_never_wipes_facts_and_never_raises():
    """RESISTANCE: /v1/judge down → extraction degrades to 'nothing new'. It must
    NOT save (which, with an empty extractor result, would be a wipe) and must not
    raise into the background task."""
    judge = MagicMock()
    judge.utility_call = AsyncMock(side_effect=httpx.ConnectError("runner down"))
    client = _client(judge_client=judge)
    client.memory.get_auto_facts = AsyncMock(return_value=[{"id": 1, "fact": "A", "category": "personal"}])

    await _extract(client)

    client.memory.save_facts.assert_not_awaited()


async def test_a_failing_save_is_swallowed():
    """RESISTANCE: a dead DB in the backstop never escapes the background task."""
    client = _client(judge_text='[{"fact": "nuevo", "category": "general"}]')
    client.memory.save_facts = AsyncMock(side_effect=RuntimeError("pg down"))

    await _extract(client)  # must not raise

    client.memory.save_facts.assert_awaited_once()


async def test_no_judge_client_disables_extraction_silently():
    """RESISTANCE: a gateway with no judge wired still serves turns — extraction is
    simply off, and nothing is spawned."""
    client = _client()
    client.judge_client = None

    client._spawn_fact_extraction("U1", "Bernard", [{"user_name": "B", "content": "x"}])

    assert not client._bg_tasks
    client.memory.save_facts.assert_not_awaited()


async def test_extraction_reads_the_current_turn_text():
    """The user's ask of THIS turn is what gets mined — not just old context."""
    client = _client(judge_text="[]")

    await _extract(client, recent=[{"user_name": "Bernard", "content": "me acaban de operar la rodilla"}])

    conversation = client.judge_client.utility_call.await_args.args[1][0]["content"]
    assert "me acaban de operar la rodilla" in conversation
    assert "Bernard" in conversation


# --------------------------------------------------------------------------
# End-to-end: a real mention turn spawns the backstop
# --------------------------------------------------------------------------


class _Typing:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _message(content: str) -> MagicMock:
    channel = MagicMock()
    channel.id = 42
    channel.name = "general"
    channel.send = AsyncMock()
    channel.typing = MagicMock(return_value=_Typing())
    msg = MagicMock()
    msg.channel = channel
    msg.author = SimpleNamespace(id=907, display_name="Bernard", bot=False)
    msg.guild = SimpleNamespace(id=1)
    msg.content = content
    msg.id = 5
    msg.attachments = []
    msg.flags = SimpleNamespace(voice=False)
    return msg


async def test_a_mention_turn_mines_the_ask_and_saves_additively():
    """END-TO-END: the delivered mention turn is what feeds the fact backstop.

    This is the seam that was severed — a turn used to be delivered and NOTHING
    ever wrote a fact from it."""
    client = _client(judge_text='[{"fact": "Le operaron la rodilla", "category": "personal"}]')
    client.memory.get_recent = AsyncMock(return_value=[])

    await client._handle(_message("me acaban de operar la rodilla"))
    await asyncio.gather(*list(client._bg_tasks))

    saved = client.memory.save_facts.await_args.args[1]
    assert saved == [{"fact": "Le operaron la rodilla", "category": "personal"}]
    conversation = client.judge_client.utility_call.await_args.args[1][0]["content"]
    assert "me acaban de operar la rodilla" in conversation
