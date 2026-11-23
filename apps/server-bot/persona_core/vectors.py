"""The facts embedder: local all-MiniLM-L6-v2 (384d, normalized) through fi-core.

pgvector holds the vectors and runs the search; this module only owns the model.
A different model from the corpus one (`persona_core.corpus.pg_rag`, multilingual
e5): facts are short Spanish notes matched against each other, not against English
sources.
"""

from __future__ import annotations

from functools import lru_cache

EMBEDDING_DIM = 384
MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_model():
    """The process-wide facts embedder (a `fi_core.rag.protocols.Embedder`); the model loads on first use."""
    from fi_core.embeddings.sentence_transformers import SentenceTransformersEmbedder

    return SentenceTransformersEmbedder(MODEL_NAME, normalize=True)
