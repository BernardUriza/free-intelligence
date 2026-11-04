"""`runtime_personas` against a REAL Postgres — append-only, newest row wins.

Positive: two versions of one persona and one of another come back as exactly two
rows, each the newest. Resistance: an unknown provider never lands (the CHECK
constraint is the last wall behind the runner's own validation).
"""

from __future__ import annotations

import asyncpg
import pytest

from tests._pg_fixture import REQUIRES_PG

pytestmark = REQUIRES_PG


def _write(repo, persona_id, dna, provider="claude", model=None):
    return repo.append(
        persona_id=persona_id, display_name=persona_id.title(), provider=provider, model=model, dna=dna, created_by="t"
    )


@pytest.mark.asyncio
async def test_latest_returns_the_newest_version_per_persona(pg_memory_store):
    repo = pg_memory_store.runtime_personas
    await _write(repo, "radon", "v1")
    newest = await _write(repo, "radon", "v2", provider="codex", model="gpt-6-astra")
    await _write(repo, "xenon", "x1")

    rows = {r.persona_id: r for r in await repo.latest()}
    assert set(rows) == {"radon", "xenon"}
    assert rows["radon"].dna == "v2" and rows["radon"].version == newest
    assert rows["radon"].provider == "codex" and rows["radon"].model == "gpt-6-astra"


@pytest.mark.asyncio
async def test_an_unknown_provider_never_lands(pg_memory_store):
    repo = pg_memory_store.runtime_personas
    with pytest.raises(asyncpg.CheckViolationError):
        await _write(repo, "radon", "v1", provider="gemini", model="x")
    assert await repo.latest() == []


@pytest.mark.asyncio
async def test_a_tombstone_hides_the_persona_and_a_new_write_revives_it(pg_memory_store):
    repo = pg_memory_store.runtime_personas
    await _write(repo, "radon", "v1")
    await _write(repo, "xenon", "x1")

    assert await repo.tombstone(persona_id="radon", deleted_by="t") is not None
    assert {r.persona_id for r in await repo.latest()} == {"xenon"}

    await _write(repo, "radon", "v3")
    rows = {r.persona_id: r for r in await repo.latest()}
    assert rows["radon"].dna == "v3"


@pytest.mark.asyncio
async def test_a_tombstone_for_an_unknown_id_writes_nothing(pg_memory_store):
    repo = pg_memory_store.runtime_personas
    assert await repo.tombstone(persona_id="ghost", deleted_by="t") is None
    assert await repo.latest() == []
