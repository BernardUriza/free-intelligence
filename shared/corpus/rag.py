"""In-memory retrieval over the fine animal-liberation tactics (Phase B).

Bernard's call: in-memory, no store, no migration — the tactics corpus is small
and static (~12 objection blocks). Chunking uses `fi_core.rag` (the reason this
is "RAG con fi_core"); the embedder is INJECTED by the caller, never imported
here, so `shared/` keeps zero dependency on `insult/` or `alice/`.

Two retrieval modes, picked by what the caller can provide:
- **Semantic** when an `embed` callable is passed (Insult/discord-bot has the
  sentence-transformers `EmbeddingModel`). Cosine over cached chunk embeddings.
- **Lexical** fallback when `embed` is None (ALICE runs at 1Gi with no embedder
  wired — loading sentence-transformers there risks the very OOM we just fixed
  on the runner). Term-overlap scoring. Same corpus, retrieval degrades, never
  breaks.

The retrieved tactic blocks are appended UNDER the always-on values frame
(animal_liberation.md, Phase A) so values lead and tactics support.
"""

from __future__ import annotations

import math
import re
import threading
from pathlib import Path
from typing import Protocol

import structlog

log = structlog.get_logger()

_TACTICS_PATH = Path(__file__).parent / "animal_liberation_tactics.md"
# chunk_size tuned small so each objection block stays its own retrievable unit
# instead of three objections fused into one fuzzy chunk.
_CHUNK_SIZE = 120
_SEMANTIC_MIN = 0.25  # cosine floor for all-MiniLM (normalized) relevance
_LEXICAL_MIN = 0.12  # query-term overlap fraction floor

_lock = threading.Lock()
_chunks: list[str] | None = None
_chunk_embeddings: list[list[float]] | None = None


class _Embed(Protocol):
    def __call__(self, text: str) -> list[float]: ...


def _strip_comment(raw: str) -> str:
    return re.sub(r"^<!--.*?-->\s*", "", raw, count=1, flags=re.DOTALL)


def _load_chunks() -> list[str]:
    """Chunk the tactics doc once (via fi_core), cache for the process."""
    global _chunks
    with _lock:
        if _chunks is None:
            try:
                from fi_core.rag import ChunkConfig, chunk_by_paragraphs

                raw = _strip_comment(_TACTICS_PATH.read_text(encoding="utf-8"))
                cfg = ChunkConfig(chunk_size=_CHUNK_SIZE, overlap=0, min_chunk_size=10)
                _chunks = chunk_by_paragraphs(raw, cfg)
                log.info("tactics_corpus_chunked", chunks=len(_chunks))
            except Exception:
                log.exception("tactics_corpus_chunk_failed")
                _chunks = []
        return _chunks


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# Stopwords (es + en) stripped before lexical overlap so common glue words
# ("de", "el", "y", "the") can't manufacture a false match against a chunk that
# shares nothing topical with the query.
_STOPWORDS = frozenset(
    [
        "de",
        "el",
        "la",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "y",
        "o",
        "que",
        "en",
        "a",
        "al",
        "del",
        "lo",
        "le",
        "les",
        "se",
        "su",
        "sus",
        "con",
        "por",
        "para",
        "como",
        "mas",
        "más",
        "pero",
        "si",
        "no",
        "ni",
        "es",
        "son",
        "fue",
        "ser",
        "está",
        "están",
        "este",
        "esta",
        "eso",
        "esa",
        "ese",
        "esto",
        "mi",
        "tu",
        "te",
        "me",
        "nos",
        "hoy",
        "muy",
        "ya",
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "is",
        "are",
        "and",
        "or",
        "for",
        "it",
        "this",
        "that",
        "with",
        "as",
        "be",
        "on",
        "i",
        "you",
        "he",
        "she",
        "they",
        "we",
    ]
)


def _lexical_score(query: str, chunk: str) -> float:
    q = {w for w in re.findall(r"\w+", query.lower()) if w not in _STOPWORDS}
    if not q:
        return 0.0
    c = set(re.findall(r"\w+", chunk.lower()))
    return len(q & c) / len(q)


def retrieve_tactics(
    query: str | None,
    *,
    embed: _Embed | None = None,
    top_k: int = 2,
) -> list[str]:
    """Return up to `top_k` tactic blocks most relevant to `query`.

    Semantic when `embed` is given, lexical otherwise. Empty list when nothing
    clears the relevance floor — the caller appends nothing rather than padding
    the turn with off-target tactics.
    """
    chunks = _load_chunks()
    if not query or not chunks:
        return []

    if embed is not None:
        global _chunk_embeddings
        with _lock:
            if _chunk_embeddings is None:
                try:
                    _chunk_embeddings = [embed(c) for c in chunks]
                except Exception:
                    log.exception("tactics_corpus_embed_failed")
                    _chunk_embeddings = []
        if _chunk_embeddings:
            try:
                qv = embed(query)
            except Exception:
                log.exception("tactics_query_embed_failed")
                return []
            scored = [(_cosine(qv, cv), c) for cv, c in zip(_chunk_embeddings, chunks, strict=False)]
            floor = _SEMANTIC_MIN
        else:
            scored = [(_lexical_score(query, c), c) for c in chunks]
            floor = _LEXICAL_MIN
    else:
        scored = [(_lexical_score(query, c), c) for c in chunks]
        floor = _LEXICAL_MIN

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for score, c in scored[:top_k] if score >= floor]
