"""Value types passed between chunking, embedder, and store layers.

Frozen dataclasses — these are values, never mutated in place. Each layer
treats the previous layer's output as immutable input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Chunk:
    """A chunked piece of source text + the metadata needed to retrieve it.

    Fields are deliberately minimal — embedder/store implementations
    can attach additional metadata via their own composition, not by
    extending this type.

    `text` is the chunk content (post-chunking, ready to embed).
    `source_type` categorizes provenance ("message", "disclosure",
    "document", "manual", etc. — the consumer's vocabulary).
    `source_ref` is the address inside that source — channel id +
    message id, document filename, anything that lets a caller
    trace a recalled chunk back to its origin.
    `created_at` is when the chunk was ingested, not when the source
    was created — useful for "what's new this week" queries.
    """

    text: str
    source_type: str
    source_ref: str
    created_at: datetime | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned from a similarity query, with its score.

    `similarity` is in [0.0, 1.0] where 1.0 means identical to the query.
    Implementations using cosine distance should expose it as
    `1 - distance` so this contract holds across stores.
    """

    chunk: Chunk
    similarity: float


@dataclass(frozen=True)
class ChunkWithEmbedding:
    """A chunk paired with its pre-computed embedding vector.

    Returned by callers that batch-compute embeddings before calling
    ``DocumentChunkStore.save_chunks`` — separating the embedder pass
    from the persistence pass lets implementations parallelize each
    stage independently.
    """

    chunk: Chunk
    embedding: list[float]


@dataclass(frozen=True)
class DocumentMetadata:
    """Lifecycle + free-form attributes for a chunked document.

    fi-core never reads ``attributes`` — it is a free-form bag for
    consumers to attach their own domain-specific fields (clinic_id,
    encounter_id, source_url, document_type, origin, etc.) without
    polluting the type system. The store persists ``attributes`` as
    opaque metadata and returns it intact on read.

    ``status`` is consumer-defined. Common values are "pending",
    "indexed", "failed", "deleted" — but fi-core does not enforce.
    The Protocol's ``list_documents(status=...)`` filter accepts any
    string, so consumers can use their own state machine.

    ``created_at`` is when the document record was first written to
    the store. ``indexed_at`` is when its chunks were embedded and
    saved — ``None`` until indexing completes.
    """

    status: str = "pending"
    created_at: datetime | None = None
    indexed_at: datetime | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentRecord:
    """A document record returned by ``get_document`` / ``list_documents``.

    Wraps the persisted document content + its metadata + the count of
    chunks currently saved under it. Implementations populate
    ``chunk_count`` from the underlying store on each read — if your
    use case demands paginated chunk retrieval, call
    ``get_chunks_by_document`` separately rather than expanding this
    type to carry chunks inline.
    """

    document_id: str
    namespace: str
    content: str
    metadata: DocumentMetadata
    chunk_count: int = 0
