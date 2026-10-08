"""Tests for the messages-table discord_message_id dedupe (v4.21.116).

The Insult plumbing (canonical storage gateway) and every persona_gateway
sibling each receive the same Discord message on their own gateway
connection and persist it into the shared Postgres — before the dedupe key
every sibling-addressed turn landed TWICE (observed 7ms apart in prod,
2026-07-05, the "@frugi cross-talk"). The unique partial index on
discord_message_id + ON CONFLICT DO NOTHING makes the write idempotent per
Discord message, first writer wins.

Runs against a real PG17 with the live `postgres_schema.sql` applied — the
same DDL prod runs (see `tests/_pg_fixture.py`).
"""

from __future__ import annotations

from tests._pg_fixture import REQUIRES_PG

pytestmark = REQUIRES_PG

CHANNEL = "999000111"


async def _stored_contents(store) -> list[str]:
    rows = await store.get_recent(CHANNEL, limit=50)
    return [r["content"] for r in rows]


async def test_second_writer_same_discord_id_is_deduped(pg_memory_store):
    """The colliding pair: Insult stores the raw mention text, the sibling
    gateway stores the stripped text 7ms later with the same message id —
    only the first row survives."""
    await pg_memory_store.store(
        CHANNEL, "907", "bernard", "user", "<@152> corrige tu lista", discord_message_id="msg_1"
    )
    await pg_memory_store.store(CHANNEL, "907", "bernard", "user", "corrige tu lista", discord_message_id="msg_1")
    contents = await _stored_contents(pg_memory_store)
    assert contents == ["<@152> corrige tu lista"]


async def test_distinct_discord_ids_both_insert(pg_memory_store):
    """Resistance: two real, different messages must never be collapsed —
    even with identical content (a user repeating themselves)."""
    await pg_memory_store.store(CHANNEL, "907", "bernard", "user", "hola", discord_message_id="msg_a")
    await pg_memory_store.store(CHANNEL, "907", "bernard", "user", "hola", discord_message_id="msg_b")
    assert len(await _stored_contents(pg_memory_store)) == 2


async def test_null_discord_id_never_conflicts(pg_memory_store):
    """Resistance: bot replies / proactive stores carry no Discord message
    id — repeated NULLs must all insert (partial index excludes NULL)."""
    await pg_memory_store.store(CHANNEL, "bot", "Insult", "assistant", "respuesta 1")
    await pg_memory_store.store(CHANNEL, "bot", "Insult", "assistant", "respuesta 2")
    await pg_memory_store.store(CHANNEL, "bot", "Insult", "assistant", "respuesta 3")
    assert len(await _stored_contents(pg_memory_store)) == 3
