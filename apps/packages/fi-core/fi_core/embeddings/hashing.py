"""HashingEmbedder — a zero-model, dep-free Embedder (the feature-hashing trick).

Maps text to a fixed-dim vector by hashing each accent-folded token into a bucket
and counting. No model download, no paid API, deterministic — cosine over these
vectors approximates lexical (term-overlap) similarity. It is the DEFAULT embedder
for the persistent RAG store so "upload files, query them" works with zero setup;
opt into a real semantic embedder (Azure / sentence-transformers) when you want
meaning beyond keywords.

Pure Python — part of the base ``fi-core`` install (no extra).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata


def _tokens(text: str) -> list[str]:
    """Accent-folded, lowercased word tokens (Spanish-friendly)."""
    folded = "".join(
        c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c)
    )
    return re.findall(r"\w+", folded)


class HashingEmbedder:
    """Feature-hashing :class:`~fi_core.rag.protocols.Embedder` — zero model."""

    def __init__(self, *, dim: int = 256) -> None:
        if dim <= 0:
            raise ValueError(f"HashingEmbedder: dim must be positive, got {dim!r}")
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    async def embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for tok in _tokens(text):
            # Stable cross-process bucket (Python's hash() is salted per run).
            bucket = int.from_bytes(hashlib.blake2b(tok.encode(), digest_size=8).digest(), "big") % self._dim
            vec[bucket] += 1.0
        return vec


__all__ = ["HashingEmbedder"]
