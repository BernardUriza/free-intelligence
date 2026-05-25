"""MCP tool contract for the STATEFUL RAG store server — zero-dep metadata.

Separate from :mod:`fi_core.rag.store_mcp_server` (which imports the MCP SDK +
storage backends) so the contract is importable WITHOUT those deps. fi-runner's
``rag_store`` capability reads this to build the ``mcp__<server>__<tool>``
allowlist, then spawns the server with ``python -m fi_core.rag.store_mcp_server``.
"""

from __future__ import annotations

MCP_SERVER_NAME = "fi-core-rag-store"

MCP_TOOLS: list[dict[str, str]] = [
    {"name": "ingest_document", "description": "Chunk + persist a document into a corpus (DocumentChunkStore). Re-ingesting the same doc_id replaces it."},
    {"name": "search_documents", "description": "Retrieve the top-k stored chunks for a query within a corpus (persistent vector search; lexical/zero-model by default)."},
    {"name": "list_documents", "description": "List the documents stored in a corpus (doc_id, chunk_count, status, attributes)."},
    {"name": "delete_document", "description": "Delete a document and all its chunks from a corpus (cascading)."},
    {"name": "delete_corpus", "description": "Delete every document (and chunks) in a corpus — tenant teardown / erase."},
    {"name": "stats", "description": "Usage for a corpus: {n_docs, n_chunks, bytes} — the metering base."},
]
