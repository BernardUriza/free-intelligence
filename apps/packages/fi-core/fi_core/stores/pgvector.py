"""Postgres + pgvector-backed implementation of ``DocumentChunkStore``.

Reference implementation of the storage protocol defined in
``fi_core.rag.protocols.DocumentChunkStore``, backed by PostgreSQL with
the ``pgvector`` extension. Designed for multi-tenant chat substrates
and similar workloads where relational filters (namespace, status,
attribute) combine with vector similarity at query time.

Use case vs the HDF5 sibling:

- **Concurrent writers**: Postgres handles them natively; the HDF5 store
  is single-writer per file. Pick this implementation when you have
  multiple processes ingesting into the same logical store.
- **Transactional consistency**: ``save_chunks`` runs in one
  transaction; cascading delete rolls back atomically on failure.
- **Operational cost**: heavier than HDF5 — needs a Postgres server,
  the ``vector`` extension installed (Azure Flexible Server enables it
  via ``azure.extensions=VECTOR``; self-hosted needs the ``pgvector``
  package + ``CREATE EXTENSION vector``), and a connection pool.

Schema convention (per task spec): two tables, prefix-parameterized so
multiple stores can coexist in one database without colliding.

  - ``{prefix}_documents`` (document_id PK, namespace, content,
    status, created_at, indexed_at, attributes jsonb)
  - ``{prefix}_chunks`` (chunk_id PK, document_id FK, namespace, text,
    source_type, source_ref, embedding vector(N), created_at)

N (the embedding dimension) is parameterized at construction time and
locked at schema-init. Cosine similarity uses pgvector's ``<=>``
operator (smaller-is-closer); the returned ``similarity`` is
``1 - distance`` so the value is in [0, 1] across stores.

Index choice: IVFFlat with ``vector_cosine_ops`` and ``lists=100`` —
matches what the discord-bot deep-memory schema uses and is the
standard pgvector starting point for tables under ~1M rows. For larger
catalogs migrate to HNSW (``CREATE INDEX ... USING hnsw``) which is
more memory-hungry but offers better recall at scale.

Optional dependency: ``asyncpg`` + ``pgvector``. Install via
``pip install 'fi-core[stores-pgvector]'``.
"""

from __future__ import annotations

import json
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any

try:
    import asyncpg
    from pgvector.asyncpg import register_vector
except ImportError as e:
    raise ImportError(
        "fi_core.stores.pgvector requires asyncpg and pgvector. "
        "Install via: pip install 'fi-core[stores-pgvector]'"
    ) from e

from fi_core.rag.types import (
    Chunk,
    ChunkWithEmbedding,
    DocumentMetadata,
    DocumentRecord,
    RetrievedChunk,
)


# Default table prefix. Consumers can override at construction so multiple
# stores can coexist in one database without colliding.
_DEFAULT_PREFIX = "fi_core"

# pgvector cosine index. lists=100 is the standard starting point for tables
# under ~1M rows; consumers crossing that threshold should rebuild as HNSW.
_IVFFLAT_LISTS = 100


