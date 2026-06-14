"""In-memory retrieval over the fine animal-liberation tactics (Phase B).

Bernard's call: in-memory, no store, no migration — the tactics corpus is small
and static (13 objection blocks). The embedder is INJECTED by the caller, never
imported here, so `shared/` keeps zero dependency on `insult/` or `alice/`.

Chunking is structure-aware (split per `## ` objection header), NOT fi_core's
token-based chunk_by_paragraphs — the /histerical-search of 2026-05-22 proved
the latter fused objections and added retrieval noise on this header-structured
corpus. See `_load_chunks`.

Two retrieval modes:
- **Lexical** (the default both bots use as of the post-histerical-search pulido):
  term-overlap with es/en stopwords stripped. On a corpus of distinct objections
  with sharp keywords (welfarism, omnívoro, granja…) it scored 6/6 — and it's
  free, model-less, identical in Insult and ALICE.
- **Semantic** still available when an `embed` callable is passed (cosine over
  cached chunk embeddings), but unused by default: all-MiniLM-L6-v2 is
  English-centric (weak in Spanish) and added nothing over lexical here.

The retrieved tactic blocks are appended UNDER the always-on values frame
(animal_liberation.md, Phase A) so values lead and tactics support.
"""

from __future__ import annotations

import math
import re
import threading
import unicodedata
from pathlib import Path
from typing import Protocol

import structlog

log = structlog.get_logger()

_TACTICS_PATH = Path(__file__).parent / "animal_liberation_tactics.md"
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
    """Split the tactics doc into one chunk per `## ` objection block.

    Structure-aware chunking. The /histerical-search of 2026-05-22 proved
    fi_core.chunk_by_paragraphs (token-based, built for prose) was the WRONG
    tool for this corpus: at chunk_size=120 it fused two objections per chunk
    (the neighbor objection became retrieval noise) and let the leading H1
    contaminate the first block — retrieval looked ~50% wrong. This corpus is a
    flat list of `## ` objections, so splitting on those headers gives 13
    self-contained, single-objection chunks — the "align chunking with document
    structure" best practice (extend.ai, 2026). The H1/preamble before the
    first `## ` is dropped: it's not an objection.
    """
    global _chunks
    with _lock:
        if _chunks is None:
            try:
                raw = _strip_comment(_TACTICS_PATH.read_text(encoding="utf-8"))
                blocks = re.split(r"(?m)^(?=## )", raw)
                _chunks = [b.strip() for b in blocks if b.strip().startswith("## ")]
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


def _norm(text: str) -> str:
    """Lowercase + strip accents. Spanish users type "religion"/"omnivoros"
    without tildes constantly, while the corpus is correctly accented — without
    folding, "religion" (query) never matches "religión" (chunk) and recall
    collapses. NFKD + drop combining marks folds áéíóúñ→aeioun (ñ→n is fine for
    keyword overlap)."""
    return "".join(ch for ch in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(ch))


def _terms(text: str) -> set[str]:
    return set(re.findall(r"\w+", _norm(text)))


def _lexical_score(query: str, chunk: str) -> float:
    q = {w for w in _terms(query) if w not in _STOPWORDS}
    if not q:
        return 0.0
    return len(q & _terms(chunk)) / len(q)


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
