"""RagStore — the persistent RAG store as a plain async service object.

The orchestration behind the stateful store MCP server, factored out so it has
TWO faces over the SAME building blocks (chunking + StoreBackedRetriever +
DocumentChunkStore lifecycle):
  - the agent face: ``fi_core.rag.store_mcp_server`` (MCP tools), and
  - the programmatic face: a thin client in fi-runner (``fi_runner.rag_store``)
    a consumer uses WITHOUT importing fi-core.

Both build the store the same way (``RagStore.from_env``), so a document ingested
programmatically is searchable by the agent and vice versa (same backend / path).

Documents are namespaced by ``corpus_id`` (per-tenant isolation). The default
backend is HDF5 on disk (persists across restarts); the default embedder is the
zero-model :class:`~fi_core.embeddings.hashing.HashingEmbedder`. Configure via env
— see :func:`build_store_from_env` / :func:`build_embedder_from_env`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fi_core.rag.chunking import ChunkConfig, ChunkingStrategy, chunk_document
from fi_core.rag.protocols import DocumentChunkStore, Embedder
from fi_core.rag.store_retrieval import StoreBackedRetriever
from fi_core.rag.types import Chunk, ChunkWithEmbedding, DocumentMetadata, DocumentRecord, RetrievedChunk


def build_store_from_env() -> DocumentChunkStore:
    """Build the configured store. ``FI_RAG_BACKEND`` = hdf5 (default) | pgvector;
    ``FI_RAG_STORE_PATH`` for hdf5; ``FI_RAG_PGVECTOR_DSN`` + ``FI_RAG_EMBED_DIM``
    for pgvector. Raises a clear error if the backend extra isn't installed."""
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


def build_embedder_from_env() -> Embedder:
    """Build the configured embedder. ``FI_RAG_EMBEDDER`` = hashing (default,
    zero-model) | azure | sentence_transformers. Semantic embedders are opt-in
    (they need a model / paid API + the matching extra)."""
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


@dataclass
class RagStore:
    """Persistent RAG over a DocumentChunkStore + an Embedder, keyed by corpus_id."""

    store: DocumentChunkStore
    embedder: Embedder
    retriever: StoreBackedRetriever

    @classmethod
    def from_components(cls, *, store: DocumentChunkStore, embedder: Embedder) -> RagStore:
        """Build a RagStore from a store + embedder (wires the retriever)."""
        return cls(store=store, embedder=embedder, retriever=StoreBackedRetriever(embedder=embedder, store=store))

    @classmethod
    def from_env(cls) -> RagStore:
        """Build a RagStore from the FI_RAG_* environment."""
        return cls.from_components(store=build_store_from_env(), embedder=build_embedder_from_env())

    async def ingest(
        self,
        corpus_id: str,
        doc_id: str,
        text: str,
        *,
        metadata: dict | None = None,
        strategy: ChunkingStrategy | str = ChunkingStrategy.PARAGRAPH_AWARE,
        chunk_size: int = 400,
        overlap: int = 50,
        min_chunk_size: int = 100,
    ) -> int:
        """Chunk + embed + persist ``text`` under ``doc_id`` in ``corpus_id``.
        Re-ingesting an existing ``doc_id`` REPLACES its chunks. Returns the count."""
        strat = ChunkingStrategy(strategy) if isinstance(strategy, str) else strategy
        md = DocumentMetadata(attributes=metadata or {})
        if await self.store.get_document(namespace=corpus_id, document_id=doc_id) is not None:
            await self.store.delete_chunks_by_document(namespace=corpus_id, document_id=doc_id)
            await self.store.update_document(namespace=corpus_id, document_id=doc_id, content=text, metadata=md)
        else:
            await self.store.create_document(namespace=corpus_id, document_id=doc_id, content=text, metadata=md)
        pieces = chunk_document(text, strat, ChunkConfig(chunk_size=chunk_size, overlap=overlap, min_chunk_size=min_chunk_size))
        chunks: list[ChunkWithEmbedding] = []
        for piece in pieces:
            embedding = await self.embedder.embed(piece)
            chunks.append(ChunkWithEmbedding(Chunk(text=piece, source_type="document", source_ref=doc_id), embedding))
        return await self.store.save_chunks(namespace=corpus_id, document_id=doc_id, chunks=chunks) if chunks else 0

    async def search(
        self, corpus_id: str, query: str, *, top_k: int = 5, filters: dict | None = None
    ) -> list[RetrievedChunk]:
        """Retrieve the top-k stored chunks for ``query`` within ``corpus_id``."""
        return await self.retriever.retrieve(query, namespace=corpus_id, top_k=top_k, filters=filters)

    async def list_documents(self, corpus_id: str) -> list[DocumentRecord]:
        """The documents stored in ``corpus_id``."""
        return await self.store.list_documents(namespace=corpus_id)

    async def delete_document(self, corpus_id: str, doc_id: str) -> bool:
        """Delete ``doc_id`` (and its chunks) from ``corpus_id``; True if it existed."""
        return await self.store.delete_document(namespace=corpus_id, document_id=doc_id)

    async def delete_corpus(self, corpus_id: str) -> int:
        """Delete EVERY document (and its chunks) in ``corpus_id``. Returns the
        number of documents deleted — the tenant-teardown / GDPR-erase op."""
        deleted = 0
        for doc in await self.store.list_documents(namespace=corpus_id):
            if await self.store.delete_document(namespace=corpus_id, document_id=doc.document_id):
                deleted += 1
        return deleted

    async def stats(self, corpus_id: str) -> dict:
        """Usage for ``corpus_id``: ``{n_docs, n_chunks, bytes}``. ``bytes`` is the
        UTF-8 size of the stored chunk text (the embedded/stored unit) — a
        backend-agnostic, billable measure (the P2 metering base)."""
        docs = await self.store.list_documents(namespace=corpus_id)
        n_chunks = 0
        nbytes = 0
        for doc in docs:
            for chunk in await self.store.get_chunks_by_document(namespace=corpus_id, document_id=doc.document_id):
                n_chunks += 1
                nbytes += len(chunk.text.encode("utf-8"))
        return {"n_docs": len(docs), "n_chunks": n_chunks, "bytes": nbytes}


__all__ = ["RagStore", "build_embedder_from_env", "build_store_from_env"]
