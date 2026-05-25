"""Stateful RAG MCP server — persist documents and query them later.

``mcp_server.py`` is STATELESS (ranks text the agent already holds). This one
PERSISTS: ``ingest_document`` chunks + embeds + stores a document in a
``DocumentChunkStore``; ``search_documents`` retrieves from it; the state survives
restarts (HDF5 on disk by default). Documents are namespaced by ``corpus_id`` for
per-tenant isolation. So a thin consumer (no fi-core import) can offer "upload
your files, query them as RAG" via ``Runner(capabilities=["rag_store"])``.

Zero-model by default: the default embedder is the dep-free
:class:`~fi_core.embeddings.hashing.HashingEmbedder` (lexical-ish cosine), so it
works with no model and no paid API. Opt into real semantics with
``FI_RAG_EMBEDDER=azure|sentence_transformers``.

Env config (read by the spawned subprocess):
  FI_RAG_BACKEND     hdf5 (default) | pgvector
  FI_RAG_STORE_PATH  HDF5 file path (default ./fi_rag_store.h5)         [hdf5]
  FI_RAG_PGVECTOR_DSN                                                   [pgvector]
  FI_RAG_EMBEDDER    hashing (default) | azure | sentence_transformers
  FI_RAG_EMBED_DIM   embedding dim (default 256; hashing buckets / pgvector dim)
  FI_RAG_AZURE_DEPLOYMENT + AZURE_OPENAI_*   [embedder=azure]
  FI_RAG_ST_MODEL                            [embedder=sentence_transformers]

Requires ``fi-core[mcp]``; the default hdf5 backend needs ``fi-core[stores-hdf5]``.
"""

from __future__ import annotations

import os

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "fi_core.rag.store_mcp_server requires the MCP SDK. Install via: pip install 'fi-core[mcp]'"
    ) from e

from fi_core.rag.chunking import ChunkConfig, ChunkingStrategy, chunk_document
from fi_core.rag.protocols import ChunkStore, Embedder
from fi_core.rag.store_mcp_contract import MCP_SERVER_NAME, MCP_TOOLS
from fi_core.rag.store_retrieval import StoreBackedRetriever
from fi_core.rag.types import Chunk, ChunkWithEmbedding, DocumentMetadata

mcp = FastMCP(
    "fi-core-rag-store",
    instructions=(
        "Persistent document RAG. `ingest_document` chunks + stores a document in a "
        "corpus (state survives restarts); `search_documents` retrieves its chunks; "
        "`list_documents` / `delete_document` manage the corpus. Namespaced by "
        "corpus_id. Zero-model lexical retrieval by default."
    ),
)


# --- store + embedder + retriever (lazy, env-built, injectable) --------------

_store: ChunkStore | None = None
_embedder: Embedder | None = None
_retriever: StoreBackedRetriever | None = None


def set_store(store: ChunkStore | None) -> None:
    """Inject the store (tests / in-process wiring). Resets the retriever."""
    global _store, _retriever
    _store, _retriever = store, None


def set_embedder(embedder: Embedder | None) -> None:
    """Inject the embedder (tests / in-process wiring). Resets the retriever."""
    global _embedder, _retriever
    _embedder, _retriever = embedder, None


def _reset() -> None:
    """Drop all cached state — also used by tests to simulate a restart."""
    global _store, _embedder, _retriever
    _store = _embedder = _retriever = None


def _build_store_from_env() -> ChunkStore:
    backend = os.getenv("FI_RAG_BACKEND", "hdf5").lower()
    if backend == "hdf5":
        from fi_core.stores.hdf5 import HDF5ChunkStore

        return HDF5ChunkStore(os.getenv("FI_RAG_STORE_PATH", "fi_rag_store.h5"))
    if backend == "pgvector":
        from fi_core.stores.pgvector import PgVectorChunkStore

        return PgVectorChunkStore(
            dsn=os.environ["FI_RAG_PGVECTOR_DSN"], embedding_dim=int(os.getenv("FI_RAG_EMBED_DIM", "256"))
        )
    raise RuntimeError(f"FI_RAG_BACKEND must be 'hdf5' or 'pgvector' (got {backend!r})")


