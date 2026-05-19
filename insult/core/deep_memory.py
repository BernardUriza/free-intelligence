"""Vector-search deep memory — RAG sibling Azure-native.

Replaces a planned dependency on the on-prem Free Intelligence / AURITY
RAG service for Insult. AURITY is HIPAA on-prem by design (clinic GPU +
Cloudflare Tunnel); Insult lives in Azure and processes no PHI, so a
co-located Azure-native RAG using the same Postgres pool and the same
Azure OpenAI cognitive account is the right fit.

Pieces:
- Storage: `deep_memory_chunks` table (vector(1536) + ivfflat index)
- Embeddings: Azure OpenAI `text-embedding-ada-002` deployment on the
  shared `insult-openai` account (1536 dims, $0.10/1M tokens)
- Query: cosine similarity via `embedding <=> $1`, filtered by user_id

Architecture mirrors `pg_state.py` and `html_artifacts.py`: one-shot
asyncpg connections per call. Volume is moderate (chunks ingest on the
siesta consolidator, queries on agent turns), and tying the module to
the bot's pool would force coupling no one needs.

Public API:
- `embed_text(text)` → 1536-dim numpy array (or None on failure)
- `insert_chunks(user_id, source_type, source_ref, chunks)` →
  embed each chunk and persist. Idempotent via the
  `idx_deep_memory_dedupe` unique index.
- `query_user_memory(user_id, query, top_k)` → list of
  {source_type, source_ref, chunk_text, similarity, created_at}
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import asyncpg
import structlog

log = structlog.get_logger()

EMBEDDING_DIM = 1536
EMBEDDING_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"
)
EMBEDDING_API_VERSION = os.environ.get(
    "AZURE_OPENAI_EMBEDDING_API_VERSION", "2024-02-01"
)


# ─── Embeddings ────────────────────────────────────────────────────────


async def embed_text(text: str) -> list[float] | None:
    """Generate one 1536-dim embedding via Azure OpenAI. None on failure.

    Uses the same `insult-openai` cognitive account ALICE uses for chat
    completions. The `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_KEY` env
    vars are already set on the discord-bot and insult-runner
    Container Apps (added 2026-05-19 for this feature).
    """
    if not text or not text.strip():
        return None
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.environ.get("AZURE_OPENAI_KEY", "")
    if not endpoint or not api_key:
        log.error("deep_memory_azure_openai_not_configured")
        return None
    try:
        from openai import AsyncAzureOpenAI

        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=EMBEDDING_API_VERSION,
        )
        resp = await client.embeddings.create(
            model=EMBEDDING_DEPLOYMENT,
            input=text,
        )
        vec = resp.data[0].embedding
        if len(vec) != EMBEDDING_DIM:
            log.error(
                "deep_memory_embedding_dim_mismatch",
                expected=EMBEDDING_DIM,
                got=len(vec),
            )
            return None
        return vec
    except Exception:
        log.exception("deep_memory_embed_failed", text_len=len(text))
        return None


# ─── Storage ───────────────────────────────────────────────────────────


async def _connect() -> asyncpg.Connection | None:
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return None
    try:
        conn = await asyncpg.connect(url)
        # Register pgvector codec so we can pass/receive list[float] as
        # `vector` directly without manual cast strings.
        try:
            from pgvector.asyncpg import register_vector

            await register_vector(conn)
        except Exception:
            log.warning("deep_memory_pgvector_codec_register_failed")
        return conn
    except Exception:
        log.exception("deep_memory_pg_connect_failed")
        return None


async def insert_chunks(
    *,
    user_id: str,
    source_type: str,
    source_ref: str,
    chunks: list[str],
) -> int:
    """Embed each chunk and INSERT. Returns # newly inserted rows.

    Idempotent: `idx_deep_memory_dedupe` ON (user_id, source_ref, md5(chunk_text))
    drops duplicates silently via ON CONFLICT DO NOTHING. Callers can
    safely re-run the backfill script without exploding the table.

    Empty chunks and embed failures are skipped, not raised — partial
    success is more useful than all-or-nothing for a batch backfill.
    """
    if not user_id or source_type not in {"message", "disclosure", "fact", "manual"}:
        return 0
    chunks = [c.strip() for c in chunks if c and c.strip()]
    if not chunks:
        return 0
    conn = await _connect()
    if conn is None:
        return 0
    inserted = 0
    try:
        for chunk in chunks:
            vec = await embed_text(chunk)
            if vec is None:
                continue
            result = await conn.execute(
                """
                INSERT INTO deep_memory_chunks
                  (user_id, source_type, source_ref, chunk_text, embedding)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, source_ref, md5(chunk_text)) DO NOTHING
                """,
                user_id,
                source_type,
                source_ref,
                chunk,
                vec,
            )
            # "INSERT 0 1" on success, "INSERT 0 0" on conflict-skip
            if result.endswith(" 1"):
                inserted += 1
        log.info(
            "deep_memory_chunks_inserted",
            user_id=user_id,
            source_type=source_type,
            source_ref=source_ref,
            considered=len(chunks),
            inserted=inserted,
        )
        return inserted
    finally:
        await conn.close()


# ─── Query ─────────────────────────────────────────────────────────────


async def query_user_memory(
    *, user_id: str, query: str, top_k: int = 5
) -> list[dict[str, Any]]:
    """Embed `query` and return the top-k closest chunks for `user_id`.

    Cosine distance via `embedding <=> $1` (pgvector's smaller-is-closer
    semantics). The returned `similarity` is `1 - distance` so the agent
    can interpret it intuitively (1.0 = identical).

    Returns [] on any failure path (no PG, no embedding service, user
    with no chunks) — the agent treats absence-of-memory as a valid
    answer, not an error.
    """
    if not user_id or not query or top_k <= 0:
        return []
    vec = await embed_text(query)
    if vec is None:
        return []
    conn = await _connect()
    if conn is None:
        return []
    try:
        rows = await conn.fetch(
            """
            SELECT source_type, source_ref, chunk_text, created_at,
                   1 - (embedding <=> $1) AS similarity
            FROM deep_memory_chunks
            WHERE user_id = $2
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
        log.exception(
            "deep_memory_query_failed", user_id=user_id, query_len=len(query)
        )
        return []
    finally:
        await conn.close()


# ─── Chunking — re-exports from fi_core.rag (the shared package) ──────


def chunk_text_for_embedding(text: str, chunk_size: int = 400, overlap: int = 50) -> list[str]:
    """Thin wrapper over ``fi_core.rag.chunk_document``.

    Same algorithm AURITY and fi-monitor use — the chunking layer is
    extracted into the `fi-core` workspace package (lives at
    ``free-intelligence/apps/packages/fi-core``) so all three consumers
    share one implementation. Defaults are 400-token chunks with
    50-token overlap and a 50-token minimum, PARAGRAPH_AWARE to keep
    conversation transcripts semantically coherent.

    Why kept as a wrapper: ``deep_memory.py``'s callers (the backfill
    script + the ingest hook) already use this name; routing through
    the wrapper lets us swap defaults here without touching them.
    """
    if not text or not text.strip():
        return []
    from fi_core.rag import ChunkConfig, ChunkingStrategy, chunk_document

    return chunk_document(
        text,
        strategy=ChunkingStrategy.PARAGRAPH_AWARE,
        config=ChunkConfig(chunk_size=chunk_size, overlap=overlap, min_chunk_size=50),
    )


# ─── Convenience formatter ─────────────────────────────────────────────


def _fmt_age(dt: datetime | None) -> str:
    if dt is None:
        return "?"
    return dt.strftime("%Y-%m-%d")
