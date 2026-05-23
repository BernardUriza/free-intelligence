"""Postgres + pgvector ``MemoryStore`` — extracted from discord-bot.

This is the production-validated impl from discord-bot's
``insult/core/memory/repositories/facts.py``, generalized to fi-core:

- ``user_id`` → ``principal_id`` (generic tenant key).
- Class name ``FactsRepository`` (Discord-domain) → ``PgMemoryStore``.
- ``BaseRepository`` + external ``ConnectionManager`` pattern (good for
  multi-table facades) collapsed into a single-class self-managing
  pool (matches the ``PgVectorChunkStore`` shape already shipped in
  ``fi_core.stores.pgvector``).
- Vector path: the discord-bot impl imports ``core.vectors.upsert_fact_vectors``
  / ``search_facts_hybrid`` from outside the repository. Here we accept an
  optional ``embedder`` (a ``fi_core.rag.protocols.Embedder``) injected at
  construction; if absent, semantic_search falls back to keyword/ordered
  results just like the source.

Schema (lifted verbatim from discord-bot's
``insult/core/memory/postgres_schema.sql``, with the table name
generalized to ``principal_facts``)::

    CREATE TABLE IF NOT EXISTS principal_facts (
        id            BIGSERIAL PRIMARY KEY,
        principal_id  TEXT NOT NULL,
        fact          TEXT NOT NULL,
        category      TEXT NOT NULL DEFAULT 'general',
        updated_at    DOUBLE PRECISION NOT NULL,
        source        TEXT NOT NULL DEFAULT 'auto',
        deleted_at    DOUBLE PRECISION DEFAULT NULL,
        embedding     vector  -- only populated when an Embedder is wired in
    );

The audit log (``fact_consolidation_log``) is also shipped — Mem0-style
consolidation writes one row per applied op, transactionally with the
fact mutation.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any

try:
    import asyncpg
except ImportError as e:  # pragma: no cover - import-time error path
    raise ImportError(
        "fi_core.memory.stores.pgvector_memory requires asyncpg. Install with: pip install 'fi-core[memory]'"
    ) from e

try:
    import pgvector.asyncpg as _pgvector_asyncpg
    from pgvector import Vector
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "fi_core.memory.stores.pgvector_memory requires pgvector. Install with: pip install 'fi-core[memory]'"
    ) from e

from fi_core.memory.types import ConsolidationOp, Fact, FactSource

if TYPE_CHECKING:
    from fi_core.rag.protocols import Embedder


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_DDL_PRINCIPAL_FACTS = """
CREATE TABLE IF NOT EXISTS principal_facts (
    id            BIGSERIAL PRIMARY KEY,
    principal_id  TEXT NOT NULL,
    fact          TEXT NOT NULL,
    category      TEXT NOT NULL DEFAULT 'general',
    updated_at    DOUBLE PRECISION NOT NULL,
    source        TEXT NOT NULL DEFAULT 'auto',
    deleted_at    DOUBLE PRECISION DEFAULT NULL,
    embedding     vector
);
"""

_DDL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_pf_principal ON principal_facts(principal_id);",
    "CREATE INDEX IF NOT EXISTS idx_pf_deleted_at ON principal_facts(deleted_at) WHERE deleted_at IS NOT NULL;",
]

_DDL_AUDIT = """
CREATE TABLE IF NOT EXISTS fact_consolidation_log (
    id                BIGSERIAL PRIMARY KEY,
    run_ts            DOUBLE PRECISION NOT NULL,
    principal_id      TEXT NOT NULL,
    fact_id_before    BIGINT,
    fact_id_after     BIGINT,
    op                TEXT NOT NULL CHECK(op IN ('ADD','UPDATE','DELETE','NOOP')),
    reason            TEXT,
    fact_text_before  TEXT,
    fact_text_after   TEXT
);
"""

_DDL_AUDIT_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_fcl_run_ts ON fact_consolidation_log(run_ts);",
    "CREATE INDEX IF NOT EXISTS idx_fcl_principal ON fact_consolidation_log(principal_id);",
]


def _row_to_fact(row: asyncpg.Record, principal_id: str | None = None) -> Fact:
    """Translate an asyncpg Record into the public ``Fact`` dataclass."""
    return Fact(
        id=row["id"],
        principal_id=principal_id or row.get("principal_id", ""),
        fact=row["fact"],
        category=row["category"],
        source=FactSource(row["source"]) if "source" in row else FactSource.AUTO,
        updated_at=row["updated_at"],
        deleted_at=row.get("deleted_at"),
    )


# ---------------------------------------------------------------------------
# Hybrid search helpers (Reciprocal Rank Fusion: vector + keyword)
# ---------------------------------------------------------------------------

# RRF constant. 60 is the value from the original Cormack et al. paper and the
# de-facto default in Elastic / OpenSearch / pgvector hybrid recipes — large
# enough that no single ranking dominates, small enough that top ranks still
# matter.
_RRF_K = 60
# Tokens shorter than this are dropped from keyword matching (articles,
# pronouns, "de"/"el"/"is") — they add noise, not signal.
_KW_MIN_TERM_LEN = 3


def _tokenize(text: str) -> list[str]:
    """Lowercased word tokens >= _KW_MIN_TERM_LEN. Language-agnostic: plain
    `\\w+` over the lowercased string, no stemming or stopword list, so it
    works the same for Spanish, English, or a mix (the discord-bot reality)."""
    return [t for t in re.findall(r"\w+", text.lower()) if len(t) >= _KW_MIN_TERM_LEN]


def _keyword_rank(query: str, facts: list[Fact]) -> list[Fact]:
    """Rank ``facts`` by how many distinct query terms appear in each, best
    first; facts with zero hits are dropped.

    Pure-Python on already-fetched rows: no ``tsvector`` column, no GIN index,
    no pg_trgm extension — fi-core stays consumer-agnostic. For the fact
    volumes this store targets (tens-hundreds per principal) the linear scan is
    negligible; a consumer with millions of facts can override with an indexed
    SQL arm later (the public ``semantic_search`` contract is unchanged)."""
    terms = set(_tokenize(query))
    if not terms:
        return []
    scored: list[tuple[int, Fact]] = []
    for f in facts:
        hits = len(terms & set(_tokenize(f.fact)))
        if hits:
            scored.append((hits, f))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in scored]


def _rrf_fuse(rankings: list[list[int]], *, k: int = _RRF_K) -> dict[int, float]:
    """Reciprocal Rank Fusion over several ranked id-lists. Each list
    contributes ``1 / (k + rank)`` per id (rank is 1-based). An id present in
    multiple rankings accumulates — so a fact that's both vector-near AND a
    keyword hit floats to the top, while a strong signal in either arm alone
    still surfaces it. Order-only: needs no comparable score scales across arms
    (the reason RRF beats naive weighted-sum of cosine + ts_rank)."""
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, fid in enumerate(ranking, start=1):
            scores[fid] += 1.0 / (k + rank)
    return scores


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class PgMemoryStore:
    """Production-shape ``MemoryStore`` backed by Postgres + pgvector.

    Lifecycle::

        store = PgMemoryStore(dsn="postgresql://...", embedder=my_embedder)
        await store.init_schema()
        ...
        facts = await store.get_facts("user-42")
        results = await store.semantic_search("user-42", "lives in Madrid")
        await store.close()
    """

    def __init__(
        self,
        *,
        dsn: str,
        embedder: Embedder | None = None,
        pool_min_size: int = 1,
        pool_max_size: int = 10,
    ) -> None:
        self._dsn = dsn
        self._embedder = embedder
        self._pool_min = pool_min_size
        self._pool_max = pool_max_size
        self._pool: asyncpg.Pool | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def init_schema(self) -> None:
        """Create table + indexes idempotently and ensure pgvector codec is
        registered on every connection acquired from the pool.

        Codec registration MUST happen before the pool is built (the
        well-known asyncpg "unknown type: vector" pitfall fixed in
        ``PgVectorChunkStore`` — same fix here): we open a single bare
        connection, ``CREATE EXTENSION IF NOT EXISTS vector``, then
        construct the pool with a per-connection ``init`` hook that
        re-registers the codec.
        """
        # One-shot bare connection to ensure the extension exists.
        bootstrap = await asyncpg.connect(self._dsn)
        try:
            await bootstrap.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        finally:
            await bootstrap.close()

        async def _init_conn(conn: asyncpg.Connection) -> None:
            await _pgvector_asyncpg.register_vector(conn)

        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=self._pool_min,
            max_size=self._pool_max,
            init=_init_conn,
        )

        async with self._pool.acquire() as conn:
            await conn.execute(_DDL_PRINCIPAL_FACTS)
            for stmt in _DDL_INDEXES:
                await conn.execute(stmt)
            await conn.execute(_DDL_AUDIT)
            for stmt in _DDL_AUDIT_INDEXES:
                await conn.execute(stmt)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @property
    def _p(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PgMemoryStore is not connected — call init_schema() first")
        return self._pool

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def get_facts(
        self,
        principal_id: str,
        *,
        include_deleted: bool = False,
    ) -> list[Fact]:
        """All facts for a principal, newest-updated first."""
        if include_deleted:
            sql = (
                "SELECT id, fact, category, updated_at, source, deleted_at "
                "FROM principal_facts WHERE principal_id = $1 "
                "ORDER BY updated_at DESC"
            )
        else:
            sql = (
                "SELECT id, fact, category, updated_at, source, deleted_at "
                "FROM principal_facts WHERE principal_id = $1 AND deleted_at IS NULL "
                "ORDER BY updated_at DESC"
            )
        rows = await self._p.fetch(sql, principal_id)
        return [_row_to_fact(r, principal_id) for r in rows]

    async def save_facts(
        self,
        principal_id: str,
        facts: list[Fact],
    ) -> None:
        """Replace AUTO-source facts with a snapshot. MANUAL + AGENT preserved.

        Transactional. Embeddings, if an ``Embedder`` is wired, are
        computed and persisted alongside the INSERT — failure to embed
        does NOT roll back the SQL: it logs and the row goes in with
        NULL embedding (consistent with discord-bot's failure mode).
        """
        import time

        now = time.time()
        async with self._p.acquire() as conn, conn.transaction():
            await conn.execute(
                "DELETE FROM principal_facts WHERE principal_id = $1 AND source = 'auto'",
                principal_id,
            )
            if not facts:
                return
            for f in facts:
                embedding_vec: Vector | None = None
                if self._embedder is not None:
                    try:
                        vec = await self._embedder.embed(f.fact)
                        embedding_vec = Vector(vec)
                    except Exception:
                        embedding_vec = None
                await conn.execute(
                    "INSERT INTO principal_facts "
                    "(principal_id, fact, category, updated_at, source, embedding) "
                    "VALUES ($1, $2, $3, $4, 'auto', $5)",
                    principal_id,
                    f.fact,
                    f.category,
                    now,
                    embedding_vec,
                )

    async def add_fact(
        self,
        principal_id: str,
        fact: str,
        *,
        category: str = "general",
        source: FactSource | None = None,
    ) -> int:
        """Insert a single fact with the given source label. Returns the new id."""
        import time

        src = (source or FactSource.MANUAL).value
        now = time.time()
        embedding_vec: Vector | None = None
        if self._embedder is not None:
            try:
                vec = await self._embedder.embed(fact)
                embedding_vec = Vector(vec)
            except Exception:
                embedding_vec = None
        row_id = await self._p.fetchval(
            "INSERT INTO principal_facts "
            "(principal_id, fact, category, updated_at, source, embedding) "
            "VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
            principal_id,
            fact,
            category,
            now,
            src,
            embedding_vec,
        )
        return int(row_id or 0)

    # ------------------------------------------------------------------
    # Soft-delete + retention
    # ------------------------------------------------------------------

    async def soft_delete_fact(self, fact_id: int, *, deleted_at: float) -> bool:
        tag = await self._p.execute(
            "UPDATE principal_facts SET deleted_at = $1 WHERE id = $2 AND deleted_at IS NULL",
            deleted_at,
            fact_id,
        )
        # asyncpg returns "UPDATE n" — split last token as int
        try:
            return int(tag.rsplit(" ", 1)[-1]) > 0
        except (ValueError, AttributeError):
            return False

    async def purge_soft_deleted(self, cutoff: float) -> int:
        tag = await self._p.execute(
            "DELETE FROM principal_facts WHERE deleted_at IS NOT NULL AND deleted_at < $1",
            cutoff,
        )
        try:
            return int(tag.rsplit(" ", 1)[-1])
        except (ValueError, AttributeError):
            return 0

    async def count_live(self, principal_id: str) -> int:
        return int(
            await self._p.fetchval(
                "SELECT COUNT(*) FROM principal_facts WHERE principal_id = $1 AND deleted_at IS NULL",
                principal_id,
            )
            or 0
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def semantic_search(
        self,
        principal_id: str,
        query: str,
        *,
        limit: int = 10,
    ) -> list[Fact]:
        """Hybrid Reciprocal-Rank-Fusion search: pgvector cosine + keyword
        term-overlap, fused via RRF.

        Two arms, fused order-only (see ``_rrf_fuse``):

        - **Vector** — cosine (``<=>``) over the ``embedding`` column, top
          ``limit``. Catches paraphrase / semantic matches.
        - **Keyword** — distinct query-term overlap over the principal's live
          facts (``_keyword_rank``). Catches EXACT tokens a vector ranks low
          (proper names, IDs, rare jargon — e.g. "Larisa", where the embedding
          of a chatty question buries the one fact that names her).

        Degrades gracefully:
        - No embedder / query won't embed → ``get_facts`` (unranked).
        - Embedder present but no embedded rows yet → keyword arm still works
          (so search is useful before the embedding backfill completes).
        - No hits in either arm → ``get_facts`` fallback.
        - Keyword arm empty (no term match) → result is the pure vector order.
        """
        if self._embedder is None:
            return await self.get_facts(principal_id)

        try:
            query_vec = await self._embedder.embed(query)
        except Exception:
            return await self.get_facts(principal_id)

        # Vector arm — top `limit` by cosine distance.
        vec_rows = await self._p.fetch(
            "SELECT id, fact, category, updated_at, source, deleted_at "
            "FROM principal_facts "
            "WHERE principal_id = $2 AND deleted_at IS NULL AND embedding IS NOT NULL "
            "ORDER BY embedding <=> $1 "
            "LIMIT $3",
            Vector(query_vec),
            principal_id,
            limit,
        )
        vec_facts = [_row_to_fact(r, principal_id) for r in vec_rows]

        # Keyword arm — over ALL live facts, because a keyword hit is exactly
        # the case the vector top-K MISSES (that's the point of going hybrid).
        live = await self.get_facts(principal_id)
        kw_facts = _keyword_rank(query, live)[:limit]

        if not vec_facts and not kw_facts:
            return await self.get_facts(principal_id)

        id_to_fact: dict[int, Fact] = {f.id: f for f in (*vec_facts, *kw_facts) if f.id is not None}
        fused = _rrf_fuse(
            [
                [f.id for f in vec_facts if f.id is not None],
                [f.id for f in kw_facts if f.id is not None],
            ]
        )
        ordered = sorted(fused, key=lambda fid: fused[fid], reverse=True)[:limit]
        return [id_to_fact[fid] for fid in ordered]

    # ------------------------------------------------------------------
    # Consolidation
    # ------------------------------------------------------------------

    async def apply_consolidation_plan(
        self,
        principal_id: str,
        plan: list[dict[str, Any]],
        *,
        run_ts: float,
    ) -> list[ConsolidationOp]:
        """Apply a Mem0-style plan transactionally. Returns the audit ops.

        Plan op shape (matches what
        ``fi_core.persona.mcp_server.parse_consolidation_result``
        produces)::

            {"op": "NOOP",   "id": int,  "reason": str}
            {"op": "DELETE", "id": int,  "reason": str}
            {"op": "UPDATE", "merge_ids": [int, ...], "new_fact": str,
             "category": str, "reason": str}
        """
        # Snapshot live facts so we can populate fact_text_before in the audit.
        live = await self.get_facts(principal_id)
        by_id: dict[int, Fact] = {f.id: f for f in live if f.id is not None}

        applied: list[ConsolidationOp] = []
        async with self._p.acquire() as conn, conn.transaction():
            for op in plan:
                kind = op["op"]
                reason = (op.get("reason") or "")[:500]

                if kind == "NOOP":
                    fid = op["id"]
                    applied.append(
                        ConsolidationOp(
                            op="NOOP",
                            fact_id_before=fid,
                            fact_id_after=fid,
                            fact_text_before=by_id[fid].fact if fid in by_id else None,
                            fact_text_after=by_id[fid].fact if fid in by_id else None,
                            reason=reason,
                            run_ts=run_ts,
                        )
                    )
                    continue

                if kind == "DELETE":
                    fid = op["id"]
                    await conn.execute(
                        "UPDATE principal_facts SET deleted_at = $1 WHERE id = $2",
                        run_ts,
                        fid,
                    )
                    applied.append(
                        ConsolidationOp(
                            op="DELETE",
                            fact_id_before=fid,
                            fact_id_after=None,
                            fact_text_before=by_id[fid].fact if fid in by_id else None,
                            fact_text_after=None,
                            reason=reason,
                            run_ts=run_ts,
                        )
                    )
                    continue

                if kind == "UPDATE":
                    merge_ids = op["merge_ids"]
                    new_text = op["new_fact"]
                    category = op.get("category", "general")

                    # Compute embedding for the merged text if we can.
                    embedding_vec: Vector | None = None
                    if self._embedder is not None:
                        try:
                            vec = await self._embedder.embed(new_text)
                            embedding_vec = Vector(vec)
                        except Exception:
                            embedding_vec = None

                    for fid in merge_ids:
                        await conn.execute(
                            "UPDATE principal_facts SET deleted_at = $1 WHERE id = $2",
                            run_ts,
                            fid,
                        )
                    new_id_raw = await conn.fetchval(
                        "INSERT INTO principal_facts "
                        "(principal_id, fact, category, updated_at, source, embedding) "
                        "VALUES ($1, $2, $3, $4, 'auto', $5) RETURNING id",
                        principal_id,
                        new_text,
                        category,
                        run_ts,
                        embedding_vec,
                    )
                    new_id = int(new_id_raw or 0)
                    for fid in merge_ids:
                        applied.append(
                            ConsolidationOp(
                                op="UPDATE",
                                fact_id_before=fid,
                                fact_id_after=new_id,
                                fact_text_before=by_id[fid].fact if fid in by_id else None,
                                fact_text_after=new_text,
                                reason=reason,
                                run_ts=run_ts,
                            )
                        )

            # Audit log rows — one per applied op. Same transaction so the
            # log and the facts can never disagree.
            for o in applied:
                await conn.execute(
                    "INSERT INTO fact_consolidation_log "
                    "(run_ts, principal_id, fact_id_before, fact_id_after, op, "
                    "reason, fact_text_before, fact_text_after) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                    run_ts,
                    principal_id,
                    o.fact_id_before,
                    o.fact_id_after,
                    o.op,
                    o.reason,
                    o.fact_text_before,
                    o.fact_text_after,
                )

        return applied
