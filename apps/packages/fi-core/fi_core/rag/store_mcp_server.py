"""Stateful RAG MCP server — persist documents and query them later.

``mcp_server.py`` is STATELESS (ranks text the agent already holds). This one
PERSISTS: ``ingest_document`` chunks + embeds + stores a document; ``search_
documents`` retrieves from it; state survives restarts (HDF5 on disk by default).
Documents are namespaced by ``corpus_id`` for per-tenant isolation. So a thin
consumer (no fi-core import) can offer "upload your files, query them as RAG" via
``Runner(capabilities=["rag_store"])``.

This is the AGENT face of :class:`fi_core.rag.store_service.RagStore`; the
PROGRAMMATIC face is ``fi_runner.rag_store`` (a consumer-facing client). Both wrap
the same RagStore built the same way, so a doc ingested either way is searchable
the other way.

Zero-model by default (the dep-free :class:`~fi_core.embeddings.hashing.HashingEmbedder`).
Opt into semantics with ``FI_RAG_EMBEDDER=azure|sentence_transformers``. Env config
(read by the spawned subprocess):
  FI_RAG_BACKEND     hdf5 (default) | pgvector
  FI_RAG_STORE_PATH  HDF5 file path (default ./fi_rag_store.h5)         [hdf5]
  FI_RAG_PGVECTOR_DSN                                                   [pgvector]
  FI_RAG_EMBEDDER    hashing (default) | azure | sentence_transformers
  FI_RAG_EMBED_DIM   embedding dim (default 256)

Requires ``fi-core[mcp]``; the default hdf5 backend needs ``fi-core[stores-hdf5]``.
"""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "fi_core.rag.store_mcp_server requires the MCP SDK. Install via: pip install 'fi-core[mcp]'"
    ) from e

from fi_core.rag.chunking import ChunkingStrategy
from fi_core.rag.protocols import DocumentChunkStore, Embedder
from fi_core.rag.store_mcp_contract import MCP_SERVER_NAME, MCP_TOOLS
from fi_core.rag.store_service import RagStore, build_embedder_from_env, build_store_from_env

mcp = FastMCP(
    "fi-core-rag-store",
    instructions=(
        "Persistent document RAG. `ingest_document` chunks + stores a document in a "
        "corpus (state survives restarts); `search_documents` retrieves its chunks; "
        "`list_documents` / `delete_document` manage the corpus. Namespaced by "
        "corpus_id. Zero-model lexical retrieval by default."
    ),
)


# --- RagStore (lazy, env-built, injectable) ----------------------------------

_store: DocumentChunkStore | None = None  # injected override (else env)
_embedder: Embedder | None = None  # injected override (else env)
_rag: RagStore | None = None  # cached service


def set_store(store: DocumentChunkStore | None) -> None:
    """Inject the store (tests / in-process wiring). Resets the cached service."""
    global _store, _rag
    _store, _rag = store, None


def set_embedder(embedder: Embedder | None) -> None:
    """Inject the embedder (tests / in-process wiring). Resets the cached service."""
    global _embedder, _rag
    _embedder, _rag = embedder, None


def _reset() -> None:
    """Drop all cached state — also used by tests to simulate a restart."""
    global _store, _embedder, _rag
    _store = _embedder = _rag = None


def _get_rag() -> RagStore:
    global _rag
    if _rag is None:
        store = _store if _store is not None else build_store_from_env()
        embedder = _embedder if _embedder is not None else build_embedder_from_env()
        _rag = RagStore.from_components(store=store, embedder=embedder)
    return _rag


# --- tools (thin wrappers over RagStore) -------------------------------------


@mcp.tool()
async def ingest_document(
    corpus_id: str,
    doc_id: str,
    text: str,
    metadata: dict | None = None,
    strategy: str = "paragraph_aware",
    chunk_size: int = 400,
    overlap: int = 50,
    min_chunk_size: int = 100,
) -> dict:
    """Chunk ``text`` and PERSIST it under ``doc_id`` in ``corpus_id``. Re-ingesting
    an existing ``doc_id`` replaces its chunks. Returns the chunk count."""
    try:
        strat = ChunkingStrategy(strategy)
    except ValueError:
        return {"error": f"unknown strategy {strategy!r}", "valid_strategies": [s.value for s in ChunkingStrategy]}
    try:
        rag = _get_rag()
    except Exception as e:  # noqa: BLE001 - misconfig/missing-extra → graceful error
        return {"error": f"rag store not configured: {e}"}
    n = await rag.ingest(
        corpus_id, doc_id, text, metadata=metadata, strategy=strat,
        chunk_size=chunk_size, overlap=overlap, min_chunk_size=min_chunk_size,
    )
    return {"corpus_id": corpus_id, "doc_id": doc_id, "chunks": n}


@mcp.tool()
async def search_documents(corpus_id: str, query: str, top_k: int = 5, filters: dict | None = None) -> dict:
    """Retrieve the top-k stored chunks for ``query`` within ``corpus_id``."""
    try:
        rag = _get_rag()
    except Exception as e:  # noqa: BLE001
        return {"error": f"rag store not configured: {e}", "hits": []}
    hits = await rag.search(corpus_id, query, top_k=top_k, filters=filters)
    return {"hits": [{"text": h.chunk.text, "similarity": h.similarity, "doc_id": h.chunk.source_ref} for h in hits]}


@mcp.tool()
async def list_documents(corpus_id: str) -> dict:
    """List the documents stored in ``corpus_id``."""
    try:
        rag = _get_rag()
    except Exception as e:  # noqa: BLE001
        return {"error": f"rag store not configured: {e}", "documents": []}
    docs = await rag.list_documents(corpus_id)
    return {
        "documents": [
            {"doc_id": d.document_id, "chunk_count": d.chunk_count, "status": d.metadata.status, "attributes": d.metadata.attributes}
            for d in docs
        ]
    }


@mcp.tool()
async def delete_document(corpus_id: str, doc_id: str) -> dict:
    """Delete ``doc_id`` and all its chunks from ``corpus_id`` (cascading)."""
    try:
        rag = _get_rag()
    except Exception as e:  # noqa: BLE001
        return {"error": f"rag store not configured: {e}"}
    deleted = await rag.delete_document(corpus_id, doc_id)
    return {"corpus_id": corpus_id, "doc_id": doc_id, "deleted": deleted}


__all__ = ["MCP_SERVER_NAME", "MCP_TOOLS", "main", "mcp"]


def main() -> None:
    """Run the stateful store MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