def _build_embedder_from_env() -> Embedder:
    kind = os.getenv("FI_RAG_EMBEDDER", "hashing").lower()
    if kind == "hashing":
        from fi_core.embeddings.hashing import HashingEmbedder

        return HashingEmbedder(dim=int(os.getenv("FI_RAG_EMBED_DIM", "256")))
    if kind == "azure":
        from fi_core.embeddings.azure_openai import AzureOpenAIEmbedder

        return AzureOpenAIEmbedder(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            deployment=os.environ["FI_RAG_AZURE_DEPLOYMENT"],
            dim=int(os.getenv("FI_RAG_EMBED_DIM", "1536")),
        )
    if kind in ("sentence_transformers", "st"):
        from fi_core.embeddings.sentence_transformers import SentenceTransformersEmbedder

        return SentenceTransformersEmbedder(model_name=os.environ["FI_RAG_ST_MODEL"])
    raise RuntimeError(f"FI_RAG_EMBEDDER must be hashing|azure|sentence_transformers (got {kind!r})")


def _get_store() -> ChunkStore:
    global _store
    if _store is None:
        _store = _build_store_from_env()
    return _store


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = _build_embedder_from_env()
    return _embedder


def _get_retriever() -> StoreBackedRetriever:
    global _retriever
    if _retriever is None:
        _retriever = StoreBackedRetriever(embedder=_get_embedder(), store=_get_store())
    return _retriever


def _docstore():
    """The store as a DocumentChunkStore (document lifecycle). Raises a clear
    error if the configured store is chunk-only (no document API)."""
    store = _get_store()
    if not hasattr(store, "create_document"):
        raise RuntimeError("the configured store does not support documents (need a DocumentChunkStore)")
    return store


# --- tools -------------------------------------------------------------------


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
        store = _docstore()
        embedder = _get_embedder()
    except Exception as e:  # noqa: BLE001 - misconfig → graceful error, not a crash
        return {"error": f"rag store not configured: {e}"}

    md = DocumentMetadata(attributes=metadata or {})
    if await store.get_document(namespace=corpus_id, document_id=doc_id) is not None:
        await store.delete_chunks_by_document(namespace=corpus_id, document_id=doc_id)
        await store.update_document(namespace=corpus_id, document_id=doc_id, content=text, metadata=md)
    else:
        await store.create_document(namespace=corpus_id, document_id=doc_id, content=text, metadata=md)

    pieces = chunk_document(text, strat, ChunkConfig(chunk_size=chunk_size, overlap=overlap, min_chunk_size=min_chunk_size))
    chunks = []
    for piece in pieces:
        embedding = await embedder.embed(piece)
        chunks.append(ChunkWithEmbedding(Chunk(text=piece, source_type="document", source_ref=doc_id), embedding))
    n = await store.save_chunks(namespace=corpus_id, document_id=doc_id, chunks=chunks) if chunks else 0
    return {"corpus_id": corpus_id, "doc_id": doc_id, "chunks": n}


@mcp.tool()
async def search_documents(corpus_id: str, query: str, top_k: int = 5, filters: dict | None = None) -> dict:
    """Retrieve the top-k stored chunks for ``query`` within ``corpus_id``
    (persistent vector search; lexical/zero-model by default)."""
    try:
        retriever = _get_retriever()
    except Exception as e:  # noqa: BLE001
        return {"error": f"rag store not configured: {e}", "hits": []}
    hits = await retriever.retrieve(query, namespace=corpus_id, top_k=top_k, filters=filters)
    return {"hits": [{"text": h.chunk.text, "similarity": h.similarity, "doc_id": h.chunk.source_ref} for h in hits]}


@mcp.tool()
async def list_documents(corpus_id: str) -> dict:
    """List the documents stored in ``corpus_id``."""
    try:
        store = _docstore()
    except Exception as e:  # noqa: BLE001
        return {"error": f"rag store not configured: {e}", "documents": []}
    docs = await store.list_documents(namespace=corpus_id)
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
        store = _docstore()
    except Exception as e:  # noqa: BLE001
        return {"error": f"rag store not configured: {e}"}
    deleted = await store.delete_document(namespace=corpus_id, document_id=doc_id)
    return {"corpus_id": corpus_id, "doc_id": doc_id, "deleted": deleted}


__all__ = ["MCP_SERVER_NAME", "MCP_TOOLS", "main", "mcp"]


def main() -> None:
    """Run the stateful store MCP server over stdio."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
