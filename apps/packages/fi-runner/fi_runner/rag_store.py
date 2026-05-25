"""fi_runner.rag_store — programmatic client for the persistent RAG store.

A thin consumer (e.g. a FastAPI endpoint) can ingest files and query them as RAG
WITHOUT importing fi-core and without an LLM: import :class:`RagStoreClient` from
fi-runner, call ``ingest`` / ``search``. fi-runner depends on fi-core, so this
wraps fi-core's ``RagStore`` — the SAME store the ``rag_store`` MCP capability
serves (same backend/path), so a document ingested programmatically is searchable
by an agent and vice versa.

Boundary: the consumer imports ``fi_runner.rag_store``, NEVER ``fi_core``. Results
are plain dicts/strings — no fi-core types cross the boundary.

Config via the same ``FI_RAG_*`` env as the MCP server: ``FI_RAG_BACKEND`` (hdf5
default, persists on disk at ``FI_RAG_STORE_PATH``; or pgvector), ``FI_RAG_EMBEDDER``
(hashing default — zero-model; or azure / sentence_transformers).

Plain text in: ``ingest`` takes already-extracted text. ``txt`` / ``md`` are plain
text (use :func:`read_text_file`); extracting text from PDF/DOCX/HTML is the
caller's responsibility (out of scope — fi-runner adds no parsing dependency).

    from fi_runner.rag_store import RagStoreClient
    rag = RagStoreClient()                                  # reads FI_RAG_* env
    await rag.ingest("tenant-1", "notes.md", "... text ...")
    hits = await rag.search("tenant-1", "what did I write?")  # -> [{"text","similarity","doc_id"}]
"""

from __future__ import annotations

from pathlib import Path


def read_text_file(path: str | Path) -> str:
    """Read a UTF-8 text file (txt/md). PDF/DOCX/HTML extraction is the caller's job."""
    return Path(path).read_text(encoding="utf-8")


class RagStoreClient:
    """In-process client over fi-core's persistent RagStore, built from FI_RAG_* env.

    Construct ONCE (e.g. at app startup) and reuse — for HDF5 it loads the on-disk
    index at construction. All methods are async."""

    def __init__(self) -> None:
        from fi_core.rag import RagStore  # fi-runner depends on fi-core; consumer does not import it

        self._rag = RagStore.from_env()

    async def ingest(
        self,
        corpus_id: str,
        doc_id: str,
        text: str,
        *,
        metadata: dict | None = None,
        strategy: str = "paragraph_aware",
        chunk_size: int = 400,
        overlap: int = 50,
        min_chunk_size: int = 100,
    ) -> int:
        """Chunk + embed + persist ``text`` under ``doc_id`` in ``corpus_id``
        (a tenant). Re-ingesting an existing ``doc_id`` replaces it. Returns the
        chunk count."""
        return await self._rag.ingest(
            corpus_id, doc_id, text, metadata=metadata, strategy=strategy,
            chunk_size=chunk_size, overlap=overlap, min_chunk_size=min_chunk_size,
        )

    async def ingest_text_file(self, corpus_id: str, path: str | Path, *, doc_id: str | None = None, **kwargs) -> int:
        """Convenience: read a txt/md file and :meth:`ingest` it (``doc_id`` defaults
        to the filename)."""
        p = Path(path)
        return await self.ingest(corpus_id, doc_id or p.name, read_text_file(p), **kwargs)

    async def search(self, corpus_id: str, query: str, *, top_k: int = 5, filters: dict | None = None) -> list[dict]:
        """Top-k stored chunks for ``query`` in ``corpus_id`` as plain dicts
        ``{"text", "similarity", "doc_id"}``."""
        hits = await self._rag.search(corpus_id, query, top_k=top_k, filters=filters)
        return [{"text": h.chunk.text, "similarity": h.similarity, "doc_id": h.chunk.source_ref} for h in hits]

    async def list_documents(self, corpus_id: str) -> list[dict]:
        """Documents in ``corpus_id`` as plain dicts."""
        docs = await self._rag.list_documents(corpus_id)
        return [
            {"doc_id": d.document_id, "chunk_count": d.chunk_count, "status": d.metadata.status, "attributes": d.metadata.attributes}
            for d in docs
        ]

    async def delete_document(self, corpus_id: str, doc_id: str) -> bool:
        """Delete ``doc_id`` (and its chunks) from ``corpus_id``; True if it existed."""
        return await self._rag.delete_document(corpus_id, doc_id)


__all__ = ["RagStoreClient", "read_text_file"]
