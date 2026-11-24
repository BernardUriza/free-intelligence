"""Per-user deep memory — vector search over a user's stored chunks.

Storage is `deep_memory_chunks` (vector(384), exact search: no vector index), shared with the
per-persona corpus; only the partition key differs (a real user_id here, a
`__corpus_*__` namespace there). Embeddings come from the local multilingual e5
model in `persona_core.corpus.pg_rag`.

Read-only today. The writer (the siesta consolidator's incremental ingest) was
deleted with the consolidator on 2026-08-06, and the per-turn reader
(`build_user_memory_block`) never had a live caller after the purge; both were
removed on 2026-11-20 instead of staying as code that looked wired. The one
consumer is the runner's `deep_memory` MCP tool, over the chunks that exist.

Public API:
- `query_user_memory(user_id, query, top_k)` → list of
  {source_type, source_ref, chunk_text, similarity, created_at}, or None when
  retrieval could not run
"""

from __future__ import annotations

from typing import Any

import structlog

from persona_core.corpus.pg_rag import connect as _connect
from persona_core.corpus.pg_rag import embed_query

log = structlog.get_logger()


async def query_user_memory(*, user_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]] | None:
    """Embed `query` and return the top-k closest chunks for `user_id`.

    `similarity` is `1 - cosine distance` (1.0 = identical). Returns [] when the
    search ran and found nothing, None when it could not run (embedder or
    Postgres down): a caller that tells the model "you have no memory of this"
    must be able to tell the two apart.
    """
    if not user_id or not query or top_k <= 0:
        return []
    vec = await embed_query(query)
    if vec is None:
        return None
    conn = await _connect()
    if conn is None:
        return None
    try:
        rows = await conn.fetch(
            """
            SELECT source_type, source_ref, chunk_text, created_at,
                   1 - (embedding <=> $1) AS similarity
            FROM deep_memory_chunks
            WHERE user_id = $2 AND embedding IS NOT NULL
            ORDER BY embedding <=> $1
            LIMIT $3
            """,
            vec,
            user_id,
            top_k,
        )
        return [
            {
                "source_type": r["source_type"],
                "source_ref": r["source_ref"],
                "chunk_text": r["chunk_text"],
                "similarity": float(r["similarity"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    except Exception:
        log.exception("deep_memory_query_failed", user_id=user_id, query_len=len(query))
        return None
    finally:
        await conn.close()
