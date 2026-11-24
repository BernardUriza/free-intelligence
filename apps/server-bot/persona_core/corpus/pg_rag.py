"""Persona-neutral pgvector RAG primitives — the shared retrieval substrate.

Both the per-user memory (`deep_memory`) and the shared per-persona corpus
retrieval (`references`, one namespace per persona in the registry) sit on top
of these:

- `get_corpus_embedder()` / `get_corpus_reranker()` — fi-core's local e5
  embedder and cross-encoder, configured for the corpus
- `embed_query(text)` / `embed_passage(text)` — embed with the e5 role prefix,
  None on failure
- `connect()` — one-shot asyncpg connection with the pgvector codec registered

The embedder runs in-process: no network, no key, no deployment. It replaced
Azure OpenAI ada-002 on 2026-11-20, after the key died with a 401 (from at least
2026-10-20) and Azure kept refusing new deployments with `715-123420`. It is a
DIFFERENT model from the facts embedder (`persona_core.vectors`, English-only
all-MiniLM-L6-v2): the corpus is mostly English sources read by Spanish speakers,
and only a multilingual model retrieves across that gap (measured: "vitamina B12
en el embarazo" → MiniLM-L6 returned a pozole recipe, e5 the pregnancy review).

Imports nothing from `personas.*`, which keeps `persona_core` free of any
persona dependency (tests/arch/test_arch_import_boundaries.py).
"""

from __future__ import annotations

import asyncio
import os
from functools import lru_cache

import asyncpg
import structlog
from fi_core.stores._pg import init_vector_connection

log = structlog.get_logger()

EMBEDDING_DIM = 384
CORPUS_MODEL = "intfloat/multilingual-e5-small"
CORPUS_TABLE_PREFIX = "corpus"
_QUERY_PREFIX = "query: "
_PASSAGE_PREFIX = "passage: "
RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
_RERANK_MAX_PASSAGE_CHARS = 1500


class EmbeddingDimensionError(RuntimeError):
    """The model returned a vector whose dim doesn't match EMBEDDING_DIM.

    A mismatch means someone swapped `CORPUS_MODEL` for a model of another
    size; writing those vectors would corrupt the index, so it fails loud.
    """


@lru_cache(maxsize=1)
def get_corpus_embedder():
    """The process-wide e5 embedder: `query: ` / `passage: ` prefixes, normalized vectors."""
    from fi_core.embeddings.sentence_transformers import SentenceTransformersEmbedder

    return SentenceTransformersEmbedder(
        CORPUS_MODEL, query_prefix=_QUERY_PREFIX, passage_prefix=_PASSAGE_PREFIX, normalize=True
    )


@lru_cache(maxsize=1)
def get_corpus_reranker():
    """The process-wide cross-encoder; passages are cut to `_RERANK_MAX_PASSAGE_CHARS`."""
    from fi_core.rag.rerank import BgeReranker

    return BgeReranker(RERANK_MODEL, max_chars=_RERANK_MAX_PASSAGE_CHARS)


async def encode(text: str, *, role: str) -> list[float]:
    """Embed `text` as a `query` or a `passage`; raises on failure or a wrong-size vector."""
    if not text or not text.strip():
        raise ValueError("encode: text must be non-empty")
    embedder = get_corpus_embedder()
    embed = {"query": embedder.embed_query, "passage": embedder.embed_passage}[role]
    vec = await embed(text.strip())
    if len(vec) != EMBEDDING_DIM:
        raise EmbeddingDimensionError(f"Expected {EMBEDDING_DIM}-dim vector, got {len(vec)} from '{CORPUS_MODEL}'")
    return vec


async def _embed_or_none(text: str, role: str) -> list[float] | None:
    if not text or not text.strip():
        return None
    try:
        return await encode(text, role=role)
    except Exception:
        log.exception("deep_memory_embed_failed", role=role, text_len=len(text))
        return None


async def embed_query(text: str) -> list[float] | None:
    """Embed a search text; None on failure (logged as `deep_memory_embed_failed`)."""
    return await _embed_or_none(text, "query")


async def embed_passage(text: str) -> list[float] | None:
    """Embed a chunk for storage; None on failure (logged as `deep_memory_embed_failed`)."""
    return await _embed_or_none(text, "passage")


async def warm_corpus_embedder() -> bool:
    """Load the model and embed one probe; True when retrieval can work.

    The only liveness signal the corpus has. Before 2026-11-20 it lived in the
    gateway alone, and the gateway was stopped on 2026-09-27, so the runner (the
    host that actually served turns) lost its library for a month in silence.
    Every host that retrieves calls this at boot. Never raises.
    """
    vec = await embed_query("corpus embed boot healthcheck")
    scores = await score_relevance("corpus boot healthcheck", ["boot healthcheck passage"]) if vec else None
    if vec is None or scores is None:
        log.error("corpus_embedder_unavailable", model=CORPUS_MODEL, note="corpus retrieval is DEAD on this replica")
        return False
    log.info("corpus_embedder_ready", model=CORPUS_MODEL, dim=len(vec))
    return True


async def embedding_model() -> str:
    """`model@commit` of the loaded embedder: a different 384d model must never pass for this one."""
    revision = await asyncio.to_thread(lambda: get_corpus_embedder().revision)
    if not revision:
        raise RuntimeError(f"{CORPUS_MODEL}: the loaded weights do not say which commit they are")
    return f"{CORPUS_MODEL}@{revision}"


async def stored_with_another_model() -> dict[str, int] | None:
    """Documents per stored `embed_model` that is not the loaded one; None when it could not be checked.

    Cosines between two models mean nothing and raise nothing, so a swap of the
    weights would degrade every answer in silence. Never raises.
    """
    conn = await connect()
    if conn is None:
        return None
    try:
        current = await embedding_model()
        rows = await conn.fetch(
            "SELECT attributes->>'embed_model' AS model, count(*) AS documents FROM corpus_documents "
            "WHERE attributes->>'embed_model' <> $1 GROUP BY 1",
            current,
        )
    except Exception:
        log.exception("corpus_embed_model_check_failed")
        return None
    finally:
        await conn.close()
    others = {row["model"]: row["documents"] for row in rows}
    if others:
        log.error("corpus_embed_model_mismatch", loaded=current, stored=others)
    return others


async def score_relevance(query: str, passages: list[str]) -> list[float] | None:
    """Cross-encoder relevance per passage; None on failure (logged)."""
    if not passages:
        return []
    try:
        return await asyncio.to_thread(get_corpus_reranker().score, query, passages)
    except Exception:
        log.exception("corpus_rerank_failed", passages=len(passages))
        return None


# ─── Storage ───────────────────────────────────────────────────────────


async def connect() -> asyncpg.Connection | None:
    """One-shot asyncpg connection with the pgvector codec registered.

    Searches are exact (no ANN index on `embedding`): an approximate index
    filters by `user_id` after its walk, so a namespace came back EMPTY on 12
    of 21 measured queries under HNSW (2026-11-19) and on 3 of 21 under a stray
    ivfflat (2026-11-20). The biggest namespace is ~2.4k rows; exact is ~10 ms.

    Reads POSTGRES_URL from the environment; returns None when it isn't set
    or the connection fails, so every caller can treat absence-of-PG as a
    valid (empty) answer rather than an error.
    """
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return None
    try:
        conn = await asyncpg.connect(url)
        await init_vector_connection(conn)
        return conn
    except Exception:
        log.exception("deep_memory_pg_connect_failed")
        return None