class PgVectorChunkStore:
    """Postgres + pgvector-backed ``DocumentChunkStore`` implementation.

    Persists documents + chunks + embeddings into two relational tables
    keyed by ``(namespace, document_id)`` and ``(namespace, chunk_id)``
    respectively. Cosine similarity queries hit a pgvector IVFFlat index
    on the chunks table.

    Construction takes either a DSN (string) or a pre-built
    ``asyncpg.Pool``. Passing a pool is preferred in long-running
    services so multiple stores share connections.

    Schema is NOT created on construction — call ``init_schema()``
    explicitly (or set ``ensure_schema=True`` on first call) so consumers
    keep DDL out of import-time side effects. Idempotent: re-running
    ``init_schema()`` against an initialized database is a no-op.

    Concurrency: safe for concurrent writers (transactional). The
    ``save_chunks`` path uses a single transaction so partial batches do
    not corrupt the index on failure.
    """

    def __init__(
        self,
        *,
        dsn: str | None = None,
        pool: "asyncpg.Pool | None" = None,
        embedding_dim: int,
        table_prefix: str = _DEFAULT_PREFIX,
    ) -> None:
        if (dsn is None) == (pool is None):
            raise ValueError(
                "PgVectorChunkStore requires exactly one of `dsn` or `pool`, not both/neither."
            )
        if embedding_dim <= 0:
            raise ValueError(f"embedding_dim must be positive, got {embedding_dim!r}")
        # Light validation — pg identifiers can't be too creative. The prefix
        # is interpolated directly into SQL (not a bind param), so we restrict
        # it to a conservative character set up-front.
        if not table_prefix or not all(
            c.isalnum() or c == "_" for c in table_prefix
        ):
            raise ValueError(
                f"table_prefix must be alphanumeric/underscore, got {table_prefix!r}"
            )
        self._dsn = dsn
        self._external_pool = pool
        self._pool: asyncpg.Pool | None = pool
        self.embedding_dim = embedding_dim
        self.table_prefix = table_prefix
        self._docs_table = f"{table_prefix}_documents"
        self._chunks_table = f"{table_prefix}_chunks"
        self._schema_ready = False

    # ------------------------------------------------------------------
    # Pool / lifecycle
    # ------------------------------------------------------------------

    async def _get_pool(self) -> "asyncpg.Pool":
        """Return the connection pool, lazily building from DSN if needed.

        The pgvector codec is registered per-connection via asyncpg's
        ``init=`` callback so ``vector(N)`` columns round-trip as
        ``list[float]`` without explicit casts. Registration is
        best-effort — if the extension isn't installed yet, the codec
        is skipped and ``init_schema()`` will install it + recreate the
        pool so subsequent connections get the codec.
        """
        if self._pool is not None:
            return self._pool
        assert self._dsn is not None
        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=1,
            max_size=4,
            init=self._init_connection,
        )
        return self._pool

    @staticmethod
    async def _init_connection(conn: "asyncpg.Connection") -> None:
        """asyncpg pool init callback: register the pgvector codec.

        Tolerant of the case where the extension isn't installed yet
        — in that branch the codec is skipped silently and the caller
        is expected to call ``init_schema()`` to install + reopen.
        """
        try:
            await register_vector(conn)
        except Exception:
            # Extension not present yet; init_schema() will rebuild.
            pass

    async def close(self) -> None:
        """Close the pool if this instance built it.

        If the pool was supplied externally by the caller, leave it
        alone — the caller owns its lifecycle.
        """
        if self._pool is not None and self._external_pool is None:
            await self._pool.close()
            self._pool = None

    async def init_schema(self) -> None:
        """Create the documents + chunks tables + indexes if missing.

        Idempotent (``CREATE TABLE IF NOT EXISTS`` + ``CREATE INDEX IF
        NOT EXISTS``). Also enables the ``vector`` extension — requires
        the connecting role to have ``CREATE`` privilege on the
        database, or the extension to be pre-installed by a superuser
        (typical in managed Postgres products).

        The ``vector`` extension is installed via a one-shot bare
        connection BEFORE the pool is built, so the pool's per-
        connection ``init=`` codec registration sees the type.
        Otherwise asyncpg's codec lookup races against a not-yet-
        created type and fails with ``unknown type: public.vector``.
        """
        if self._pool is None and self._dsn is not None:
            # One-shot bare connection to install the extension first.
            bare = await asyncpg.connect(self._dsn)
            try:
                await bare.execute("CREATE EXTENSION IF NOT EXISTS vector")
            finally:
                await bare.close()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # If the pool was supplied externally OR built before extension
            # creation, this is the safety net.
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            try:
                await register_vector(conn)
            except Exception:
                pass
            async with conn.transaction():
                await conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._docs_table} (
                        document_id     TEXT NOT NULL,
                        namespace       TEXT NOT NULL,
                        content         TEXT NOT NULL,
                        status          TEXT NOT NULL DEFAULT 'pending',
                        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        indexed_at      TIMESTAMPTZ,
                        attributes      JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        PRIMARY KEY (namespace, document_id)
                    )
                    """
                )
                await conn.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_docs_ns_status
                        ON {self._docs_table} (namespace, status)
                    """
                )
                await conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._chunks_table} (
                        chunk_id        TEXT NOT NULL,
                        document_id     TEXT NOT NULL,
                        namespace       TEXT NOT NULL,
                        text            TEXT NOT NULL,
                        source_type     TEXT NOT NULL,
                        source_ref      TEXT NOT NULL,
                        embedding       vector({self.embedding_dim}) NOT NULL,
                        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (namespace, chunk_id),
                        FOREIGN KEY (namespace, document_id)
                            REFERENCES {self._docs_table} (namespace, document_id)
                            ON DELETE CASCADE
                    )
                    """
                )
                await conn.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_chunks_doc
                        ON {self._chunks_table} (namespace, document_id)
                    """
                )
                # IVFFlat cosine index. lists=100 is the standard starting
                # point for tables under ~1M rows (matches the discord-bot
                # deep-memory convention). Migrate to HNSW above that.
                await conn.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_prefix}_chunks_embedding
                        ON {self._chunks_table}
                        USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = {_IVFFLAT_LISTS})
                    """
                )
        self._schema_ready = True

    async def _ensure_schema(self) -> None:
        if not self._schema_ready:
            await self.init_schema()

    # ------------------------------------------------------------------
    # Protocol: ChunkStore.add / query
    # ------------------------------------------------------------------

    async def add(
        self,
        *,
        namespace: str,
        chunk: Chunk,
        embedding: list[float],
    ) -> None:
        """ChunkStore.add — chunk-only insert.

        For consumers that don't model documents explicitly: synthesizes
        a per-source-ref parent document so the underlying foreign key
        is satisfied. Idempotent on ``(namespace, source_ref)``.
        """
        await self._ensure_schema()
        document_id = f"_auto_{chunk.source_ref}"
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Create-if-missing parent doc.
                await conn.execute(
                    f"""
                    INSERT INTO {self._docs_table}
                        (document_id, namespace, content, status, created_at, attributes)
                    VALUES ($1, $2, $3, 'pending', NOW(), '{{}}'::jsonb)
                    ON CONFLICT (namespace, document_id) DO NOTHING
                    """,
                    document_id,
                    namespace,
                    chunk.text,
                )
                await self._save_chunks_in_conn(
                    conn,
                    namespace=namespace,
                    document_id=document_id,
                    chunks=[ChunkWithEmbedding(chunk=chunk, embedding=embedding)],
                )

    async def query(
        self,
        *,
        namespace: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        """ChunkStore.query — top-k cosine similarity within ``namespace``.

        Uses pgvector's ``<=>`` cosine distance operator. Returned
        ``similarity`` is ``1 - distance`` so 1.0 means identical, 0.0
        means orthogonal. Zero-norm query vectors return ``[]`` rather
        than NaN — matches the HDF5 sibling's behavior.
        """
        await self._ensure_schema()
        if top_k <= 0:
            return []
        if not any(v != 0.0 for v in query_embedding):
            # pgvector returns NaN for cosine distance against a zero vector.
            # Match HDF5 sibling: empty list, not garbage results.
            return []
        if len(query_embedding) != self.embedding_dim:
            raise ValueError(
                f"query_embedding has {len(query_embedding)} dims, store expects {self.embedding_dim}"
            )
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT text, source_type, source_ref, created_at,
                       1 - (embedding <=> $1) AS similarity
                FROM {self._chunks_table}
                WHERE namespace = $2
                ORDER BY embedding <=> $1
                LIMIT $3
                """,
                query_embedding,
                namespace,
                top_k,
            )
        return [
            RetrievedChunk(
                chunk=Chunk(
                    text=r["text"],
                    source_type=r["source_type"],
                    source_ref=r["source_ref"],
                    created_at=r["created_at"],
                ),
                similarity=float(r["similarity"]),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Protocol: DocumentChunkStore (document lifecycle)
    # ------------------------------------------------------------------

    async def create_document(
        self,
        *,
        namespace: str,
        document_id: str,
        content: str,
        metadata: DocumentMetadata | None = None,
    ) -> str:
        await self._ensure_schema()
        meta = metadata or DocumentMetadata(created_at=_now())
        created_at = meta.created_at or _now()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            try:
                await conn.execute(
                    f"""
                    INSERT INTO {self._docs_table}
                        (document_id, namespace, content, status, created_at, indexed_at, attributes)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                    """,
                    document_id,
                    namespace,
                    content,
                    meta.status,
                    created_at,
                    meta.indexed_at,
                    json.dumps(meta.attributes),
                )
            except asyncpg.UniqueViolationError as e:
                raise ValueError(
                    f"Document {document_id!r} already exists in namespace {namespace!r}. "
                    f"Use update_document for upsert semantics."
                ) from e
        return document_id

    async def get_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> DocumentRecord | None:
        await self._ensure_schema()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT d.document_id, d.namespace, d.content, d.status,
                       d.created_at, d.indexed_at, d.attributes,
                       (
                         SELECT COUNT(*) FROM {self._chunks_table} c
                         WHERE c.namespace = d.namespace
                           AND c.document_id = d.document_id
                       ) AS chunk_count
                FROM {self._docs_table} d
                WHERE d.namespace = $1 AND d.document_id = $2
                """,
                namespace,
                document_id,
            )
        if row is None:
            return None
        return _row_to_document_record(row)

    async def list_documents(
        self,
        *,
        namespace: str,
        status: str | None = None,
        limit: int | None = None,
    ) -> list[DocumentRecord]:
        await self._ensure_schema()
        pool = await self._get_pool()
        # Build the query with optional clauses. Use named placeholders to
        # keep the binding consistent regardless of optional filters.
        where_clauses = ["d.namespace = $1"]
        params: list[Any] = [namespace]
        if status is not None:
            where_clauses.append(f"d.status = ${len(params) + 1}")
            params.append(status)
        where = " AND ".join(where_clauses)
        limit_clause = ""
        if limit is not None:
            limit_clause = f" LIMIT ${len(params) + 1}"
            params.append(limit)
        query = f"""
            SELECT d.document_id, d.namespace, d.content, d.status,
                   d.created_at, d.indexed_at, d.attributes,
                   (
                     SELECT COUNT(*) FROM {self._chunks_table} c
                     WHERE c.namespace = d.namespace
                       AND c.document_id = d.document_id
                   ) AS chunk_count
            FROM {self._docs_table} d
            WHERE {where}
            ORDER BY d.created_at DESC{limit_clause}
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [_row_to_document_record(r) for r in rows]

    async def update_document(
        self,
        *,
        namespace: str,
        document_id: str,
        content: str | None = None,
        metadata: DocumentMetadata | None = None,
    ) -> bool:
        await self._ensure_schema()
        if content is None and metadata is None:
            # No-op update — still need to verify existence to honor contract.
            existing = await self.get_document(namespace=namespace, document_id=document_id)
            return existing is not None
        # Build a single UPDATE so the existence check and the write share
        # one round-trip. asyncpg's `execute` returns a status string like
        # "UPDATE 1" / "UPDATE 0"; we use that to detect the "not found" case.
        sets: list[str] = []
        params: list[Any] = []
        if content is not None:
            sets.append(f"content = ${len(params) + 1}")
            params.append(content)
        if metadata is not None:
            sets.append(f"status = ${len(params) + 1}")
            params.append(metadata.status)
            if metadata.created_at is not None:
                sets.append(f"created_at = ${len(params) + 1}")
                params.append(metadata.created_at)
            if metadata.indexed_at is not None:
                sets.append(f"indexed_at = ${len(params) + 1}")
                params.append(metadata.indexed_at)
            sets.append(f"attributes = ${len(params) + 1}::jsonb")
            params.append(json.dumps(metadata.attributes))
        ns_idx = len(params) + 1
        params.append(namespace)
        doc_idx = len(params) + 1
        params.append(document_id)
        set_clause = ", ".join(sets)
        query = (
            f"UPDATE {self._docs_table} SET {set_clause} "
            f"WHERE namespace = ${ns_idx} AND document_id = ${doc_idx}"
        )
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            status = await conn.execute(query, *params)
        # asyncpg returns "UPDATE <n>" for executes against UPDATE statements.
        return status.endswith(" 1") or status.endswith(" 2")  # 2 = safety pad for weird rules

    async def delete_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> bool:
        await self._ensure_schema()
        pool = await self._get_pool()
        # FK has ON DELETE CASCADE, so chunks go with the document atomically.
        async with pool.acquire() as conn:
            status = await conn.execute(
                f"DELETE FROM {self._docs_table} WHERE namespace = $1 AND document_id = $2",
                namespace,
                document_id,
            )
        return status.endswith(" 1")

    async def save_chunks(
        self,
        *,
        namespace: str,
        document_id: str,
        chunks: list[ChunkWithEmbedding],
    ) -> int:
        await self._ensure_schema()
        if not chunks:
            return 0
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                return await self._save_chunks_in_conn(
                    conn,
                    namespace=namespace,
                    document_id=document_id,
                    chunks=chunks,
                )

    async def _save_chunks_in_conn(
        self,
        conn: "asyncpg.Connection",
        *,
        namespace: str,
        document_id: str,
        chunks: list[ChunkWithEmbedding],
    ) -> int:
        """Inner save path — assumes an existing connection + transaction.

        Verifies the parent document exists, inserts chunks idempotently
        (keyed on ``(namespace, chunk_id)`` where chunk_id is derived
        deterministically from source_ref + text hash), and on first
        non-zero save auto-promotes the document status from "pending"
        to "indexed" with ``indexed_at = NOW()``.
        """
        doc_row = await conn.fetchrow(
            f"SELECT status FROM {self._docs_table} WHERE namespace = $1 AND document_id = $2",
            namespace,
            document_id,
        )
        if doc_row is None:
            raise ValueError(
                f"Document {document_id!r} does not exist in namespace "
                f"{namespace!r}. Call create_document first."
            )
        saved = 0
        for ce in chunks:
            if len(ce.embedding) != self.embedding_dim:
                raise ValueError(
                    f"Embedding dim {len(ce.embedding)} != store dim {self.embedding_dim} "
                    f"for chunk (source_ref={ce.chunk.source_ref!r})"
                )
            chunk_id = _chunk_id_from(document_id, ce.chunk)
            result = await conn.execute(
                f"""
                INSERT INTO {self._chunks_table}
                    (chunk_id, document_id, namespace, text,
                     source_type, source_ref, embedding, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (namespace, chunk_id) DO NOTHING
                """,
                chunk_id,
                document_id,
                namespace,
                ce.chunk.text,
                ce.chunk.source_type,
                ce.chunk.source_ref,
                ce.embedding,
                ce.chunk.created_at or _now(),
            )
            if result.endswith(" 1"):
                saved += 1
        if saved > 0:
            # Auto-promote pending → indexed; leave other statuses alone.
            await conn.execute(
                f"""
                UPDATE {self._docs_table}
                SET indexed_at = NOW(),
                    status = CASE WHEN status = 'pending' THEN 'indexed' ELSE status END
                WHERE namespace = $1 AND document_id = $2
                """,
                namespace,
                document_id,
            )
        return saved

    async def get_chunks_by_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> list[Chunk]:
        await self._ensure_schema()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT text, source_type, source_ref, created_at
                FROM {self._chunks_table}
                WHERE namespace = $1 AND document_id = $2
                """,
                namespace,
                document_id,
            )
        return [
            Chunk(
                text=r["text"],
                source_type=r["source_type"],
                source_ref=r["source_ref"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    async def delete_chunks_by_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> int:
        await self._ensure_schema()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            status = await conn.execute(
                f"DELETE FROM {self._chunks_table} WHERE namespace = $1 AND document_id = $2",
                namespace,
                document_id,
            )
        # asyncpg execute returns "DELETE <n>"
        try:
            return int(status.split()[-1])
        except (ValueError, IndexError):
            return 0

    async def reindex_document(
        self,
        *,
        namespace: str,
        document_id: str,
    ) -> bool:
        """Pgvector index is persistent — no in-memory cache to rebuild.

        Returns True if the document exists, False otherwise. Treated
        as a no-op per the Protocol's "implementations that don't
        maintain an in-memory index may treat this as a no-op" clause.
        """
        await self._ensure_schema()
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT 1 FROM {self._docs_table} WHERE namespace = $1 AND document_id = $2",
                namespace,
                document_id,
            )
        return row is not None


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_document_record(row: "asyncpg.Record") -> DocumentRecord:
    """Reconstruct a DocumentRecord from an asyncpg Record row."""
    raw_attrs = row["attributes"]
    if isinstance(raw_attrs, str):
        try:
            attributes = json.loads(raw_attrs)
        except (ValueError, TypeError):
            attributes = {}
    elif isinstance(raw_attrs, dict):
        attributes = raw_attrs
    else:
        attributes = {}
    return DocumentRecord(
        document_id=row["document_id"],
        namespace=row["namespace"],
        content=row["content"],
        metadata=DocumentMetadata(
            status=row["status"],
            created_at=row["created_at"],
            indexed_at=row["indexed_at"],
            attributes=attributes,
        ),
        chunk_count=int(row["chunk_count"] or 0),
    )


def _chunk_id_from(document_id: str, chunk: Chunk) -> str:
    """Deterministic chunk_id from (document_id, source_ref, text-hash-prefix).

    Idempotency contract: re-running an ingest with the same Chunk must
    produce the same chunk_id so the ``ON CONFLICT DO NOTHING`` insert
    short-circuits. Matches the HDF5 sibling's convention.
    """
    text_hash = format(abs(hash(chunk.text)) % (1 << 32), "08x")
    safe_source_ref = chunk.source_ref.replace("/", "_").replace(":", "_")
    # Include document_id prefix so the same chunk text under different
    # documents in the same namespace still gets distinct primary keys.
    safe_doc_id = document_id.replace("/", "_").replace(":", "_")
    return f"{safe_doc_id}__{safe_source_ref}_{text_hash}"


# Unused but kept for forward-compat: callers that want a UUID for a
# brand-new chunk can use this when they're not deriving from a hashable
# source_ref. Not used by the Protocol surface.
def _new_uuid_chunk_id() -> str:  # pragma: no cover - reserved
    return _uuid.uuid4().hex
