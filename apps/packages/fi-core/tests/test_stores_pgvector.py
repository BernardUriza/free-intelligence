"""Tests for ``fi_core.stores.pgvector.PgVectorChunkStore``.

Real asyncpg + ephemeral Postgres (via ``pytest-postgresql``) — no
mocks. Mirrors the contract pinned by ``tests/test_stores_hdf5.py``;
the backend is what changes, the protocol surface is the same.

Auto-skip behavior:

- If ``asyncpg`` or ``pgvector`` is missing, ``pytest.importorskip``
  short-circuits the whole module.
- If ``pytest-postgresql`` cannot find a usable ``pg_ctl`` /
  ``postgres`` binary, the ephemeral-Postgres fixture raises during
  setup; we catch that and ``pytest.skip`` so the module reports
  ALL-SKIP rather than ALL-ERROR.
- If the host's Postgres binaries lack the ``pgvector`` extension, the
  ``CREATE EXTENSION vector`` call inside ``init_schema()`` raises and
  we skip — same all-skip outcome.

Tests deliberately use small embedding_dim=3 vectors so the geometry of
``query_top_k_correctness`` is auditable by hand.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone

import pytest

# Optional-deps gating — runs before any pytest-postgresql import.
pytest.importorskip("asyncpg")
pytest.importorskip("pgvector")
pytest.importorskip("pytest_postgresql")

import asyncpg  # noqa: E402

from fi_core.rag import (  # noqa: E402
    Chunk,
    ChunkWithEmbedding,
    DocumentMetadata,
)
from fi_core.rag.protocols import DocumentChunkStore  # noqa: E402
from fi_core.stores.pgvector import PgVectorChunkStore  # noqa: E402


# ---------------------------------------------------------------------
# pytest-postgresql configuration.
#
# We try a series of candidate postgres-bin directories to find one that
# both has a working pg_ctl AND has the pgvector extension installed.
# The default PATH on macOS often has libpq's pg_ctl without a matching
# postgres binary, or PG14 without pgvector — both surfaces would
# break tests rather than skip cleanly. We pre-detect the path and feed
# it to the postgresql_proc factory.
# ---------------------------------------------------------------------


def _detect_postgres_executable() -> str | None:
    """Return a pg_ctl path whose tree has pgvector available, or None.

    Tries (in order): Homebrew postgresql@17, postgresql@18, generic
    `pg_ctl` on PATH. The first one whose adjacent ``share/extension/``
    contains ``vector.control`` wins.
    """
    from pathlib import Path

    candidates: list[str] = []
    # Homebrew Apple-Silicon paths first (most likely to have pgvector
    # installed via `brew install pgvector`).
    for prefix in ("postgresql@17", "postgresql@18", "postgresql@16"):
        p = Path(f"/opt/homebrew/opt/{prefix}/bin/pg_ctl")
        if p.exists():
            candidates.append(str(p))
    # Fallback: whatever's on PATH.
    on_path = shutil.which("pg_ctl")
    if on_path:
        candidates.append(on_path)

    # Brew links pgvector's extension files into the global
    # /opt/homebrew/share/postgresql@<N>/extension/ tree, NOT inside the
    # PG keg's own share/. So we check both: the keg's local share and
    # the brew-global one keyed off the major version.
    extension_roots: list[Path] = [
        Path("/opt/homebrew/share"),
        Path("/usr/local/share"),  # Intel-Mac brew layout
    ]

    def _has_pgvector_for(pg_ctl: str) -> bool:
        bin_dir = Path(pg_ctl).resolve().parent
        # Keg-local share check
        for share in (bin_dir.parent / "share",):
            if share.exists() and any(share.rglob("vector.control")):
                return True
        # Brew-global share check
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

    # Session-scoped ephemeral Postgres process. Lives for the duration
    # of the test session; pytest-postgresql tears it down at exit.
    postgresql_proc = factories.postgresql_proc(executable=_PG_CTL)
else:
    # Stub fixture so individual tests can request it and skip rather
    # than collection error on import.
    @pytest.fixture(scope="session")
    def postgresql_proc():
        pytest.skip(
            "No Postgres binary with pgvector extension found on this host "
            "(checked /opt/homebrew/opt/postgresql@{17,18,16} and PATH). "
            "Install with: brew install postgresql@17 pgvector"
        )


# ---------------------------------------------------------------------
# Async glue
# ---------------------------------------------------------------------


@pytest.fixture(scope="session")
async def pg_dsn(postgresql_proc) -> str:
    """Build an asyncpg DSN pointing at the ephemeral Postgres.

    pytest-postgresql's ``postgresql_proc`` only starts the server; the
    advertised ``dbname`` is created lazily by the ``postgresql`` client
    fixture (which we don't use here, since we drive everything via
    asyncpg). We create the database ourselves on first use against the
    admin ``postgres`` DB.

    Per-test isolation is achieved via the unique ``table_prefix`` in
    the ``store`` fixture below — all tests share one DB but never
    touch each other's tables.
    """
    proc = postgresql_proc
    admin_dsn = (
        f"postgresql://{proc.user}@{proc.host}:{proc.port}/postgres"
    )
    target_db = proc.dbname
    # Use a one-shot admin connection to ensure the test DB exists.
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", target_db
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{target_db}"')
    finally:
        await conn.close()
    return f"postgresql://{proc.user}@{proc.host}:{proc.port}/{target_db}"


@pytest.fixture
async def store(pg_dsn) -> PgVectorChunkStore:
    """A fresh PgVectorChunkStore with schema initialized, isolated per test.

    Uses a per-test ``table_prefix`` (derived from a monotonic counter)
    so two tests sharing the same ephemeral postgres don't see each
    other's rows even if they ran sequentially without teardown.
    """
    # Counter scoped to the module — bumped per fixture instantiation.
    global _PREFIX_COUNTER
    _PREFIX_COUNTER += 1
    prefix = f"fi_core_test_{_PREFIX_COUNTER}"
    s = PgVectorChunkStore(dsn=pg_dsn, embedding_dim=3, table_prefix=prefix)
    try:
        await s.init_schema()
    except asyncpg.exceptions.UndefinedFileError:
        # vector extension missing on this server.
        pytest.skip("pgvector extension not available on this server")
    except Exception as e:
        # Any other init failure — likely missing extension privileges.
        if "vector" in str(e).lower() or "extension" in str(e).lower():
            pytest.skip(f"pgvector extension unavailable: {e}")
        raise
    yield s
    # Cleanup: drop tables (chunks first due to FK) so the next prefix
    # in the same session starts clean if pytest reuses the process.
    pool = await s._get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"DROP TABLE IF EXISTS {prefix}_chunks CASCADE")
        await conn.execute(f"DROP TABLE IF EXISTS {prefix}_documents CASCADE")
    await s.close()


_PREFIX_COUNTER = 0


def _chunk(text: str, source_ref: str, source_type: str = "test") -> Chunk:
    return Chunk(
        text=text,
        source_type=source_type,
        source_ref=source_ref,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _ce(text: str, source_ref: str, embedding: list[float]) -> ChunkWithEmbedding:
    return ChunkWithEmbedding(chunk=_chunk(text, source_ref), embedding=embedding)


# =====================================================================
# Required tests per task spec
# =====================================================================


@pytest.mark.asyncio
async def test_pgvector_create_and_get_document(store):
    await store.create_document(
        namespace="ns1",
        document_id="d1",
        content="Hello world.",
        metadata=DocumentMetadata(status="pending", attributes={"clinic_id": "C1"}),
    )
    doc = await store.get_document(namespace="ns1", document_id="d1")
    assert doc is not None
    assert doc.document_id == "d1"
    assert doc.namespace == "ns1"
    assert doc.content == "Hello world."
    assert doc.metadata.status == "pending"
    assert doc.metadata.attributes == {"clinic_id": "C1"}
    assert doc.chunk_count == 0


@pytest.mark.asyncio
async def test_pgvector_namespace_isolation(store):
    """Data in namespace 'A' must not leak into 'B' queries."""
    await store.create_document(namespace="A", document_id="d1", content="A doc")
    await store.save_chunks(
        namespace="A",
        document_id="d1",
        chunks=[_ce("In namespace A", "A#0", [1.0, 0.0, 0.0])],
    )
    await store.create_document(namespace="B", document_id="d1", content="B doc")
    await store.save_chunks(
        namespace="B",
        document_id="d1",
        chunks=[_ce("In namespace B", "B#0", [1.0, 0.0, 0.0])],
    )
    results_a = await store.query(
        namespace="A", query_embedding=[1.0, 0.0, 0.0], top_k=5
    )
    assert len(results_a) == 1
    assert results_a[0].chunk.text == "In namespace A"
    # Documents also isolated
    docs_a = await store.list_documents(namespace="A")
    docs_b = await store.list_documents(namespace="B")
    assert len(docs_a) == 1
    assert len(docs_b) == 1
    assert docs_a[0].content == "A doc"
    assert docs_b[0].content == "B doc"


@pytest.mark.asyncio
async def test_pgvector_idempotent_save_chunks(store):
    """Re-saving the same chunks should add 0 (ON CONFLICT DO NOTHING)."""
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    first = await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("Same chunk", "d1#0", [1.0, 0.0, 0.0])],
    )
    second = await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("Same chunk", "d1#0", [1.0, 0.0, 0.0])],
    )
    assert first == 1
    assert second == 0
    chunks = await store.get_chunks_by_document(namespace="ns1", document_id="d1")
    assert len(chunks) == 1


@pytest.mark.asyncio
async def test_pgvector_cascading_delete(store):
    """delete_document must drop all child chunks atomically (ON DELETE CASCADE)."""
    await store.create_document(namespace="ns1", document_id="d1", content="A")
    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[
            _ce("Chunk A", "d1#0", [1.0, 0.0, 0.0]),
            _ce("Chunk B", "d1#1", [0.0, 1.0, 0.0]),
        ],
    )
    deleted = await store.delete_document(namespace="ns1", document_id="d1")
    assert deleted is True
    # Document gone
    assert await store.get_document(namespace="ns1", document_id="d1") is None
    # Chunks gone (no orphans)
    results = await store.query(
        namespace="ns1", query_embedding=[1.0, 0.0, 0.0], top_k=5
    )
    assert results == []


@pytest.mark.asyncio
async def test_pgvector_query_top_k_correctness(store):
    """Three chunks with known embeddings; query at known angle; verify order."""
    await store.create_document(namespace="ns1", document_id="d1", content="doc")
    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[
            _ce("Exact match", "d1#0", [1.0, 0.0, 0.0]),
            _ce("Orthogonal", "d1#1", [0.0, 1.0, 0.0]),
            _ce("Mid match", "d1#2", [0.7, 0.7, 0.0]),
        ],
    )
    results = await store.query(
        namespace="ns1", query_embedding=[1.0, 0.0, 0.0], top_k=2
    )
    assert len(results) == 2
    # Closest = exact match, similarity ~ 1.0
    assert results[0].chunk.text == "Exact match"
    assert results[0].similarity == pytest.approx(1.0, abs=1e-5)
    # Next = mid-match (cos(45°) ≈ 0.707), NOT orthogonal
    assert results[1].chunk.text == "Mid match"
    assert results[1].similarity > 0.5
    assert results[1].similarity < 1.0


@pytest.mark.asyncio
async def test_pgvector_status_auto_promotion(store):
    """Status 'pending' -> 'indexed' after first non-empty save_chunks."""
    await store.create_document(
        namespace="ns1",
        document_id="d1",
        content="A",
        metadata=DocumentMetadata(status="pending"),
    )
    doc_pre = await store.get_document(namespace="ns1", document_id="d1")
    assert doc_pre.metadata.status == "pending"
    assert doc_pre.metadata.indexed_at is None

    await store.save_chunks(
        namespace="ns1",
        document_id="d1",
        chunks=[_ce("X", "d1#0", [1.0, 0.0, 0.0])],
    )
    doc_post = await store.get_document(namespace="ns1", document_id="d1")
    assert doc_post.metadata.status == "indexed"
    assert doc_post.metadata.indexed_at is not None


@pytest.mark.asyncio
async def test_pgvector_satisfies_documentchunkstore_protocol(store):
    """Runtime structural check: instance satisfies the Protocol."""
    assert isinstance(store, DocumentChunkStore)
