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

from datetime import UTC, datetime
from typing import Any

import structlog

from persona_core.corpus.pg_rag import (
    EMBEDDING_API_VERSION as EMBEDDING_API_VERSION,
)
from persona_core.corpus.pg_rag import (
    EMBEDDING_DEPLOYMENT as EMBEDDING_DEPLOYMENT,
)
from persona_core.corpus.pg_rag import (
    EMBEDDING_DIM as EMBEDDING_DIM,
)
from persona_core.corpus.pg_rag import (
    AzureOpenAIEmbedder as AzureOpenAIEmbedder,
)
from persona_core.corpus.pg_rag import (
    EmbeddingDimensionError as EmbeddingDimensionError,
)
from persona_core.corpus.pg_rag import connect as _connect
from persona_core.corpus.pg_rag import embed_text

# RAG primitives + the shared per-persona corpus retrieval live in
# persona_core.corpus (generalized from the film-only module 2026-07-16:
# `references.py`, namespace declared per persona in the registry). The
# per-user memory below consumes the neutral embedder/connection from there.
from persona_core.corpus.references import fit_to_budget
from persona_core.corpus.references import (
    query_corpus as query_corpus,
)
from persona_core.prompts import SHARED_PROMPTS_DIR, PromptCache, load_prompt

log = structlog.get_logger()
_PROMPT_CACHE: PromptCache = {}

# ─── Storage ───────────────────────────────────────────────────────────


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


