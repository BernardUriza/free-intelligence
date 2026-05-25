"""In-memory retrieval scoring — the "recall" half of RAG.

fi_core.rag could chunk text and persist it (chunking + stores), but had no way
to RANK chunks against a query without a database. This adds the missing piece: a
zero-dep, model-less retriever for small static corpora held in memory.

Extracted from the production Discord bots (Insult + ALICE both ran an identical
copy of this over a tactics corpus). Two modes:

- **Lexical** (default): accent-folded query-term overlap with ES+EN stopwords
  stripped. Free, deterministic, no model. On a corpus of distinct items with
  sharp keywords it beats an English-centric embedder on Spanish text — which is
  why both bots use lexical by default.
- **Semantic**: cosine over caller-supplied embedding vectors, when you already
  have them (this module never calls an embedder — you pass the vectors).

    from fi_core.rag.retrieval import LexicalRetriever
    r = LexicalRetriever()
    hits = r.rank("¿es ético comer carne?", corpus_chunks, top_k=2)
    for h in hits:
        print(h.score, h.text[:60])

Accent folding matters for Spanish: users type "religion"/"omnivoro" without
tildes while a corpus is correctly accented — without folding, recall collapses.
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass

#: Common ES + EN glue words stripped before lexical overlap, so they can't
#: manufacture a false match against a chunk that shares nothing topical.
SPANISH_ENGLISH_STOPWORDS: frozenset[str] = frozenset({
    # Spanish
    "de", "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "que",
    "en", "a", "al", "del", "lo", "le", "les", "se", "su", "sus", "con", "por",
    "para", "como", "mas", "más", "pero", "si", "no", "ni", "es", "son", "fue",
    "ser", "está", "están", "este", "esta", "eso", "esa", "ese", "esto", "mi",
    "tu", "te", "me", "nos", "hoy", "muy", "ya",
    # English
    "the", "an", "of", "to", "in", "is", "are", "and", "or", "for", "it", "this",
    "that", "with", "as", "be", "on", "i", "you", "he", "she", "they", "we",
})

#: Default minimum lexical-overlap fraction for a hit to count.
DEFAULT_LEXICAL_MIN = 0.12
#: Default minimum cosine similarity for a semantic hit to count.
DEFAULT_SEMANTIC_MIN = 0.25


def fold_accents(text: str) -> str:
    """Lowercase and strip diacritics (áéíóúñ → aeioun) for matching.

    NFKD-decompose then drop combining marks. ñ→n is fine for keyword overlap.
    """
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(ch)
    )


def tokenize(text: str) -> set[str]:
    """Word tokens of `text`, accent-folded. Set-valued (overlap, not frequency)."""
    return set(re.findall(r"\w+", fold_accents(text)))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine of two equal-length vectors; 0.0 if either is a zero vector."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


@dataclass(frozen=True)
class ScoredText:
    """A retrieved text with its relevance score (higher = more relevant)."""

    text: str
    score: float


@dataclass
class LexicalRetriever:
    """Ranks texts by accent-folded query-term overlap. Zero-dep, model-less.

    The score is ``|query terms ∩ chunk terms| / |query terms|`` (after folding +
    stopword stripping) — the fraction of the query covered by the chunk, in
    [0, 1]. Injectable stopwords + floor so a deployment can tune without forking.
    """

    stopwords: frozenset[str] = SPANISH_ENGLISH_STOPWORDS
    min_score: float = DEFAULT_LEXICAL_MIN

    def score(self, query: str, text: str) -> float:
        """Fraction of the query's content terms present in `text` (0..1)."""
        q = {w for w in tokenize(query) if w not in self.stopwords}
        if not q:
            return 0.0
        return len(q & tokenize(text)) / len(q)

    def rank(
        self,
        query: str,
        texts: list[str],
        *,
        top_k: int = 2,
        min_score: float | None = None,
    ) -> list[ScoredText]:
        """Return up to `top_k` texts scoring at/above the floor, best first.

        Empty query or empty corpus → empty list. Nothing clears the floor →
        empty list (the caller appends nothing rather than padding with noise).
        """
        floor = self.min_score if min_score is None else min_score
        if not query or not texts:
            return []
        scored = [ScoredText(t, self.score(query, t)) for t in texts]
        scored.sort(key=lambda s: s.score, reverse=True)
        return [s for s in scored[:top_k] if s.score >= floor]


@dataclass
class SemanticRetriever:
    """Ranks texts by cosine over caller-supplied embeddings. Model-less here.

    This module never calls an embedder — you pass the query vector and the
    per-text vectors (compute them with whatever Embedder you like). Use this when
    you already have embeddings; otherwise prefer :class:`LexicalRetriever`, which
    needs no model and wins on short Spanish text.
    """

    min_score: float = DEFAULT_SEMANTIC_MIN

    def rank(
        self,
        query_vector: list[float],
        texts: list[str],
        text_vectors: list[list[float]],
        *,
        top_k: int = 2,
        min_score: float | None = None,
    ) -> list[ScoredText]:
        """Rank `texts` by cosine(query_vector, text_vectors[i]). Lengths must match."""
        floor = self.min_score if min_score is None else min_score
        if not texts or len(texts) != len(text_vectors):
            return []
        scored = [
            ScoredText(t, cosine_similarity(query_vector, v))
            for t, v in zip(texts, text_vectors, strict=False)
        ]
        scored.sort(key=lambda s: s.score, reverse=True)
        return [s for s in scored[:top_k] if s.score >= floor]
