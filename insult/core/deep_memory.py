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
from datetime import UTC, datetime
from typing import Any

import asyncpg
import structlog

log = structlog.get_logger()

EMBEDDING_DIM = 1536
EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
EMBEDDING_API_VERSION = os.environ.get("AZURE_OPENAI_EMBEDDING_API_VERSION", "2024-02-01")


# ─── Embeddings ────────────────────────────────────────────────────────


class EmbeddingDimensionError(RuntimeError):
    """The Azure deployment returned a vector whose dim doesn't match EMBEDDING_DIM.

    Raised by `AzureOpenAIEmbedder.embed()` instead of silently returning
    None — the embedder Protocol contract is "raise on failure". A
    dimension mismatch is almost always a deployment misconfiguration
    (someone pointed the env var at `text-embedding-3-large` which is
    3072 dims) and should fail loud, not corrupt the index silently.
    """


class AzureOpenAIEmbedder:
    """`fi_core.rag.Embedder` Protocol implementation for Azure OpenAI.

    Implements the structural contract (`async def embed(self, text: str)
    -> list[float]`) defined in `fi_core.rag.protocols.Embedder`. Duck-
    typed: `isinstance(emb, Embedder)` returns True via @runtime_checkable.

    Holds endpoint/key/deployment as instance state and reuses the
    AsyncAzureOpenAI client across calls. Constructing one embedder
    per worker (rather than per call) avoids re-opening the HTTP
    connection pool for every embed.

    Configuration precedence: explicit constructor args > env vars >
    module defaults. Most consumers just call `AzureOpenAIEmbedder()`
    and let the env vars do the work — same env vars the discord-bot
    and insult-runner Container Apps already have set.
    """

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self.endpoint = (endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_KEY", "")
        self.deployment = deployment or EMBEDDING_DEPLOYMENT
        self.api_version = api_version or EMBEDDING_API_VERSION
        self._client: object | None = None  # lazy AsyncAzureOpenAI

    def _get_client(self):
        """Lazily build the Azure client. Reused across embed() calls."""
        if self._client is not None:
            return self._client
        if not self.endpoint or not self.api_key:
            raise RuntimeError(
                "AzureOpenAIEmbedder requires AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_KEY (env vars or constructor args)"
            )
        from openai import AsyncAzureOpenAI

        self._client = AsyncAzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )
        return self._client

    async def embed(self, text: str) -> list[float]:
        """Return a `EMBEDDING_DIM`-element vector for ``text``.

        Raises (per Protocol contract):
        - `ValueError` if ``text`` is empty / whitespace-only.
        - `RuntimeError` if endpoint/key aren't configured.
        - `EmbeddingDimensionError` if the deployment returns a
          wrong-sized vector (deployment misconfiguration).
        - Whatever the openai SDK raises (auth, rate-limit, etc.) —
          surfaced unwrapped so the caller can branch on `RateLimitError`,
          `APITimeoutError`, etc. without parsing strings.
        """
        if not text or not text.strip():
            raise ValueError("AzureOpenAIEmbedder.embed: text must be non-empty")
        client = self._get_client()
        resp = await client.embeddings.create(model=self.deployment, input=text)
        vec = resp.data[0].embedding
        if len(vec) != EMBEDDING_DIM:
            raise EmbeddingDimensionError(
                f"Expected {EMBEDDING_DIM}-dim vector, got {len(vec)} from deployment '{self.deployment}'"
            )
        return vec


# Module-level singleton built lazily on first use. Avoids paying the
# openai client construction cost on every embed_text() call.
_default_embedder: AzureOpenAIEmbedder | None = None


def _get_default_embedder() -> AzureOpenAIEmbedder:
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = AzureOpenAIEmbedder()
    return _default_embedder


async def embed_text(text: str) -> list[float] | None:
    """Back-compat convenience: embed `text`, return None on failure.

    Pre-DM-5 callers used this function directly; it survives so the
    backfill script and the MCP tool don't have to change. New code
    should prefer constructing an `AzureOpenAIEmbedder` explicitly and
    handling its exceptions, which gives the caller real failure-mode
    granularity instead of a binary None / not-None.

    Catches and swallows all exceptions, logging each via structlog.
    Callers who need to distinguish auth-failure from rate-limit from
    dim-mismatch should use `AzureOpenAIEmbedder.embed` directly.
    """
    if not text or not text.strip():
        return None
    try:
        return await _get_default_embedder().embed(text)
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