async def query_user_memory(*, user_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
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
        log.exception("deep_memory_query_failed", user_id=user_id, query_len=len(query))
        return []
    finally:
        await conn.close()


# Tuning for the per-turn user-memory injection (v4.3.0 auto-retrieval).
# Mirrors the film-corpus knobs below so the two retrieval paths behave
# consistently. Lived in cogs/chat/stages.py until the RetrievalPort seam
# moved rendering ownership into this domain service (PR-D).
_USER_MEMORY_TOP_K = 4
# ada-002 nunca produce cosenos <0.4 ni entre textos ajenos (rango real ~[0.65,
# 0.95]) — el 0.30 histórico jamás filtró un solo hit. 0.75, más suave que el
# 0.78 del corpus a propósito: perder recall de memoria del usuario cuesta más
# que colar un chunk tibio (la clase de P0 "larisa never remembered"). Calibrar
# con telemetría antes de subirlo (2026-07-16).
_USER_MEMORY_MIN_SIMILARITY = 0.75
_USER_MEMORY_MIN_QUERY_LEN = 12  # skip "ok"/"jaja" — not worth an embed call
_USER_MEMORY_MAX_CHARS = 2000  # cap injected context so the turn stays bounded


async def build_user_memory_block(*, user_id: str, text: str | None) -> str | None:
    """Retrieve the user's most relevant raw-history chunks and format them
    for prompt injection.

    Mirror of `corpus.references.build_references_block` for the per-user partition: owns
    the similarity floor, the char budget and the authoritative header, so the
    turn pipeline consumes a finished block instead of raw hits. Returns the
    labeled block or None when the message is trivial, retrieval fails, or
    nothing clears the similarity floor. Callers (the RetrievalPort adapter)
    wrap this in try/except — a failure here NEVER breaks the turn.

    The header is authoritative on purpose (v4.8.x): the previous "úsalo solo
    si aplica" let the model dismiss this block — it answered "no la tengo"
    about Larisa even with her chunk delivered here (2026-05-24). These
    fragments ARE in the bot's memory of this user; if the message asks about
    something they cover, the bot must answer from them and MUST NOT claim it
    has no record.
    """
    query = (text or "").strip()
    if len(query) < _USER_MEMORY_MIN_QUERY_LEN:
        return None
    hits = await query_user_memory(user_id=user_id, query=query, top_k=_USER_MEMORY_TOP_K)
    relevant = [h for h in hits if h.get("similarity", 0.0) >= _USER_MEMORY_MIN_SIMILARITY]
    if not relevant:
        return None

    kept, truncated = fit_to_budget([f"- {h['chunk_text'].strip()}" for h in relevant], _USER_MEMORY_MAX_CHARS)

    log.info(
        "deep_memory_prefetched",
        user_id=user_id,
        hits=len(kept),
        top_similarity=round(relevant[0].get("similarity", 0.0), 3),
        dropped_over_budget=len(relevant) - len(kept),
        truncated=truncated,
    )
    lines = [line for _, line in kept]
    return load_prompt(SHARED_PROMPTS_DIR, "deep_memory_header", _PROMPT_CACHE) + "\n" + "\n".join(lines)


# ─── Incremental ingest (siesta consolidator hook, DM-6) ──────────────


async def ingest_new_user_messages(user_id: str, *, lookback_days_initial: int = 180) -> int:
    """Incrementally ingest a user's new messages into deep_memory_chunks.

    Designed to be called from the siesta consolidator after the user's
    fact consolidation completes. Behavior:

    1. Look up the most recent ``created_at`` for this user's chunks in
       ``deep_memory_chunks``. That's our cutoff — anything older has
       already been embedded.
    2. If no prior chunks exist for the user, treat them as new and
       backfill ``lookback_days_initial`` days (default 180) — same
       window the standalone ``scripts/backfill_deep_memory.py`` uses.
    3. Pull ``role='user'`` messages after the cutoff, format them
       chronologically, chunk via fi_core, embed via the module-level
       Azure embedder, INSERT with the schema's ON CONFLICT DO NOTHING.

    Returns the number of newly inserted chunks. Errors are logged but
    NOT raised — the consolidator should never fail because the
    incremental ingest hiccuped (consolidation success is the more
    important commit, ingest is best-effort enrichment).

    Idempotent on re-run: if no new messages arrived since the last
    cutoff, returns 0.
    """
    if not user_id:
        return 0
    conn = await _connect()
    if conn is None:
        log.warning("deep_memory_ingest_no_pg", user_id=user_id)
        return 0
    try:
        cutoff_row = await conn.fetchrow(
            "SELECT MAX(created_at) AS last_at FROM deep_memory_chunks WHERE user_id = $1",
            user_id,
        )
        last_at = cutoff_row["last_at"] if cutoff_row else None
        if last_at is None:
            # No prior chunks — seed with the standard initial window.
            since_epoch = (datetime.now(UTC).timestamp()) - lookback_days_initial * 86400
            window_label = f"seed-{lookback_days_initial}d"
        else:
            # Tiny safety margin so we don't miss a message whose
            # timestamp equals the cutoff (insertion order != message ts).
            since_epoch = last_at.timestamp() - 1.0
            window_label = "incremental"

        rows = await conn.fetch(
            """
            SELECT id, channel_id, user_name, content, timestamp
            FROM messages
            WHERE user_id = $1
              AND timestamp >= $2
              AND role = 'user'
            ORDER BY timestamp ASC
            """,
            user_id,
            since_epoch,
        )
        if not rows:
            log.info("deep_memory_ingest_no_new_messages", user_id=user_id, window=window_label)
            return 0

        first_ts = rows[0]["timestamp"]
        last_ts = rows[-1]["timestamp"]
        doc = "\n\n".join(
            f"[{datetime.fromtimestamp(r['timestamp'], tz=UTC).strftime('%Y-%m-%d %H:%M')}] "
            f"{r['user_name']}: {r['content']}"
            for r in rows
        )
        chunks = chunk_text_for_embedding(doc, chunk_size=400, overlap=50)
        if not chunks:
            log.info(
                "deep_memory_ingest_no_chunks_after_filter",
                user_id=user_id,
                msg_count=len(rows),
            )
            return 0
        # source_ref encodes the time window so re-runs of the same
        # cutoff don't collide on the dedupe index (idx_deep_memory_dedupe).
        source_ref = f"messages:{window_label}:{int(first_ts)}-{int(last_ts)}"
        inserted = await insert_chunks(
            user_id=user_id,
            source_type="message",
            source_ref=source_ref,
            chunks=chunks,
        )
        log.info(
            "deep_memory_ingest_complete",
            user_id=user_id,
            window=window_label,
            msg_count=len(rows),
            chunks_produced=len(chunks),
            chunks_inserted=inserted,
        )
        return inserted
    except Exception:
        log.exception("deep_memory_ingest_failed", user_id=user_id)
        return 0
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
