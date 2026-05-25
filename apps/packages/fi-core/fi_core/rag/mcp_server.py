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

import os

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
from fi_core.rag.hybrid import HybridRetriever
from fi_core.rag.store_retrieval import StoreBackedRetriever

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

# --- store-backed (persistent) retriever -----------------------------------
#
# `search_documents` needs a CONFIGURED embedder + vector store (unlike the
# zero-DB tools above). In the stdio-subprocess model the only way to configure
# a spawned server is the environment, so it is built lazily from env vars and
# cached. A deploy that builds its own retriever in-process can inject it with
# `set_retriever(...)` (also the test seam). Unconfigured → the tool returns a
# clear error dict instead of failing the whole server.

_retriever: StoreBackedRetriever | None = None


def set_retriever(retriever: StoreBackedRetriever | None) -> None:
    """Inject the store-backed retriever (deploy in-process wiring / tests)."""
    global _retriever
    _retriever = retriever


def _build_retriever_from_env() -> StoreBackedRetriever:
    """Build a StoreBackedRetriever from env. Raises RuntimeError (with what's
    missing) when unconfigured, or ImportError if the chosen extra isn't installed.

    Embedder (FI_RAG_EMBEDDER):
      - ``azure``: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
        FI_RAG_AZURE_DEPLOYMENT, FI_RAG_EMBED_DIM (default 1536)
      - ``sentence_transformers``: FI_RAG_ST_MODEL
    Store (FI_RAG_STORE):
      - ``pgvector``: FI_RAG_PGVECTOR_DSN, FI_RAG_EMBED_DIM (default 1536)
      - ``hdf5``: FI_RAG_HDF5_PATH
    """
    embedder_kind = os.getenv("FI_RAG_EMBEDDER", "").lower()
    dim = int(os.getenv("FI_RAG_EMBED_DIM", "1536"))
    if embedder_kind == "azure":
        from fi_core.embeddings.azure_openai import AzureOpenAIEmbedder

        embedder = AzureOpenAIEmbedder(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            deployment=os.environ["FI_RAG_AZURE_DEPLOYMENT"],
            dim=dim,
        )
    elif embedder_kind in ("sentence_transformers", "st"):
        from fi_core.embeddings.sentence_transformers import SentenceTransformersEmbedder

        embedder = SentenceTransformersEmbedder(model_name=os.environ["FI_RAG_ST_MODEL"])
    else:
        raise RuntimeError("set FI_RAG_EMBEDDER to 'azure' or 'sentence_transformers'")

    store_kind = os.getenv("FI_RAG_STORE", "").lower()
    if store_kind == "pgvector":
        from fi_core.stores.pgvector import PgVectorChunkStore

        store = PgVectorChunkStore(dsn=os.environ["FI_RAG_PGVECTOR_DSN"], embedding_dim=dim)
    elif store_kind == "hdf5":
        from fi_core.stores.hdf5 import HDF5ChunkStore

        store = HDF5ChunkStore(file_path=os.environ["FI_RAG_HDF5_PATH"])
    else:
        raise RuntimeError("set FI_RAG_STORE to 'pgvector' or 'hdf5'")

    return StoreBackedRetriever(embedder=embedder, store=store)


def _get_retriever() -> StoreBackedRetriever:
    """Return the injected retriever, else build + cache one from env."""
    global _retriever
    if _retriever is None:
        _retriever = _build_retriever_from_env()
    return _retriever


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
# Persistent document RAG (embed query -> vector store -> chunks)
# ---------------------------------------------------------------------------


@mcp.tool()
async def search_documents(
    query: str,
    namespace: str,
    top_k: int = 5,
    min_similarity: float = 0.0,
) -> dict:
    """Semantic search over a PERSISTENT vector store: embeds ``query`` and returns
    the top-k stored chunks in ``namespace``. Unlike ``semantic_search`` (which
    ranks vectors you supply), this owns the embed + store query. Requires the
    server to be configured (FI_RAG_EMBEDDER + FI_RAG_STORE env, or an injected
    retriever); returns an ``error`` when not."""
    try:
        retriever = _get_retriever()
    except Exception as e:  # noqa: BLE001 - unconfigured/missing-extra → graceful error, not a crash
        return {"error": f"store-backed RAG not configured: {e}", "hits": []}
    hits = await retriever.retrieve(
        query, namespace=namespace, top_k=top_k, min_similarity=min_similarity or None
    )
    return {
        "hits": [
            {
                "text": h.chunk.text,
                "similarity": h.similarity,
                "source_type": h.chunk.source_type,
                "source_ref": h.chunk.source_ref,
            }
            for h in hits
        ]
    }


@mcp.tool()
async def hybrid_search(
    query: str,
    namespace: str,
    top_k: int = 5,
    candidate_k: int = 50,
) -> dict:
    """Hybrid search over the PERSISTENT store: dense vector recall + lexical
    (accent-folded, Spanish-tuned) re-ranking fused by Reciprocal Rank Fusion.
    Catches exact-keyword / proper-noun matches that pure semantic under-weights.
    Over-fetches ``candidate_k`` dense candidates, fuses, returns ``top_k``. Needs
    the same config as ``search_documents``; returns an ``error`` when unconfigured."""
    try:
        retriever = _get_retriever()
    except Exception as e:  # noqa: BLE001 - unconfigured/missing-extra → graceful error
        return {"error": f"store-backed RAG not configured: {e}", "hits": []}
    hybrid = HybridRetriever(dense=retriever, candidate_k=candidate_k)
    hits = await hybrid.retrieve(query, namespace=namespace, top_k=top_k, candidate_k=candidate_k)
    return {
        "hits": [
            {
                "text": h.chunk.text,
                "similarity": h.similarity,
                "source_type": h.chunk.source_type,
                "source_ref": h.chunk.source_ref,
            }
            for h in hits
        ]
    }


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
