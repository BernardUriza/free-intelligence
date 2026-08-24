"""`save_facts` must not be able to erase a principal's memory by accident.

These need no database ON PURPOSE: the refusal happens before a connection is
acquired, which is the property worth pinning. The pgvector-backed tests that
would cover the rest of the method skip on any host without a matching
Postgres + pgvector pair, so the most destructive path would otherwise be
verified nowhere at all.
"""

import pytest

from fi_core.memory.stores.pgvector_memory import PgMemoryStore
from fi_core.memory.types import Fact, FactSource


class _PoolThatMustNotBeTouched:
    """Acquiring a connection means the guard let the call through."""

    def acquire(self):  # pragma: no cover - reaching it IS the failure
        raise AssertionError("save_facts reached the database on a call it should have refused")


def _store() -> PgMemoryStore:
    s = PgMemoryStore.__new__(PgMemoryStore)
    s._pool = _PoolThatMustNotBeTouched()  # `_p` is a property over this
    s._embedder = None
    return s


@pytest.mark.asyncio
async def test_an_empty_snapshot_is_refused_before_it_deletes_anything():
    """The DELETE used to run first and `if not facts: return` exited the
    transaction normally — which COMMITS. An extractor that refused, returned
    `[]`, or failed to parse erased every auto fact, with no `deleted_at` and no
    retention window, while the module ships all three."""
    with pytest.raises(ValueError, match="allow_empty"):
        await _store().save_facts("u1", [])


@pytest.mark.asyncio
async def test_clearing_is_possible_but_must_be_asked_for():
    """The guard makes the erasure deliberate, not unavailable. Reaching the pool
    is what proves the call was allowed through."""
    with pytest.raises(AssertionError, match="reached the database"):
        await _store().save_facts("u1", [], allow_empty=True)


def test_the_insert_writes_the_facts_own_source_not_a_literal():
    """It hardcoded `'auto'`, so a MANUAL fact was downgraded on the way in and
    the NEXT snapshot's `DELETE ... WHERE source='auto'` hard-deleted it —
    against the invariant `protocols.py` states in writing."""
    import inspect

    body = inspect.getsource(PgMemoryStore.save_facts)
    insert = body[body.index("INSERT INTO principal_facts"):]
    assert "'auto'" not in insert, "the source column must come from the fact, not a literal"
    assert "f.source.value" in body
    assert "f.updated_at or now" in body, "a fact carrying its own timestamp keeps it"


def test_a_manual_fact_survives_the_shape_the_delete_looks_for():
    """The invariant, stated as the values that actually decide it."""
    manual = Fact(fact="allergic to penicillin", principal_id="u1", source=FactSource.MANUAL)
    assert manual.source.value != "auto", "what the snapshot DELETE keys on"


# --- semantic_search must honour the limit its signature promises ------------


@pytest.mark.asyncio
async def test_every_degraded_path_is_capped_at_limit():
    """Unbounded, the fallbacks returned the principal's ENTIRE fact set from a
    method that promises at most `limit` — a context blowup arriving exactly when
    the embedder is down, which is when a caller is least able to see why."""
    store = PgMemoryStore.__new__(PgMemoryStore)
    store._pool = None
    store._embedder = None
    many = [Fact(fact=f"f{i}", principal_id="u1") for i in range(50)]

    async def _all(_ids):
        return many

    store.get_facts_multi = _all
    assert len(await store.semantic_search_multi(["u1"], "q", limit=5)) == 5


@pytest.mark.asyncio
async def test_a_query_that_will_not_embed_is_also_capped():
    class _Broken:
        async def embed(self, _t):
            raise RuntimeError("embedding backend down")

    store = PgMemoryStore.__new__(PgMemoryStore)
    store._pool = None
    store._embedder = _Broken()
    many = [Fact(fact=f"f{i}", principal_id="u1") for i in range(50)]

    async def _all(_ids):
        return many

    store.get_facts_multi = _all
    assert len(await store.semantic_search_multi(["u1"], "q", limit=3)) == 3
