"""Value types passed between chunking, embedder, and store layers.

Frozen dataclasses — these are values, never mutated in place. Each layer
treats the previous layer's output as immutable input.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
