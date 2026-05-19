"""fi_core.rag — chunking + embedder/store protocols.

The chunking algorithm is shipped here (pure Python, zero deps).
The Embedder + ChunkStore protocols are interfaces the consumer
implements with its own deployment-specific stack.
"""

from fi_core.rag.chunking import (
    ChunkConfig,
    ChunkingStrategy,
    chunk_by_fixed_size,
    chunk_by_paragraphs,
    chunk_by_sentences,
    chunk_document,
    estimate_tokens,
)
from fi_core.rag.protocols import ChunkStore, DocumentChunkStore, Embedder
from fi_core.rag.types import (
    Chunk,
    ChunkWithEmbedding,
    DocumentMetadata,
    DocumentRecord,
    RetrievedChunk,
)

__all__ = [
    "Chunk",
    "ChunkConfig",
    "ChunkStore",
    "ChunkWithEmbedding",
    "ChunkingStrategy",
    "DocumentChunkStore",
    "DocumentMetadata",
    "DocumentRecord",
    "Embedder",
    "RetrievedChunk",
    "chunk_by_fixed_size",
    "chunk_by_paragraphs",
    "chunk_by_sentences",
    "chunk_document",
    "estimate_tokens",
]
