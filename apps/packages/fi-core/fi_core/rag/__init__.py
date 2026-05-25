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
from fi_core.rag.contextual import (
    CallableContextualizer,
    Contextualizer,
    build_contextual_prompt,
)
from fi_core.rag.hybrid import (
    DEFAULT_RRF_K,
    HybridRetriever,
    reciprocal_rank_fusion,
)
from fi_core.rag.mcp_contract import MCP_SERVER_NAME, MCP_TOOLS
from fi_core.rag.protocols import ChunkStore, DocumentChunkStore, Embedder
from fi_core.rag.retrieval import (
    DEFAULT_LEXICAL_MIN,
    DEFAULT_SEMANTIC_MIN,
    SPANISH_ENGLISH_STOPWORDS,
    LexicalRetriever,
    ScoredText,
    SemanticRetriever,
    cosine_similarity,
    fold_accents,
    tokenize,
)
from fi_core.rag.store_retrieval import StoreBackedRetriever
from fi_core.rag.types import (
    Chunk,
    ChunkWithEmbedding,
    DocumentMetadata,
    DocumentRecord,
    RetrievedChunk,
)

__all__ = [
    "DEFAULT_LEXICAL_MIN",
    "DEFAULT_SEMANTIC_MIN",
    "MCP_SERVER_NAME",
    "MCP_TOOLS",
    "SPANISH_ENGLISH_STOPWORDS",
    "Chunk",
    "ChunkConfig",
    "ChunkStore",
    "ChunkWithEmbedding",
    "ChunkingStrategy",
    "DocumentChunkStore",
    "DocumentMetadata",
    "DocumentRecord",
    "Embedder",
    "LexicalRetriever",
    "RetrievedChunk",
    "ScoredText",
    "SemanticRetriever",
    "StoreBackedRetriever",
    "Contextualizer",
    "CallableContextualizer",
    "build_contextual_prompt",
    "HybridRetriever",
    "reciprocal_rank_fusion",
    "DEFAULT_RRF_K",
    "chunk_by_fixed_size",
    "chunk_by_paragraphs",
    "chunk_by_sentences",
    "chunk_document",
    "cosine_similarity",
    "estimate_tokens",
    "fold_accents",
    "tokenize",
]
