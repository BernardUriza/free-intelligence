"""``PgVectorChunkStore`` — the protocol surface of the pgvector store.

See the package docstring (``fi_core.stores.pgvector``) for use-case
guidance and schema convention; DDL lives in ``schema``, row mapping in
``rows``, connection bootstrap in ``fi_core.stores._pg`` and chunk-id
derivation in ``fi_core.stores._common``.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Sequence
from typing import Any

try:
    import asyncpg
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
    DocumentUpsert,
    RetrievedChunk,
    SyncResult,
)
from fi_core.stores._common import chunk_id_from, now
from fi_core.stores._pg import (
    create_vector_pool,
    ensure_vector_extension,
    init_vector_connection,
)
from fi_core.stores.pgvector.rows import row_to_document_record
from fi_core.stores.pgvector.schema import schema_statements

# Default table prefix. Consumers can override at construction so multiple
# stores can coexist in one database without colliding.
_DEFAULT_PREFIX = "fi_core"


class PgVectorChunkStore:
    """Postgres + pgvector-backed ``DocumentChunkStore`` implementation.

    Persists documents + chunks + embeddings into two relational tables
    keyed by ``(namespace, document_id)`` and ``(namespace, chunk_id)``
    respectively. Cosine similarity queries hit a pgvector IVFFlat index
    on the chunks table, or scan it exactly with ``ann_index=False``.

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
        ann_index: bool = True,
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
        self.ann_index = ann_index
        self._docs_table = f"{table_prefix}_documents"
        self._chunks_table = f"{table_prefix}_chunks"
        self._schema_ready = False

    # ------------------------------------------------------------------
    # Pool / lifecycle
    # ------------------------------------------------------------------

    async def _get_pool(self) -> "asyncpg.Pool":
        """Return the connection pool, lazily building from DSN if needed.

        The pgvector codec is registered per-connection via the shared
        ``fi_core.stores._pg`` bootstrap so ``vector(N)`` columns
        round-trip as ``list[float]`` without explicit casts.
        Registration is best-effort — if the extension isn't installed
        yet, the codec is skipped and ``init_schema()`` will install it
        so subsequent connections get the codec.
        """
        if self._pool is not None:
            return self._pool
        assert self._dsn is not None
        pool = await create_vector_pool(self._dsn, min_size=1, max_size=4)
        self._pool = pool
        return pool

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

        The ``vector`` extension is installed BEFORE the pool is built
        (``fi_core.stores._pg.ensure_vector_extension``) so the pool's
        per-connection codec registration sees the type — otherwise
        asyncpg's codec lookup races against a not-yet-created type and
        fails with ``unknown type: public.vector``.
        """
        if self._pool is None and self._dsn is not None:
            await ensure_vector_extension(self._dsn)
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # If the pool was supplied externally OR built before extension
            # creation, this is the safety net.
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await init_vector_connection(conn)
            async with conn.transaction():
                for statement in schema_statements(
                    table_prefix=self.table_prefix,
                    docs_table=self._docs_table,
                    chunks_table=self._chunks_table,
                    embedding_dim=self.embedding_dim,
                    ann_index=self.ann_index,
                ):
                    await conn.execute(statement)
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
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """ChunkStore.query — top-k cosine similarity within ``namespace``.

        Uses pgvector's ``<=>`` cosine distance operator. Returned
        ``similarity`` is ``1 - distance`` so 1.0 means identical, 0.0
        means orthogonal. Zero-norm query vectors return ``[]`` rather
        than NaN — matches the HDF5 sibling's behavior. ``filters`` restricts
        to chunks whose parent document's ``attributes`` contain the given pairs
        (Postgres ``@>`` JSONB containment).
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
            if filters:
                # Join to documents and filter by JSONB containment on attributes.
                rows = await conn.fetch(
                    f"""
                    SELECT c.text, c.source_type, c.source_ref, c.created_at,
                           1 - (c.embedding <=> $1) AS similarity
                    FROM {self._chunks_table} c
                    JOIN {self._docs_table} d
                      ON d.namespace = c.namespace AND d.document_id = c.document_id
                    WHERE c.namespace = $2 AND d.attributes @> $4::jsonb
                    ORDER BY c.embedding <=> $1
                    LIMIT $3
                    """,
                    query_embedding,
                    namespace,
                    top_k,
                    json.dumps(filters),
                )
            else:
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
        meta = metadata or DocumentMetadata(created_at=now())
        created_at = meta.created_at or now()
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
        return row_to_document_record(row)

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
        return [row_to_document_record(r) for r in rows]

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

    async def sync_documents(
        self,
        *,
        namespace: str,
        upserts: Sequence[DocumentUpsert],
        deletes: Collection[str] = (),
        expected_ids: Collection[str] | None = None,
    ) -> SyncResult:
        """Reconcile a namespace in ONE transaction: every document replaced and deleted, or none.

        Each upsert's chunks become the document's only chunks. ``expected_ids``
        is the set of document ids the plan was computed from; if the namespace
        holds another set by the time the lock is taken, nothing is written and
        ``RuntimeError`` is raised. An upsert without chunks, a delete of a
        missing document and an id on both lists raise ``ValueError``.
        """
        await self._ensure_schema()
        ids = [u.document_id for u in upserts]
        if len(set(ids)) != len(ids):
            raise ValueError("sync_documents: the same document_id appears twice in upserts")
        if overlap := set(ids) & set(deletes):
            raise ValueError(f"sync_documents: {sorted(overlap)} both upserted and deleted")
        for u in upserts:
            if not u.chunks:
                raise ValueError(f"sync_documents: document {u.document_id!r} has no chunks")
            if any(len(ce.embedding) != self.embedding_dim for ce in u.chunks):
                raise ValueError(f"sync_documents: {u.document_id!r} carries a vector that is not {self.embedding_dim}d")
        pool = await self._get_pool()
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtext($1))", f"{self.table_prefix}\x1f{namespace}"
            )
            rows = await conn.fetch(f"SELECT document_id FROM {self._docs_table} WHERE namespace = $1", namespace)
            present = {r["document_id"] for r in rows}
            if expected_ids is not None and present != set(expected_ids):
                raise RuntimeError(f"sync_documents: namespace {namespace!r} changed since the plan was computed")
            if missing := set(deletes) - present:
                raise ValueError(f"sync_documents: cannot delete missing documents {sorted(missing)}")
            await conn.execute(
                f"DELETE FROM {self._docs_table} WHERE namespace = $1 AND document_id = ANY($2)",
                namespace,
                list(deletes),
            )
            saved = 0
            for u in upserts:
                saved += await self._replace_in_conn(conn, namespace=namespace, upsert=u)
        return SyncResult(upserted=len(upserts), deleted=len(deletes), chunks=saved)

    async def _replace_in_conn(self, conn: asyncpg.Connection, *, namespace: str, upsert: DocumentUpsert) -> int:
        await conn.execute(
            f"""
            INSERT INTO {self._docs_table}
                (document_id, namespace, content, status, created_at, indexed_at, attributes)
            VALUES ($1, $2, $3, 'indexed', NOW(), NOW(), $4::jsonb)
            ON CONFLICT (namespace, document_id) DO UPDATE
                SET content = EXCLUDED.content, status = EXCLUDED.status,
                    indexed_at = EXCLUDED.indexed_at, attributes = EXCLUDED.attributes
            """,
            upsert.document_id,
            namespace,
            upsert.content,
            json.dumps(upsert.attributes),
        )
        await conn.execute(
            f"DELETE FROM {self._chunks_table} WHERE namespace = $1 AND document_id = $2",
            namespace,
            upsert.document_id,
        )
        by_id: dict[str, ChunkWithEmbedding] = {}
        for ce in upsert.chunks:
            chunk_id = chunk_id_from(ce.chunk, document_id=upsert.document_id)
            if by_id.setdefault(chunk_id, ce).chunk.text != ce.chunk.text:
                raise ValueError(f"sync_documents: two chunks of {upsert.document_id!r} share the id {chunk_id!r}")
        await conn.executemany(
            f"""
            INSERT INTO {self._chunks_table}
                (chunk_id, document_id, namespace, text, source_type, source_ref, embedding, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            [
                (
                    chunk_id,
                    upsert.document_id,
                    namespace,
                    ce.chunk.text,
                    ce.chunk.source_type,
                    ce.chunk.source_ref,
                    ce.embedding,
                    ce.chunk.created_at or now(),
                )
                for chunk_id, ce in by_id.items()
            ],
        )
        return len(by_id)

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
            chunk_id = chunk_id_from(ce.chunk, document_id=document_id)
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
                ce.chunk.created_at or now(),
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
