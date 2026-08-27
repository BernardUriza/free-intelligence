"""Tests for the facts persistence contract — the bug that mattered.

Before v3.4.10 `save_facts` did a blanket `DELETE FROM user_facts WHERE
user_id=?` and re-inserted whatever the LLM returned. Because extract_facts
only sees the last ~10 messages, anything older (manual injections, older
auto-extractions) routinely got wiped on the NEXT conversation turn.

These tests lock in the new contract:
- Rows with source='manual' NEVER get deleted by save_facts.
- Rows with source='auto' are replaced atomically per save_facts call.
- add_manual_fact writes with source='manual' and returns the row id.
- The save_facts transaction is atomic — a mid-save crash never leaves
  the table half-wiped (Postgres MVCC + repo's `_tx()` wrapper).

Post-PG migration: runs against ephemeral PG17 with pgvector via
`pytest-postgresql`. Each test gets a clean DB; the contract is verified
end-to-end through the same `asyncpg.Pool` path prod uses.
"""

from __future__ import annotations

import pytest

from tests._pg_fixture import REQUIRES_PG

pytestmark = REQUIRES_PG


@pytest.mark.asyncio
async def test_add_manual_fact_inserts_with_manual_source(pg_memory_store):
    row_id = await pg_memory_store.add_manual_fact("u1", "Es de Orange County", "identity")
    assert row_id > 0
    facts = await pg_memory_store.get_facts("u1")
    assert len(facts) == 1
    assert facts[0]["fact"] == "Es de Orange County"
    assert facts[0]["category"] == "identity"


@pytest.mark.asyncio
async def test_save_facts_preserves_manual_rows(pg_memory_store):
    manual_id = await pg_memory_store.add_manual_fact("u1", "Es de Orange County, CA", "identity")
    await pg_memory_store.save_facts(
        "u1",
        [
            {"fact": "Le gusta Python", "category": "interests"},
            {"fact": "Vive en CDMX", "category": "location"},
        ],
    )
    facts = await pg_memory_store.get_facts("u1")
    assert len(facts) == 3, "auto save must not wipe the manual fact"
    texts = {f["fact"] for f in facts}
    assert "Es de Orange County, CA" in texts
    assert "Le gusta Python" in texts
    assert "Vive en CDMX" in texts
    assert any(f["id"] == manual_id and f["fact"] == "Es de Orange County, CA" for f in facts)


@pytest.mark.asyncio
async def test_save_facts_replaces_previous_auto_rows(pg_memory_store):
    await pg_memory_store.save_facts("u1", [{"fact": "Old fact A", "category": "personal"}])
    await pg_memory_store.save_facts("u1", [{"fact": "Old fact B", "category": "personal"}])
    facts = await pg_memory_store.get_facts("u1")
    assert len(facts) == 1
    assert facts[0]["fact"] == "Old fact B"


@pytest.mark.asyncio
async def test_repeated_auto_saves_do_not_accumulate_but_manual_persists(pg_memory_store):
    await pg_memory_store.add_manual_fact("u1", "Nacio en Orange County", "identity")
    for i in range(5):
        await pg_memory_store.save_facts(
            "u1",
            [
                {"fact": f"auto-turn-{i}-a", "category": "personal"},
                {"fact": f"auto-turn-{i}-b", "category": "personal"},
            ],
        )
    facts = await pg_memory_store.get_facts("u1")
    assert len(facts) == 3
    texts = {f["fact"] for f in facts}
    assert "Nacio en Orange County" in texts
    assert "auto-turn-4-a" in texts
    assert "auto-turn-4-b" in texts
    for i in range(4):
        assert f"auto-turn-{i}-a" not in texts


@pytest.mark.asyncio
async def test_manual_fact_isolation_between_users(pg_memory_store):
    """fi-core 0.25 HARDENED the property this test defends: an empty auto
    snapshot no longer silently proceeds — save_facts([]) raises unless the
    caller passes allow_empty=True, because an extractor returning nothing is
    far more often a failed extraction than a principal with no facts. Prod
    never sends an empty list (persona_gateway/facts.py returns early when
    nothing was added), so the guard firing IS the contract now — and either
    way, nobody's facts move."""
    await pg_memory_store.add_manual_fact("u1", "u1 private detail", "personal")
    await pg_memory_store.add_manual_fact("u2", "u2 private detail", "personal")
    assert len(await pg_memory_store.get_facts("u1")) == 1
    assert len(await pg_memory_store.get_facts("u2")) == 1
    with pytest.raises(ValueError, match="allow_empty"):
        await pg_memory_store.save_facts("u1", [])
    assert any(f["fact"] == "u1 private detail" for f in await pg_memory_store.get_facts("u1"))
    assert any(f["fact"] == "u2 private detail" for f in await pg_memory_store.get_facts("u2"))


