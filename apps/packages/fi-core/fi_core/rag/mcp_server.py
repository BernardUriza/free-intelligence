"""MCP server exposing the fi_core.rag primitives as agent tools.

A **thin wrapper** over the pure-Python core (`chunking` + `retrieval`) — exactly
like `fi_core.cognitive.mcp_server` wraps the cognitive primitives. Each tool just
calls the corresponding core function and returns a JSON-serializable dict; no
logic is duplicated here.

This is the agent-facing transport: a Claude-Agent-SDK / MCP runner registers it
as a stdio subprocess (`python -m fi_core.rag.mcp_server`) and calls
`mcp__fi-core-rag__lexical_search`, `__chunk_document`, etc. The same primitives
remain importable directly for synchronous, non-agent code.

Why these belong on an agent: the retrievers are zero-model AND zero-DB — they
rank texts the agent already holds (a small static corpus, a handful of candidate
snippets) without a vector store. `lexical_search` in particular beats an
English-centric embedder on short Spanish text, which is why both production bots
default to it. `semantic_search` ranks by cosine over vectors the caller already
has (this server never calls an embedder).

Requires the `mcp` extra::

    pip install 'fi-core[mcp]'
"""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "fi_core.rag.mcp_server requires the MCP SDK. "
        "Install via: pip install 'fi-core[mcp]'"
    ) from e

from fi_core.rag.chunking import (
    ChunkConfig,
    ChunkingStrategy,
)
from fi_core.rag.chunking import (
    chunk_document as _chunk_document,
)
from fi_core.rag.chunking import (
    estimate_tokens as _estimate_tokens,
)
from fi_core.rag.retrieval import (
    LexicalRetriever,
    SemanticRetriever,
)
from fi_core.rag.retrieval import (
    cosine_similarity as _cosine_similarity,
)

mcp = FastMCP(
    "fi-core-rag",
    instructions=(
        "Zero-model, zero-DB retrieval primitives for an agent. Split a document "
        "into chunks with `chunk_document`, size text with `estimate_tokens`, and "
        "RANK candidate texts the agent already holds: `lexical_search` (free, "
        "deterministic, accent-folded term overlap — best on short Spanish text) "
        "or `semantic_search` (cosine over embedding vectors you supply; this "
        "server never calls an embedder). `cosine_similarity` is the raw vector "
        "primitive. Recall over an in-context corpus, no vector store required."
    ),
)

_LEXICAL = LexicalRetriever()
_SEMANTIC = SemanticRetriever()


# ---------------------------------------------------------------------------
# Chunking (split a document into retrieval units)
# ---------------------------------------------------------------------------


@mcp.tool()
async def chunk_document(
    text: str,
    strategy: str = "paragraph_aware",
    chunk_size: int = 400,
    overlap: int = 50,
    min_chunk_size: int = 100,
) -> dict:
    """Split ``text`` into retrieval-sized chunks using a chunking strategy."""
    try:
        strat = ChunkingStrategy(strategy)
    except ValueError:
        return {
            "error": f"unknown strategy {strategy!r}",
            "valid_strategies": [s.value for s in ChunkingStrategy],
        }
    config = ChunkConfig(chunk_size=chunk_size, overlap=overlap, min_chunk_size=min_chunk_size)
    chunks = _chunk_document(text, strat, config)
    return {"strategy": strat.value, "count": len(chunks), "chunks": chunks}


# ---------------------------------------------------------------------------
# Token sizing
# ---------------------------------------------------------------------------


@mcp.tool()
async def estimate_tokens(text: str) -> dict:
    """Estimate the token count of ``text`` (Spanish ~1.3 tokens/word)."""
    return {"tokens": _estimate_tokens(text), "words": len(text.split())}


# ---------------------------------------------------------------------------
# Lexical retrieval (free, model-less — best on short Spanish text)
# ---------------------------------------------------------------------------


@mcp.tool()
async def lexical_search(
    query: str,
    texts: list[str],
    top_k: int = 2,
    min_score: float | None = None,
) -> dict:
    """Rank ``texts`` against ``query`` by accent-folded term overlap (0..1)."""
    hits = _LEXICAL.rank(query, list(texts or []), top_k=top_k, min_score=min_score)
    return {"hits": [{"text": h.text, "score": h.score} for h in hits]}


# ---------------------------------------------------------------------------
# Semantic retrieval (cosine over caller-supplied embeddings)
# ---------------------------------------------------------------------------


@mcp.tool()
async def semantic_search(
    query_vector: list[float],
    texts: list[str],
    text_vectors: list[list[float]],
    top_k: int = 2,
    min_score: float | None = None,
) -> dict:
    """Rank ``texts`` by cosine(query_vector, text_vectors[i]). Lengths must match."""
    texts = list(texts or [])
    text_vectors = list(text_vectors or [])
    if len(texts) != len(text_vectors):
        return {
            "error": "texts and text_vectors must have the same length",
            "n_texts": len(texts),
            "n_vectors": len(text_vectors),
        }
    hits = _SEMANTIC.rank(
        list(query_vector or []), texts, text_vectors, top_k=top_k, min_score=min_score
    )
    return {"hits": [{"text": h.text, "score": h.score} for h in hits]}


# ---------------------------------------------------------------------------
# Vector primitive
# ---------------------------------------------------------------------------


@mcp.tool()
async def cosine_similarity(a: list[float], b: list[float]) -> dict:
    """Cosine similarity of two equal-length vectors (0..1; 0 for a zero vector)."""
    a, b = list(a or []), list(b or [])
    if len(a) != len(b):
        return {"error": "vectors must have the same length", "len_a": len(a), "len_b": len(b)}
    return {"similarity": _cosine_similarity(a, b)}


# ---------------------------------------------------------------------------
# Tool contract (single source of truth in mcp_contract — zero-dep) + entry
# ---------------------------------------------------------------------------

from fi_core.rag.mcp_contract import (  # noqa: E402  (re-export)
    MCP_SERVER_NAME,
    MCP_TOOLS,
)

__all__ = ["MCP_SERVER_NAME", "MCP_TOOLS", "main", "mcp"]


def main() -> None:
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
