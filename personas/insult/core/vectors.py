"""Legacy re-export shim — embedding-model utility moved to khimeras_shared.vectors (PR-1c).

A neutral MiniLM loader with zero persona content; the memory store depends on
it for fact embeddings, so it travels with memory into the shared layer. Single
source of truth: ``khimeras_shared.vectors``.
"""

from khimeras_shared.vectors import (
    EMBEDDING_DIM,
    MODEL_NAME,
    EmbeddingModel,
    get_embedding_model,
)

__all__ = ["EMBEDDING_DIM", "MODEL_NAME", "EmbeddingModel", "get_embedding_model"]
