"""Knowledge Base API schemas.

Pydantic models for request/response serialization.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor)
"""

from __future__ import annotations

from backend.domain.document.models import DocumentType
from pydantic import BaseModel, Field


# =============================================================================
# Document Responses
# =============================================================================


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""

    doc_id: str = Field(..., description="Unique document ID")
    title: str = Field(..., description="Document title")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Human-readable message")


class DocumentResponse(BaseModel):
    """Document metadata response."""

    doc_id: str
    clinic_id: str
    title: str
    status: str
    origin: str
    uploaded_by: str
    uploaded_at: str
    updated_at: str | None = None
    num_chunks: int = 0
    file_size_bytes: int = 0
    specialty: str | None = None
    document_type: str = "other"
    error_message: str | None = None


class DocumentDetailResponse(DocumentResponse):
    """Document with full content."""

    content: str | None = None


class DocumentListResponse(BaseModel):
    """Paginated document list response."""

    documents: list[DocumentResponse]
    total: int
    page: int
    limit: int


# =============================================================================
# Document Requests
# =============================================================================


class DocumentUpdateRequest(BaseModel):
    """Request to update document metadata."""

    title: str | None = None
    specialty: str | None = None
    document_type: DocumentType | None = None
    keywords: list[str] | None = None


# =============================================================================
# Search
# =============================================================================


class SearchRequest(BaseModel):
    """Semantic search request."""

    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)
    document_type: DocumentType | None = None


class SearchResultResponse(BaseModel):
    """Single search result."""

    doc_id: str
    title: str
    chunk_text: str
    score: float
    page_num: int | None = None
    document_type: str = "other"
    specialty: str | None = None


class SearchResponse(BaseModel):
    """Search results response."""

    query: str
    results: list[SearchResultResponse]
    total: int
