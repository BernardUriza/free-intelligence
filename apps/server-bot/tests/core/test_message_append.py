"""Tests for `append_content_by_discord_id` (v4.21.117).

The write half of the image-transcript trace: the row is stored
synchronously at intake (empty content for an image-only message) and the
vision transcript arrives seconds later from a background task, keyed on
discord_message_id so it lands no matter which deduped writer won the
insert. Runs against a real PG17 with the live `postgres_schema.sql`
applied (see `tests/_pg_fixture.py`).
"""

from __future__ import annotations

from tests._pg_fixture import REQUIRES_PG

pytestmark = REQUIRES_PG

CHANNEL = "999000222"


async def _contents(store) -> list[str]:
    rows = await store.get_recent(CHANNEL, limit=50)
    return [r["content"] for r in rows]


async def test_append_to_empty_row_becomes_transcript(pg_memory_store):
    """The incident shape: an image-only message stores an EMPTY row; the
    transcript append must not leave a leading separator."""
    await pg_memory_store.store(CHANNEL, "907", "bernard", "user", "", discord_message_id="img_1")
    updated = await pg_memory_store.append_to_message("img_1", "[Imagen adjunta: receta HCQ 200mg]")
    assert updated is True
    assert await _contents(pg_memory_store) == ["[Imagen adjunta: receta HCQ 200mg]"]


async def test_append_to_text_row_separates_with_newline(pg_memory_store):
    await pg_memory_store.store(CHANNEL, "907", "bernard", "user", "mira el esquema", discord_message_id="img_2")
    updated = await pg_memory_store.append_to_message("img_2", "[Imagen adjunta: esquema de tratamiento]")
    assert updated is True
    assert await _contents(pg_memory_store) == ["mira el esquema\n[Imagen adjunta: esquema de tratamiento]"]


async def test_append_unknown_id_returns_false_and_touches_nothing(pg_memory_store):
    """Resistance: a transcript for a message that never stored (or was
    pruned) is a no-op, reported as False."""
    await pg_memory_store.store(CHANNEL, "907", "bernard", "user", "hola", discord_message_id="img_3")
    updated = await pg_memory_store.append_to_message("nonexistent", "[Imagen adjunta: x]")
    assert updated is False
    assert await _contents(pg_memory_store) == ["hola"]


async def test_append_never_matches_null_id_rows(pg_memory_store):
    """Resistance: bot replies carry no discord_message_id — an append
    must never mutate them."""
    await pg_memory_store.store(CHANNEL, "bot", "Insult", "assistant", "respuesta")
    updated = await pg_memory_store.append_to_message("respuesta", "[Imagen adjunta: x]")
    assert updated is False
    assert await _contents(pg_memory_store) == ["respuesta"]
