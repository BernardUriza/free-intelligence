"""Document Domain Models.

Defines the core entities for the document management system.
Follows Clean Architecture - pure domain models with no external dependencies.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Card: Document Repository Implementation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DocumentOrigin(str, Enum):
    """Where the document came from."""

    ADMIN_UPLOAD = "admin_upload"  # Uploaded via admin dashboard
    API_UPLOAD = "api_upload"      # Uploaded via API
    EMAIL_IMPORT = "email_import"  # Imported from email attachment
    MIGRATION = "migration"        # Migrated from legacy system


class DocumentStatus(str, Enum):
    """Processing status of the document."""

    PENDING = "pending"       # Uploaded, not yet indexed
    INDEXING = "indexing"     # Currently being processed
    INDEXED = "indexed"       # Successfully indexed and searchable
    ERROR = "error"           # Failed to process
    ARCHIVED = "archived"     # Soft-deleted but kept for audit


class DocumentType(str, Enum):
    """Type of medical document."""

    CLINICAL_GUIDE = "clinical_guide"       # Treatment protocols, guidelines
    RESEARCH_PAPER = "research_paper"       # Published research
    POLICY_DOCUMENT = "policy_document"     # Hospital policies, procedures
    DRUG_INFORMATION = "drug_information"   # Medication guides
    DIAGNOSTIC_CRITERIA = "diagnostic_criteria"  # Disease diagnostic criteria
    OTHER = "other"


@dataclass
class DocumentMetadata:
    """Metadata associated with a document.

    Includes clinical context, processing info, and audit trail.
    """

    # Clinical context
    specialty: str | None = None
    language: str = "es"  # ISO 639-1 code
    keywords: list[str] = field(default_factory=list)
    document_type: DocumentType = DocumentType.OTHER

    # File metadata
    file_size_bytes: int = 0
    mime_type: str = "application/pdf"
    original_filename: str = ""

    # Processing metadata
    num_pages: int = 0
    num_chunks: int = 0
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Custom metadata (flexible for future extensions)
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """Core document entity.

    Represents a medical document uploaded to the knowledge base.
    Used for RAG (Retrieval-Augmented Generation) in clinical workflows.
    """

    # Identity (required fields first)
    doc_id: str  # Unique identifier (UUID v4)
    clinic_id: str  # Multi-tenancy: which clinic owns this document
    title: str
    content: str  # Full text content (extracted from PDF/DOCX)
    metadata: DocumentMetadata
    uploaded_by: str  # User ID (Auth0 subject)

    # Status (with defaults)
    status: DocumentStatus = DocumentStatus.PENDING
    origin: DocumentOrigin = DocumentOrigin.API_UPLOAD

    # Audit trail
    uploaded_at: datetime = field(default_factory=lambda: datetime.now())
    updated_at: datetime | None = None

    # Error tracking (if status == ERROR)
    error_message: str | None = None
    retry_count: int = 0

    def is_searchable(self) -> bool:
        """Check if document is ready for semantic search."""
        return self.status == DocumentStatus.INDEXED

    def mark_indexed(self, num_chunks: int) -> None:
        """Mark document as successfully indexed."""
        self.status = DocumentStatus.INDEXED
        self.metadata.num_chunks = num_chunks
        self.updated_at = datetime.now()
        self.error_message = None

    def mark_error(self, error: str) -> None:
        """Mark document as failed with error message."""
        self.status = DocumentStatus.ERROR
        self.error_message = error
        self.retry_count += 1
        self.updated_at = datetime.now()


@dataclass
class DocumentChunk:
    """A chunk of a document with its embedding.

    Large documents are split into chunks for better retrieval.
    Each chunk has its own embedding vector for semantic search.
    """

    # Identity (required fields first)
    chunk_id: str  # Unique identifier (UUID v4)
    doc_id: str    # Parent document ID
    clinic_id: str # Multi-tenancy: inherited from parent document
    text: str      # Chunk text (typically 200-500 tokens)

    # Content metadata (with defaults)
    page_num: int | None = None  # Which page this chunk came from
    chunk_index: int = 0         # Position in document (0-indexed)

    # Embedding
    embedding: list[float] | None = None  # Vector representation
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Metadata for ranking
    relevance_boost: float = 1.0  # Boost factor for search (e.g., 1.5 for title chunks)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "clinic_id": self.clinic_id,
            "text": self.text,
            "page_num": self.page_num,
            "chunk_index": self.chunk_index,
            "embedding": self.embedding,
            "embedding_model": self.embedding_model,
            "relevance_boost": self.relevance_boost,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentChunk:
        """Create from dictionary."""
        return cls(
            chunk_id=data["chunk_id"],
            doc_id=data["doc_id"],
            clinic_id=data["clinic_id"],
            text=data["text"],
            page_num=data.get("page_num"),
            chunk_index=data.get("chunk_index", 0),
            embedding=data.get("embedding"),
            embedding_model=data.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2"),
            relevance_boost=data.get("relevance_boost", 1.0),
        )


@dataclass
class SearchResult:
    """A single search result from semantic search."""

    # Required fields first
    doc_id: str
    title: str
    chunk_id: str
    chunk_text: str
    score: float  # Cosine similarity score (0-1, higher is better)

    # Optional fields with defaults
    page_num: int | None = None
    document_type: DocumentType = DocumentType.OTHER
    specialty: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "chunk_id": self.chunk_id,
            "chunk_text": self.chunk_text,
            "page_num": self.page_num,
            "score": self.score,
            "document_type": self.document_type.value,
            "specialty": self.specialty,
        }


__all__ = [
    "Document",
    "DocumentOrigin",
    "DocumentStatus",
    "DocumentType",
    "DocumentMetadata",
    "DocumentChunk",
    "SearchResult",
]
