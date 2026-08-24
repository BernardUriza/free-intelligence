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
from fi_core.rag.store_service import build_embedder_from_env, build_store_from_env
from fi_core.rag.retrieval import (
    LexicalRetriever,
    SemanticRetriever,
)
from fi_core.rag.retrieval import (
    cosine_similarity as _cosine_similarity,
)
from fi_core.rag.hybrid import HybridRetriever
from fi_core.rag.rerank import BgeReranker, Reranker
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
    Configured by the SAME env vars as every other consumer — ``FI_RAG_BACKEND``,
    ``FI_RAG_STORE_PATH``, ``FI_RAG_EMBEDDER``, ``FI_RAG_EMBED_DIM`` — because it
    now calls the same builders they do.

    It used to carry its own copy, reading ``FI_RAG_STORE`` and
    ``FI_RAG_HDF5_PATH``: names that appear NOWHERE else in the repo, not in
    `store_service`, not in fi-runner's capability, not in either deploy doc. So
    a correctly configured box left this server unconfigured, `search_documents`
    answered `{"error": "...not configured", "hits": []}`, and the agent reported
    "nothing found" — a retrieval failure wearing the face of an empty corpus.
    The copy had drifted twice over: no ``hashing`` branch at all, though hashing
    is the documented default everywhere else, and ``FI_RAG_EMBED_DIM`` defaulting
    to 1536 against `store_service`'s 256, so a corpus written at 256 would be
    read back through a 1536-dim store.

    One pair of builders, one set of names. That is the fix; the drift was the
    symptom of there being two.

    What did NOT change is the strictness: with nothing set this still refuses
    rather than defaulting to an hdf5 file in the working directory. Its sibling
    `store_mcp_server` does default, and that difference is deliberate — a
    STATEFUL store is asked to persist, a stateless retriever silently writing a
    file nobody named is a surprise. A test pinned that behaviour and it is not
    this change's business to overrule it; the bug was the NAMES.
    """
    if not (os.getenv("FI_RAG_BACKEND") or os.getenv("FI_RAG_EMBEDDER")):
        raise RuntimeError(
            "retrieval not configured: set FI_RAG_BACKEND (hdf5|pgvector) and "
            "FI_RAG_EMBEDDER (hashing|azure|sentence_transformers)"
        )
    return StoreBackedRetriever(
        embedder=build_embedder_from_env(),
        store=build_store_from_env(),
    )


def _get_retriever() -> StoreBackedRetriever:
    """Return the injected retriever, else build + cache one from env."""
    global _retriever
    if _retriever is None:
        _retriever = _build_retriever_from_env()
    return _retriever


# --- reranker (cross-encoder) ----------------------------------------------
#
# The `rerank` tool reorders candidates the agent already holds (no store/embed),
# so it just needs a model. Lazy + cached (the model is ~600MB). FI_RAG_RERANKER_
# MODEL overrides the default; injectable via set_reranker for tests/in-process.

_reranker: Reranker | None = None


def set_reranker(reranker: Reranker | None) -> None:
    """Inject the reranker (in-process wiring / tests)."""
    global _reranker
    _reranker = reranker


def _get_reranker() -> Reranker:
    global _reranker
    if _reranker is None:
        _reranker = BgeReranker(model_name=os.getenv("FI_RAG_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"))
    return _reranker


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
    filters: dict | None = None,
) -> dict:
    """Semantic search over a PERSISTENT vector store: embeds ``query`` and returns
    the top-k stored chunks in ``namespace``. Unlike ``semantic_search`` (which
    ranks vectors you supply), this owns the embed + store query. ``filters``
    restricts to chunks whose parent document's attributes contain the given pairs
    (e.g. ``{"clinic_id": "c1"}``). Requires the server to be configured
    (FI_RAG_EMBEDDER + FI_RAG_BACKEND env, or an injected retriever); ``error`` if not."""
    try:
        retriever = _get_retriever()
    except Exception as e:  # noqa: BLE001 - unconfigured/missing-extra → graceful error, not a crash
        return {"error": f"store-backed RAG not configured: {e}", "hits": []}
    hits = await retriever.retrieve(
        query, namespace=namespace, top_k=top_k, min_similarity=min_similarity or None, filters=filters
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
    filters: dict | None = None,
) -> dict:
    """Hybrid search over the PERSISTENT store: dense vector recall + lexical
    (accent-folded, Spanish-tuned) re-ranking fused by Reciprocal Rank Fusion.
    Catches exact-keyword / proper-noun matches that pure semantic under-weights.
    Over-fetches ``candidate_k`` dense candidates, fuses, returns ``top_k``.
    ``filters`` restricts by parent-document attribute containment. Needs the same
    config as ``search_documents``; returns an ``error`` when unconfigured."""
    try:
        retriever = _get_retriever()
    except Exception as e:  # noqa: BLE001 - unconfigured/missing-extra → graceful error
        return {"error": f"store-backed RAG not configured: {e}", "hits": []}
    hybrid = HybridRetriever(dense=retriever, candidate_k=candidate_k)
    hits = await hybrid.retrieve(query, namespace=namespace, top_k=top_k, candidate_k=candidate_k, filters=filters)
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
async def rerank(query: str, documents: list[str], top_k: int = 5) -> dict:
    """Rerank candidate texts the agent already holds with a cross-encoder (reads
    query+doc together → far more calibrated than bi-encoder cosine). Returns the
    top_k texts best-first with scores. Needs ``fi-core[rerank]`` (loads a ~600MB
    model on first use); returns an ``error`` when the model isn't available."""
    docs = list(documents or [])
    if not docs:
        return {"hits": []}
    try:
        results = await _get_reranker().rerank(query, docs)
    except Exception as e:  # noqa: BLE001 - model/extra missing → graceful error
        return {"error": f"reranker not available: {e}", "hits": []}
    return {"hits": [{"text": docs[r.index], "score": r.score} for r in results[:top_k]]}


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
