"""`messages.reactions` against a real Postgres (v4.47.0).

The migration is additive (`ADD COLUMN IF NOT EXISTS reactions TEXT[]`) and the
schema pass runs on every connect, so a store built on a fresh database must
accept the column, write it, and hand it back from `get_recent`. Mocks cannot
prove the TEXT[] round-trip or that an older row reads as `[]`.
"""

from __future__ import annotations

import pytest

from tests._pg_fixture import REQUIRES_PG

pytestmark = REQUIRES_PG

CHANNEL = "conv-reactions"


@pytest.mark.asyncio
async def test_a_reaction_only_reply_round_trips(pg_memory_store):
    await pg_memory_store.store(CHANNEL, "907", "Bernard", "user", "mira esto")
    await pg_memory_store.store(CHANNEL, "bot", "Insult", "assistant", "", for_user_id="907", reactions=["👀", "🔥"])

    recent = await pg_memory_store.get_recent(CHANNEL, 10)

    assert [r["role"] for r in recent] == ["user", "assistant"]
    assert recent[1]["content"] == ""
    assert recent[1]["reactions"] == ["👀", "🔥"]


@pytest.mark.asyncio
async def test_a_row_without_reactions_reads_as_an_empty_list(pg_memory_store):
    await pg_memory_store.store(CHANNEL, "907", "Bernard", "user", "hola")
    (row,) = await pg_memory_store.get_recent(CHANNEL, 10)
    assert row["reactions"] == []


@pytest.mark.asyncio
async def test_a_reaction_only_turn_is_not_something_the_persona_said(pg_memory_store):
    """The reflection loop reads what the persona SAID; a bare gesture is not words."""
    await pg_memory_store.store(CHANNEL, "bot", "Insult", "assistant", "Ajá.")
    await pg_memory_store.store(CHANNEL, "bot", "Insult", "assistant", "", reactions=["👀"])
    turns = await pg_memory_store._messages.recent_assistant_turns("Insult")
    assert [t["content"] for t in turns] == ["Ajá."]


@pytest.mark.asyncio
async def test_a_probe_row_is_tagged_and_the_reflection_loop_skips_it(pg_memory_store):
    await pg_memory_store.store(CHANNEL, "bot", "Insult", "assistant", "respuesta real")
    await pg_memory_store.store(CHANNEL, "bot", "Insult", "assistant", "respuesta de probe", origin="probe")

    turns = await pg_memory_store._messages.recent_assistant_turns("Insult")
    assert [t["content"] for t in turns] == ["respuesta real"]
    tagged = await pg_memory_store._messages._fetch(
        "SELECT origin FROM messages WHERE channel_id = $1 ORDER BY id", CHANNEL
    )
    assert [r["origin"] for r in tagged] == [None, "probe"]
