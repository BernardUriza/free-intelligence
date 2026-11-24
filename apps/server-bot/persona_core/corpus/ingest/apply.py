"""Embed a plan's documents and write it in one transaction."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fi_core.rag import Chunk, ChunkWithEmbedding, DocumentUpsert, SyncResult
from fi_core.stores.pgvector import PgVectorChunkStore

from persona_core.corpus.ingest.documents import CorpusDocument
from persona_core.corpus.ingest.plan import StoredDocument, SyncPlan
from persona_core.corpus.pg_rag import CORPUS_TABLE_PREFIX, EMBEDDING_DIM

Embed = Callable[[str], Awaitable[list[float]]]


class PlanRefusedError(RuntimeError):
    """The plan has refusals; nothing was written."""


def corpus_store(dsn: str) -> PgVectorChunkStore:
    """The corpus tables, searched exactly."""
    return PgVectorChunkStore(dsn=dsn, embedding_dim=EMBEDDING_DIM, table_prefix=CORPUS_TABLE_PREFIX, ann_index=False)


async def stored_documents(store: PgVectorChunkStore, namespace: str) -> list[StoredDocument]:
    records = await store.list_documents(namespace=namespace)
    return [StoredDocument(r.document_id, r.chunk_count, r.metadata.attributes) for r in records]


async def _upsert(document: CorpusDocument, embed: Embed) -> DocumentUpsert:
    chunks = [
        ChunkWithEmbedding(Chunk(text=t, source_type="manual", source_ref=document.document_id), await embed(t))
        for t in document.chunks
    ]
    return DocumentUpsert(document.document_id, document.content, chunks, document.attributes)


async def apply_plan(
    store: PgVectorChunkStore,
    namespace: str,
    plan: SyncPlan,
    *,
    embed: Embed,
    progress: Callable[[int, int], None] = lambda done, total: None,
) -> SyncResult:
    """Every vector is computed before the transaction opens, so a failed embed writes nothing."""
    if plan.refusals:
        raise PlanRefusedError("; ".join(plan.refusals))
    upserts = []
    for document in plan.writes:
        upserts.append(await _upsert(document, embed))
        progress(len(upserts), len(plan.writes))
    return await store.sync_documents(
        namespace=namespace, upserts=upserts, deletes=plan.delete, expected_ids=plan.expected_ids
    )