# --- fi-core migration (2026-05-22): agent tier + inline-embedding search ---
# The contract above (manual preserved, auto replaced, isolation) now runs
# through `fi_core.memory.PgMemoryStore`. These add the two paths the
# migration newly delegates: the `[REMEMBER:]` agent tier and the inline
# semantic search that replaced the standalone `fact_embeddings` join.


@pytest.mark.asyncio
async def test_add_remember_fact_inserts_with_agent_source(pg_memory_store):
    row_id = await pg_memory_store.add_remember_fact("u1", "Larisa es la terapeuta de Alex", "personal")
    assert row_id > 0
    facts = await pg_memory_store.get_facts("u1")
    assert any(f["fact"] == "Larisa es la terapeuta de Alex" for f in facts)


@pytest.mark.asyncio
async def test_save_facts_preserves_agent_rows(pg_memory_store):
    """`[REMEMBER:]` (source='agent') facts survive auto re-extraction — the
    resistance case for the agent tier, mirroring the manual guarantee.

    Without the source-scoped DELETE, an agent-marked fact would die on the
    next auto extraction (the exact regression the source column prevents)."""
    await pg_memory_store.add_remember_fact("u1", "Recuerda este detalle clave", "personal")
    await pg_memory_store.save_facts("u1", [{"fact": "auto fact nueva", "category": "general"}])
    texts = {f["fact"] for f in await pg_memory_store.get_facts("u1")}
    assert "Recuerda este detalle clave" in texts, "agent fact must survive an auto save"
    assert "auto fact nueva" in texts


@pytest.mark.asyncio
async def test_get_facts_for_injection_keeps_curated_over_recent_auto(pg_memory_store):
    """The 'Other People' block must surface a person's CURATED facts even when
    buried under a burst of recent auto-extractions.

    The 2026-06-03 regression: `get_facts()[:N]` (pure recency) let a flood of
    recent auto facts (Alex's pet-sitting mishap) push her load-bearing curated
    facts (trainer-cert plan, family origin) out of the prompt. `get_facts_for_injection`
    always includes curated facts + only the freshest N auto.
    """
    await pg_memory_store.add_manual_fact("u1", "Plans a trainer certification", "plans")
    await pg_memory_store.add_manual_fact("u1", "Family is from Tantoyuca, Veracruz", "identity")
    # Flood with 15 newer auto facts — under pure recency these would evict the curated ones.
    await pg_memory_store.save_facts("u1", [{"fact": f"auto recent {i}", "category": "personal"} for i in range(15)])

    inj = await pg_memory_store.get_facts_for_injection("u1", auto_limit=5)
    texts = {f["fact"] for f in inj}
    # Both curated facts survive despite 15 newer auto facts.
    assert "Plans a trainer certification" in texts
    assert "Family is from Tantoyuca, Veracruz" in texts
    # Only the freshest 5 auto facts are included, not all 15.
    assert len([t for t in texts if t.startswith("auto recent")]) == 5


@pytest.mark.asyncio
async def test_get_facts_for_injection_empty_user(pg_memory_store):
    """RESISTANCE: a user with no facts yields an empty list, not an error."""
    assert await pg_memory_store.get_facts_for_injection("nobody") == []


@pytest.mark.asyncio
async def test_search_facts_semantic_ranks_relevant_first(pg_memory_store):
    """Inline-embedding cosine search surfaces the relevant fact first.

    Exercises the full migrated path: save_facts embeds each fact inline via
    MiniLM, semantic_search embeds the query and orders by `embedding <=> $1`
    on the inline column (no `fact_embeddings` join anymore)."""
    await pg_memory_store.save_facts(
        "u1",
        [
            {"fact": "Vive en la Ciudad de México", "category": "location"},
            {"fact": "Le encanta programar en Python", "category": "interests"},
            {"fact": "Tiene un gato llamado Mango", "category": "personal"},
        ],
    )
    results = await pg_memory_store.search_facts_semantic("u1", "¿en qué ciudad vive?", limit=3)
    assert results, "semantic search should return ranked facts"
    assert results[0]["fact"] == "Vive en la Ciudad de México"
    # Legacy dict shape preserved for the ~30 consumers.
    assert set(results[0].keys()) == {"id", "fact", "category", "updated_at"}
