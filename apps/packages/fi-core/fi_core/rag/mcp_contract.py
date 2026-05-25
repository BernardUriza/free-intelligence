"""MCP tool contract for fi_core.rag — zero-dep metadata.

Kept separate from :mod:`fi_core.rag.mcp_server` (which imports the MCP SDK) so
the contract is importable WITHOUT the ``mcp`` extra. A runner can do
``from fi_core.rag import MCP_SERVER_NAME, MCP_TOOLS`` to build the
``mcp__<server>__<tool>`` names it allows, then spawn the actual server with
``python -m fi_core.rag.mcp_server`` (which does need ``mcp``).
"""

from __future__ import annotations

MCP_SERVER_NAME = "fi-core-rag"

MCP_TOOLS: list[dict[str, str]] = [
    {"name": "chunk_document", "description": "Split a document into retrieval-sized chunks (fixed_size / sentence_aware / paragraph_aware)."},
    {"name": "estimate_tokens", "description": "Estimate the token count of a text (Spanish ~1.3 tokens/word heuristic)."},
    {"name": "lexical_search", "description": "Rank candidate texts against a query by accent-folded term overlap (zero-model, ES+EN stopwords)."},
    {"name": "semantic_search", "description": "Rank candidate texts by cosine over caller-supplied embedding vectors."},
    {"name": "cosine_similarity", "description": "Cosine similarity of two equal-length vectors (0..1; 0 for a zero vector)."},
    {"name": "search_documents", "description": "Semantic search over a PERSISTENT vector store: embeds the query and returns top-k stored chunks (needs FI_RAG_EMBEDDER + FI_RAG_STORE config)."},
]
