"""Tests for ``fi_core.memory.stores.pgvector_memory.PgMemoryStore``.

Real asyncpg + ephemeral Postgres (via ``pytest-postgresql``) — no
mocks. Mirrors the fixture pattern in ``test_stores_pgvector.py``;
the only difference is the store under test.

Auto-skip behavior matches the chunk store tests:

- Missing optional deps → ``pytest.importorskip``.
- No Postgres binary with pgvector → fixture skip.
- pgvector extension absent in the keg → ``init_schema`` skips.
"""

from __future__ import annotations

import shutil
from typing import ClassVar

import pytest

# Optional-deps gating — runs before any pytest-postgresql import.
pytest.importorskip("asyncpg")
pytest.importorskip("pgvector")
pytest.importorskip("pytest_postgresql")

import asyncpg

from fi_core.memory import Fact, FactSource, MemoryStore
from fi_core.memory.stores.pgvector_memory import PgMemoryStore

# ---------------------------------------------------------------------
# pytest-postgresql configuration (mirrors test_stores_pgvector.py)
# ---------------------------------------------------------------------


def _detect_postgres_executable() -> str | None:
    from pathlib import Path

    candidates: list[str] = []
    for prefix in ("postgresql@17", "postgresql@18", "postgresql@16"):
        p = Path(f"/opt/homebrew/opt/{prefix}/bin/pg_ctl")
        if p.exists():
            candidates.append(str(p))
    on_path = shutil.which("pg_ctl")
    if on_path:
        candidates.append(on_path)

    extension_roots: list[Path] = [
        Path("/opt/homebrew/share"),
        Path("/usr/local/share"),
    ]

    def _has_pgvector_for(pg_ctl: str) -> bool:
        bin_dir = Path(pg_ctl).resolve().parent
        for share in (bin_dir.parent / "share",):
            if share.exists() and any(share.rglob("vector.control")):
                return True
        for root in extension_roots:
            if not root.exists():
                continue
            if any(root.rglob("vector.control")):
                return True
        return False

    for pg_ctl in candidates:
        if _has_pgvector_for(pg_ctl):
            return pg_ctl
    return None


_PG_CTL = _detect_postgres_executable()


if _PG_CTL is not None:
    from pytest_postgresql import factories

    memory_postgresql_proc = factories.postgresql_proc(executable=_PG_CTL, port=None)
else:

    @pytest.fixture(scope="session")
    def memory_postgresql_proc():
        pytest.skip(
            "No Postgres binary with pgvector extension found on this host "
            "(checked /opt/homebrew/opt/postgresql@{17,18,16} and PATH). "
            "Install with: brew install postgresql@17 pgvector"
        )


# ---------------------------------------------------------------------
# Async glue
# ---------------------------------------------------------------------


@pytest.fixture(scope="session")
async def memory_pg_dsn(memory_postgresql_proc) -> str:
    proc = memory_postgresql_proc
    admin_dsn = f"postgresql://{proc.user}@{proc.host}:{proc.port}/postgres"
    target_db = proc.dbname
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", target_db)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{target_db}"')
    finally:
        await conn.close()
    return f"postgresql://{proc.user}@{proc.host}:{proc.port}/{target_db}"


@pytest.fixture
async def store(memory_pg_dsn):
    """A fresh PgMemoryStore with schema initialized.

    Each test gets a clean slate via TRUNCATE on the two managed tables.
    Yields the store and tears down the pool at the end.
    """
    s = PgMemoryStore(dsn=memory_pg_dsn)
    try:
        await s.init_schema()
    except asyncpg.UndefinedFileError:
        pytest.skip("pgvector extension not available in this Postgres install")
    # Clean tables before each test (init_schema is idempotent).
    pool = s._p
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE principal_facts RESTART IDENTITY")
        await conn.execute("TRUNCATE fact_consolidation_log RESTART IDENTITY")
    yield s
    await s.close()


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


class TestProtocolSatisfaction:
    async def test_pg_memory_store_satisfies_protocol(self, store):
        assert isinstance(store, MemoryStore)


