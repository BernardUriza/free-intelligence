"""The corpus — a consumer's uploaded documents, searchable, in the owner's database.

The storage half of `rag_store` (backlog #46). fi-core keeps a corpus on disk with
an embedder, an hdf5 store and a reranker — two thousand lines that assume a
machine with room, on a droplet with 512 MB and a $20/mo ceiling ([[do-budget]]).
What actually decides it is the law: the memory lives in the OWNER'S database,
never on the mortal box ([[log-is-the-truth]] prohibition 2), and a corpus on the
droplet's disk dies with the droplet.

So the retrieval is Postgres's own full-text search — `tsvector` plus a GIN index,
already shipping inside the database that holds the transcript. No embedder, no
model, no network. It matches on words rather than meaning, which is a real
ceiling and an honest one.

Indexed with the `spanish` configuration: it drops the stopwords that would
otherwise dominate every query ("de", "la", "que") and stems the rest. An English
document still matches its own unstemmed words — degraded, not broken.

SCOPE, and its honest boundary: rows are namespaced by `owner`, the consumer that
wrote them (a casita's `@base`, so every chat of one consumer shares one shelf and
another consumer's casita cannot reach it). Distinguishing that consumer's END
USERS from each other is the CONSUMER's job, done by making `corpus_id` a
per-user id — the same guarantee its local store gave, carried over unchanged.
"""

from __future__ import annotations

import asyncio

from . import db
from .chunking import chunk

TABLE = "aire_corpus_chunk"
MAX_TOP_K = 20
SNIPPET = 600
STATEMENT_TIMEOUT_MS = 5_000

DDL = (
    f"CREATE TABLE IF NOT EXISTS {TABLE} ("
    " seq bigserial PRIMARY KEY,"
    " at timestamptz NOT NULL DEFAULT now(),"
    " owner text NOT NULL,"
    " corpus_id text NOT NULL,"
    " doc_id text NOT NULL,"
    " ord int NOT NULL,"
    " body text NOT NULL,"
    " fts tsvector GENERATED ALWAYS AS (to_tsvector('spanish', body)) STORED)"
)
INDEXES = (
    f"CREATE INDEX IF NOT EXISTS aire_corpus_fts ON {TABLE} USING GIN (fts)",
    f"CREATE INDEX IF NOT EXISTS aire_corpus_doc ON {TABLE} (owner, corpus_id, doc_id)",
)

_ready = False
_lock = asyncio.Lock()


async def ensure() -> None:
    """The table, committed and visible to other connections, before anything
    writes — on its OWN connection outside any transaction, for the reason
    `spend.ensure` documents in full: a flag flipped over an uncommitted CREATE
    sends every other coroutine at a table it cannot see."""
    global _ready
    if _ready or not db.dsn():
        return
    async with _lock:
        if _ready:
            return
        async with db.acquire() as conn:
            await conn.execute(DDL)
            for index in INDEXES:
                await conn.execute(index)
        _ready = True


async def ingest(owner: str, corpus_id: str, doc_id: str, text: str) -> int:
    """Replace a document with its chunks, and return how many landed. Replace,
    not append: re-uploading a corrected file must not leave the old sentences
    searchable beside the new ones."""
    await ensure()
    chunks = chunk(text)
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        await conn.execute(f"DELETE FROM {TABLE} WHERE owner=$1 AND corpus_id=$2 AND doc_id=$3",
                           owner, corpus_id, doc_id)
        await conn.executemany(
            f"INSERT INTO {TABLE} (owner, corpus_id, doc_id, ord, body) VALUES ($1,$2,$3,$4,$5)",
            [(owner, corpus_id, doc_id, i, body) for i, body in enumerate(chunks)])
    return len(chunks)


async def search(owner: str, corpus_id: str, query: str, top_k: int) -> list[dict]:
    """The best-ranked chunks for a query, within ONE corpus of ONE owner.

    `websearch_to_tsquery` because the query is written by a model in prose: it
    tolerates quotes, `or`, and a bare sentence, where `to_tsquery` raises on the
    first stray character and would turn a retrieval into an error mid-turn."""
    await ensure()
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        rows = await conn.fetch(
            f"SELECT doc_id, ord, left(body, {SNIPPET}) AS body,"
            " ts_rank(fts, websearch_to_tsquery('spanish', $3)) AS rank"
            f" FROM {TABLE}"
            " WHERE owner=$1 AND corpus_id=$2"
            "   AND fts @@ websearch_to_tsquery('spanish', $3)"
            " ORDER BY rank DESC, seq LIMIT $4",
            owner, corpus_id, query, min(max(1, top_k), MAX_TOP_K))
    return [{"doc_id": r["doc_id"], "chunk": r["ord"], "text": r["body"],
             "score": round(float(r["rank"]), 4)} for r in rows]


async def documents(owner: str, corpus_id: str) -> list[dict]:
    await ensure()
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        rows = await conn.fetch(
            f"SELECT doc_id, count(*) AS chunks, max(at) AS at FROM {TABLE}"
            " WHERE owner=$1 AND corpus_id=$2 GROUP BY doc_id ORDER BY max(at) DESC",
            owner, corpus_id)
    return [{"doc_id": r["doc_id"], "chunks": r["chunks"], "at": r["at"].isoformat()}
            for r in rows]


async def drop(owner: str, corpus_id: str, doc_id: str | None = None) -> int:
    """Delete one document, or the whole corpus when `doc_id` is None. Returns the
    rows removed, so a delete that matched nothing can say so instead of
    reporting a success the caller cannot distinguish from a typo."""
    await ensure()
    sql = f"DELETE FROM {TABLE} WHERE owner=$1 AND corpus_id=$2"
    args: tuple = (owner, corpus_id)
    if doc_id is not None:
        sql, args = sql + " AND doc_id=$3", (owner, corpus_id, doc_id)
    async with db.acquire(statement_timeout_ms=STATEMENT_TIMEOUT_MS) as conn:
        tag = await conn.execute(sql, *args)
    return int(tag.rsplit(" ", 1)[-1] or 0)
