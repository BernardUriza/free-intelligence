"""Persona-neutral pgvector RAG primitives — the shared retrieval substrate.

Both the per-user memory (`deep_memory`) and the shared per-persona corpus
retrieval (`references`, one namespace per persona in the registry) sit on top
of these:

- `CorpusEmbedder` — local `intfloat/multilingual-e5-small` (384d, normalized)
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
import threading

import asyncpg
import structlog

log = structlog.get_logger()

EMBEDDING_DIM = 384
CORPUS_MODEL = "intfloat/multilingual-e5-small"
_QUERY_PREFIX = "query: "
_PASSAGE_PREFIX = "passage: "
RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
_RERANK_MAX_PASSAGE_CHARS = 1500


class EmbeddingDimensionError(RuntimeError):
    """The model returned a vector whose dim doesn't match EMBEDDING_DIM.

    A mismatch means someone swapped `CORPUS_MODEL` for a model of another
    size; writing those vectors would corrupt the index, so it fails loud.
    """


class CorpusEmbedder:
    """Lazy, thread-safe singleton over the multilingual e5 model.

    e5 is trained with role prefixes: a search text is embedded as
    `query: ...` and a stored chunk as `passage: ...`. Mixing them up still
    returns vectors, just worse rankings, so the two entry points are separate
    methods instead of a flag a caller can forget.
    """

    def __init__(self, model_name: str = CORPUS_MODEL) -> None:
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                log.info("corpus_embedder_loaded", model=self.model_name, dim=EMBEDDING_DIM)
        return self._model

    def _encode(self, text: str) -> list[float]:
        vec = self._ensure_model().encode(text, normalize_embeddings=True)
        out = [float(x) for x in vec]
        if len(out) != EMBEDDING_DIM:
            raise EmbeddingDimensionError(
                f"Expected {EMBEDDING_DIM}-dim vector, got {len(out)} from '{self.model_name}'"
            )
        return out

    async def embed(self, text: str, *, role: str) -> list[float]:
        """Embed `text` as a `query` or a `passage`; raises on failure."""
        if not text or not text.strip():
            raise ValueError("CorpusEmbedder.embed: text must be non-empty")
        prefix = {"query": _QUERY_PREFIX, "passage": _PASSAGE_PREFIX}[role]
        return await asyncio.to_thread(self._encode, prefix + text.strip())


_default_embedder = CorpusEmbedder()


def get_corpus_embedder() -> CorpusEmbedder:
    return _default_embedder


async def _embed_or_none(text: str, role: str) -> list[float] | None:
    if not text or not text.strip():
        return None
    try:
        return await _default_embedder.embed(text, role=role)
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


class CorpusReranker:
    """Lazy, thread-safe singleton over a multilingual cross-encoder.

    The relevance gate. e5 cosines are compressed: measured 2026-11-19 on 21
    real queries, on-topic hits scored 0.784-0.888 and off-topic ones
    0.780-0.834, so no cosine floor separates them. The cross-encoder reads the
    question and the passage together: over 8 candidates, 8 of 11 on-topic
    queries clear -2.0 and 0 of 10 off-topic ones do (2026-11-20).
    """

    def __init__(self, model_name: str = RERANK_MODEL) -> None:
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _ensure_model(self):
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
                log.info("corpus_reranker_loaded", model=self.model_name)
        return self._model

    def _score(self, query: str, passages: list[str]) -> list[float]:
        pairs = [(query, p[:_RERANK_MAX_PASSAGE_CHARS]) for p in passages]
        return [float(x) for x in self._ensure_model().predict(pairs)]

    async def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        return await asyncio.to_thread(self._score, query, passages)


_default_reranker = CorpusReranker()


async def score_relevance(query: str, passages: list[str]) -> list[float] | None:
    """Cross-encoder relevance per passage; None on failure (logged)."""
    try:
        return await _default_reranker.score(query, passages)
    except Exception:
        log.exception("corpus_rerank_failed", passages=len(passages))
        return None


# ─── Storage ───────────────────────────────────────────────────────────


async def connect() -> asyncpg.Connection | None:
    """One-shot asyncpg connection with the pgvector codec registered.

    Iterative HNSW scan is on: the index returns its 40 nearest rows across the
    whole table before `WHERE user_id` filters, so a small namespace came back
    EMPTY on 12 of 21 measured queries (2026-11-19) without it.

    Reads POSTGRES_URL from the environment; returns None when it isn't set
    or the connection fails, so every caller can treat absence-of-PG as a
    valid (empty) answer rather than an error.
    """
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return None
    try:
        conn = await asyncpg.connect(url)
        try:
            from pgvector.asyncpg import register_vector

            await register_vector(conn)
        except Exception:
            log.warning("deep_memory_pgvector_codec_register_failed")
        await conn.execute("SET hnsw.iterative_scan = strict_order")
        return conn
    except Exception:
        log.exception("deep_memory_pg_connect_failed")
        return None
