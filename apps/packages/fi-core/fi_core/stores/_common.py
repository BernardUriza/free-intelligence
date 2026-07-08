"""Shared helpers for the concrete store implementations.

Pure-stdlib module (no optional backend deps) so every store can import
it regardless of which extras are installed. Home of the conventions the
stores must AGREE on — chunk-id derivation above all: HDF5 and pgvector
sat on byte-identical private copies of the same hash/sanitize logic,
and an id convention that drifts between backends silently breaks the
idempotency contract when a corpus migrates stores.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fi_core.rag.types import Chunk


def now() -> datetime:
    return datetime.now(timezone.utc)


def sanitize_ref(ref: str) -> str:
    """Make a source_ref/document_id safe for use inside a chunk_id."""
    return ref.replace("/", "_").replace(":", "_")


def chunk_text_hash(text: str) -> str:
    """8-hex-digit hash of the chunk text, the id's uniqueness suffix."""
    return format(abs(hash(text)) % (1 << 32), "08x")


def chunk_id_from(chunk: Chunk, *, document_id: str | None = None) -> str:
    """Deterministic chunk_id from (source_ref, text-hash-prefix).

    Idempotency contract: re-running an ingest with the same Chunk must
    produce the same chunk_id so the store's conflict check (HDF5
    ``create_group``, pgvector ``ON CONFLICT DO NOTHING``) short-circuits.

    ``document_id`` prefixes the id when the store scopes chunks by
    document primary key (pgvector) so the same chunk text under
    different documents in the same namespace still gets distinct keys;
    the HDF5 store namespaces by group path and omits it.
    """
    text_hash = chunk_text_hash(chunk.text)
    safe_source_ref = sanitize_ref(chunk.source_ref)
    if document_id is None:
        return f"{safe_source_ref}_{text_hash}"
    return f"{sanitize_ref(document_id)}__{safe_source_ref}_{text_hash}"