class TestCRUD:
    async def test_get_facts_empty_namespace(self, store):
        result = await store.get_facts("u1")
        assert result == []

    async def test_add_fact_returns_id_and_persists(self, store):
        fid = await store.add_fact("u1", "lives in Madrid")
        assert fid > 0
        facts = await store.get_facts("u1")
        assert len(facts) == 1
        assert facts[0].fact == "lives in Madrid"
        assert facts[0].source == FactSource.MANUAL  # default for add_fact
        assert facts[0].id == fid

    async def test_add_fact_with_agent_source(self, store):
        await store.add_fact("u1", "remembers Bernard's birthday", source=FactSource.AGENT)
        facts = await store.get_facts("u1")
        assert facts[0].source == FactSource.AGENT

    async def test_save_facts_replaces_auto_only(self, store):
        # Seed with one manual + one auto
        await store.add_fact("u1", "manual fact", source=FactSource.MANUAL)
        await store.save_facts(
            "u1",
            [
                Fact(fact="auto fact 1", principal_id="u1", source=FactSource.AUTO),
                Fact(fact="auto fact 2", principal_id="u1", source=FactSource.AUTO),
            ],
        )
        assert (await store.count_live("u1")) == 3

        # Re-save_facts: auto rows should be wiped, manual preserved
        await store.save_facts(
            "u1",
            [Fact(fact="new auto", principal_id="u1", source=FactSource.AUTO)],
        )
        facts = await store.get_facts("u1")
        assert len(facts) == 2
        texts = {f.fact for f in facts}
        assert "manual fact" in texts  # preserved
        assert "new auto" in texts  # newly inserted
        assert "auto fact 1" not in texts  # wiped


class TestSoftDeleteAndPurge:
    async def test_soft_delete_excludes_from_get_facts(self, store):
        fid = await store.add_fact("u1", "fact to delete")
        await store.soft_delete_fact(fid, deleted_at=1000.0)
        live = await store.get_facts("u1")
        assert live == []
        with_deleted = await store.get_facts("u1", include_deleted=True)
        assert len(with_deleted) == 1
        assert with_deleted[0].deleted_at == 1000.0

    async def test_soft_delete_unknown_id_returns_false(self, store):
        result = await store.soft_delete_fact(99999, deleted_at=1000.0)
        assert result is False

    async def test_count_live_excludes_soft_deleted(self, store):
        fid1 = await store.add_fact("u1", "live")
        fid2 = await store.add_fact("u1", "to delete")
        await store.soft_delete_fact(fid2, deleted_at=1000.0)
        assert (await store.count_live("u1")) == 1
        _ = fid1

    async def test_purge_soft_deleted_removes_past_cutoff(self, store):
        fid_old = await store.add_fact("u1", "old delete")
        fid_recent = await store.add_fact("u1", "recent delete")
        await store.soft_delete_fact(fid_old, deleted_at=100.0)
        await store.soft_delete_fact(fid_recent, deleted_at=900.0)

        removed = await store.purge_soft_deleted(cutoff=500.0)
        assert removed == 1

        all_with_deleted = await store.get_facts("u1", include_deleted=True)
        # Only the recent one survives
        assert len(all_with_deleted) == 1
        assert all_with_deleted[0].id == fid_recent


class TestConsolidationApply:
    async def test_noop_plan_preserves_facts(self, store):
        fid1 = await store.add_fact("u1", "a")
        fid2 = await store.add_fact("u1", "b")
        plan = [
            {"op": "NOOP", "id": fid1, "reason": ""},
            {"op": "NOOP", "id": fid2, "reason": ""},
        ]
        ops = await store.apply_consolidation_plan("u1", plan, run_ts=1000.0)
        assert len(ops) == 2
        assert all(o.op == "NOOP" for o in ops)
        assert await store.count_live("u1") == 2

    async def test_delete_plan_soft_deletes(self, store):
        fid = await store.add_fact("u1", "to be deleted")
        plan = [{"op": "DELETE", "id": fid, "reason": "obsolete"}]
        ops = await store.apply_consolidation_plan("u1", plan, run_ts=1000.0)
        assert len(ops) == 1
        assert ops[0].op == "DELETE"
        assert ops[0].fact_id_after is None
        assert await store.count_live("u1") == 0

    async def test_update_plan_merges_ids_into_new_row(self, store):
        ids = [
            await store.add_fact("u1", "fragment 1"),
            await store.add_fact("u1", "fragment 2"),
        ]
        plan = [
            {
                "op": "UPDATE",
                "merge_ids": ids,
                "new_fact": "merged fragment",
                "category": "general",
                "reason": "redundant",
            }
        ]
        ops = await store.apply_consolidation_plan("u1", plan, run_ts=1000.0)
        # 1 UPDATE op per merged id
        assert len(ops) == 2
        new_ids = {o.fact_id_after for o in ops}
        assert len(new_ids) == 1  # all merged into same new id
        # 1 live (the merged) + 2 soft-deleted
        assert await store.count_live("u1") == 1

    async def test_audit_log_written_in_same_tx(self, store):
        fid = await store.add_fact("u1", "x")
        plan = [{"op": "NOOP", "id": fid}]
        await store.apply_consolidation_plan("u1", plan, run_ts=1000.0)
        # Audit row should exist
        pool = store._p
        count = await pool.fetchval(
            "SELECT COUNT(*) FROM fact_consolidation_log WHERE principal_id = $1",
            "u1",
        )
        assert count == 1


