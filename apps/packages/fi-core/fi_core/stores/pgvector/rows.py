"""Row → domain-type mapping for the pgvector store."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from fi_core.rag.types import DocumentMetadata, DocumentRecord

if TYPE_CHECKING:
    import asyncpg


def row_to_document_record(row: "asyncpg.Record") -> DocumentRecord:
    """Reconstruct a DocumentRecord from an asyncpg Record row.

    ``attributes`` arrives as JSONB — usually already a dict, but a str
    when the connection lacks the JSONB codec; both decode to the same
    dict, and anything unparseable degrades to ``{}`` rather than raising.
    """
    raw_attrs = row["attributes"]
    if isinstance(raw_attrs, str):
        try:
            attributes = json.loads(raw_attrs)
        except (ValueError, TypeError):
            attributes = {}
    elif isinstance(raw_attrs, dict):
        attributes = raw_attrs
    else:
        attributes = {}
    return DocumentRecord(
        document_id=row["document_id"],
        namespace=row["namespace"],
        content=row["content"],
        metadata=DocumentMetadata(
            status=row["status"],
            created_at=row["created_at"],
            indexed_at=row["indexed_at"],
            attributes=attributes,
        ),
        chunk_count=int(row["chunk_count"] or 0),
    )
