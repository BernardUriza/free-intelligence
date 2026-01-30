"""Document Repository Interface.

Defines the contract for document storage and retrieval.
Implementations can use HDF5, PostgreSQL, S3, or any other backend.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Card: Document Repository Implementation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO

from backend.services.document.domain.models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    SearchResult,
)


class IDocumentRepository(ABC):
    """Repository for document storage and retrieval.

    Responsibilities:
    - Store and retrieve documents (metadata + content)
    - Store and retrieve document chunks (for RAG)
    - Semantic search across documents (with clinic_id filtering)
    - Document lifecycle management (create, update, delete, archive)

    Security:
    - ALL methods that accept clinic_id MUST filter by it (no cross-clinic access)
    - Semantic search MUST respect clinic_id boundary

    Clean Architecture Benefits:
    - Decouples business logic from storage implementation
    - Allows swapping storage backends (HDF5 → PostgreSQL) without changing services
    - Enables testing with in-memory implementation
    """

    # =============================================================================
    # DOCUMENT CRUD
    # =============================================================================

    @abstractmethod
    def create_document(
        self,
        doc: Document,
        file_content: bytes | None = None
    ) -> Document:
        """Create a new document.

        Args:
            doc: Document entity with metadata
            file_content: Optional binary content of the file (PDF, DOCX, etc.)

        Returns:
            Created document with generated doc_id

        Raises:
            ValueError: If clinic_id is empty or invalid
            StorageError: If storage operation fails
        """
        ...

    @abstractmethod
    def get_document(
        self,
        doc_id: str,
        clinic_id: str
    ) -> Document | None:
        """Get a document by ID (with clinic_id filter).

        Args:
            doc_id: Document ID
            clinic_id: Clinic ID (security boundary)

        Returns:
            Document if found and belongs to clinic, None otherwise

        Security:
            MUST filter by clinic_id - prevent cross-clinic access
        """
        ...

    @abstractmethod
    def list_documents(
        self,
        clinic_id: str,
        status: DocumentStatus | None = None,
        skip: int = 0,
        limit: int = 50
    ) -> list[Document]:
        """List documents for a clinic.

        Args:
            clinic_id: Clinic ID (security boundary)
            status: Optional filter by status
            skip: Pagination offset
            limit: Max results to return

        Returns:
            List of documents (empty if none found)

        Security:
            MUST filter by clinic_id - prevent cross-clinic access
        """
        ...

    @abstractmethod
    def update_document(
        self,
        doc_id: str,
        clinic_id: str,
        updates: dict
    ) -> Document | None:
        """Update document metadata.

        Args:
            doc_id: Document ID
            clinic_id: Clinic ID (security boundary)
            updates: Fields to update (e.g., {"title": "New Title"})

        Returns:
            Updated document if found and belongs to clinic, None otherwise

        Security:
            MUST filter by clinic_id - prevent cross-clinic access
        """
        ...

    @abstractmethod
    def delete_document(
        self,
        doc_id: str,
        clinic_id: str,
        soft_delete: bool = True
    ) -> bool:
        """Delete a document.

        Args:
            doc_id: Document ID
            clinic_id: Clinic ID (security boundary)
            soft_delete: If True, mark as ARCHIVED; if False, hard delete

        Returns:
            True if deleted, False if not found or wrong clinic

        Security:
            MUST filter by clinic_id - prevent cross-clinic access
        """
        ...

    @abstractmethod
    def get_document_count(
        self,
        clinic_id: str,
        status: DocumentStatus | None = None
    ) -> int:
        """Count documents for a clinic.

        Args:
            clinic_id: Clinic ID (security boundary)
            status: Optional filter by status

        Returns:
            Number of documents

        Security:
            MUST filter by clinic_id - prevent cross-clinic access
        """
        ...

    # =============================================================================
    # DOCUMENT CHUNKS (for RAG)
    # =============================================================================

    @abstractmethod
    def save_chunks(
        self,
        doc_id: str,
        clinic_id: str,
        chunks: list[DocumentChunk]
    ) -> int:
        """Save chunks for a document.

        Args:
            doc_id: Parent document ID
            clinic_id: Clinic ID (security boundary)
            chunks: List of document chunks with embeddings

        Returns:
            Number of chunks saved

        Security:
            MUST verify doc_id belongs to clinic_id before saving
        """
        ...

    @abstractmethod
    def get_chunks(
        self,
        doc_id: str,
        clinic_id: str
    ) -> list[DocumentChunk]:
        """Get all chunks for a document.

        Args:
            doc_id: Document ID
            clinic_id: Clinic ID (security boundary)

        Returns:
            List of chunks (empty if document not found or wrong clinic)

        Security:
            MUST filter by clinic_id - prevent cross-clinic access
        """
        ...

    @abstractmethod
    def delete_chunks(
        self,
        doc_id: str,
        clinic_id: str
    ) -> int:
        """Delete all chunks for a document.

        Args:
            doc_id: Document ID
            clinic_id: Clinic ID (security boundary)

        Returns:
            Number of chunks deleted

        Security:
            MUST filter by clinic_id - prevent cross-clinic access
        """
        ...

    # =============================================================================
    # SEMANTIC SEARCH (Vector Search)
    # =============================================================================

    @abstractmethod
    def search_by_embedding(
        self,
        query_embedding: list[float],
        clinic_id: str,
        limit: int = 10,
        min_score: float = 0.5,
        document_type: str | None = None
    ) -> list[SearchResult]:
        """Semantic search using query embedding.

        Args:
            query_embedding: Query vector (same dimensions as chunk embeddings)
            clinic_id: Clinic ID (security boundary)
            limit: Max results to return
            min_score: Minimum cosine similarity score (0-1)
            document_type: Optional filter by document type

        Returns:
            List of search results, sorted by score (highest first)

        Security:
            MUST filter by clinic_id - prevent cross-clinic leakage
            This is CRITICAL - search results from other clinics = data breach
        """
        ...

    # =============================================================================
    # BULK OPERATIONS
    # =============================================================================

    @abstractmethod
    def reindex_document(
        self,
        doc_id: str,
        clinic_id: str
    ) -> bool:
        """Mark document for re-indexing.

        Useful when:
        - Embedding model changes
        - Document content updated
        - Chunking strategy changes

        Args:
            doc_id: Document ID
            clinic_id: Clinic ID (security boundary)

        Returns:
            True if marked for reindex, False if not found

        Security:
            MUST filter by clinic_id - prevent cross-clinic access
        """
        ...

    @abstractmethod
    def get_pending_documents(
        self,
        clinic_id: str | None = None,
        limit: int = 100
    ) -> list[Document]:
        """Get documents pending indexing.

        Used by background workers to process uploaded documents.

        Args:
            clinic_id: Optional clinic filter (None = all clinics, for SUPERADMIN)
            limit: Max results to return

        Returns:
            List of documents with status=PENDING or status=INDEXING (stale)
        """
        ...


__all__ = ["IDocumentRepository"]