class TestSemanticSearchWithoutEmbedder:
    async def test_falls_back_to_get_facts_when_no_embedder(self, store):
        await store.add_fact("u1", "a")
        await store.add_fact("u1", "b")
        results = await store.semantic_search("u1", "anything")
        assert len(results) == 2


class _FakeEmbedder:
    """Deterministic 2-D embedder for hybrid tests — maps known texts to chosen
    vectors so we control exactly which facts are vector-near vs vector-far.
    Everything unknown lands orthogonal to the [1,0] query axis."""

    _MAP: ClassVar[dict[str, list[float]]] = {
        # facts
        "el clima de hoy hace calor": [0.99, 0.14],  # vector-NEAR [1,0], no keyword
        "le gusta el cafe de especialidad": [0.95, 0.31],  # vector-near-ish, no keyword
        "su contacto es larisa la terapeuta": [0.0, 1.0],  # vector-FAR, has "larisa"
        # queries
        "larisa": [1.0, 0.0],
        "dame algo random sin coincidencias": [1.0, 0.0],
    }

    async def embed(self, text: str) -> list[float]:
        return self._MAP.get(text, [0.0, 1.0])


@pytest.fixture
async def hybrid_store(memory_pg_dsn):
    """Like ``store`` but with an Embedder wired, so semantic_search runs the
    full RRF hybrid path instead of the no-embedder fallback."""
    s = PgMemoryStore(dsn=memory_pg_dsn, embedder=_FakeEmbedder())
    try:
        await s.init_schema()
    except asyncpg.UndefinedFileError:
        pytest.skip("pgvector extension not available in this Postgres install")
    async with s._p.acquire() as conn:
        await conn.execute("TRUNCATE principal_facts RESTART IDENTITY")
        await conn.execute("TRUNCATE fact_consolidation_log RESTART IDENTITY")
    yield s
    await s.close()


class TestSemanticSearchHybrid:
    _FACTS: ClassVar[list[str]] = [
        "el clima de hoy hace calor",
        "le gusta el cafe de especialidad",
        "su contacto es larisa la terapeuta",
    ]

    async def _seed(self, store):
        for text in self._FACTS:
            await store.add_fact("u1", text)

    async def test_keyword_match_outranks_vector_closest(self, hybrid_store):
        """Positive: 'larisa' embeds NEAR the chatty facts and FAR from the one
        fact that names her — pure vector would bury it. RRF's keyword arm lifts
        the exact-token match to the top. This is the 'Larisa' miss, fixed."""
        await self._seed(hybrid_store)
        results = await hybrid_store.semantic_search("u1", "larisa", limit=3)
        assert results, "hybrid search must return ranked facts"
        assert results[0].fact == "su contacto es larisa la terapeuta"

    async def test_no_keyword_overlap_falls_back_to_vector_order(self, hybrid_store):
        """Resistance: a query with NO term overlap → keyword arm is empty →
        result is the pure vector order (the vector-closest fact first), NOT a
        random keyword injection."""
        await self._seed(hybrid_store)
        results = await hybrid_store.semantic_search("u1", "dame algo random sin coincidencias", limit=3)
        assert results
        assert results[0].fact == "el clima de hoy hace calor"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
