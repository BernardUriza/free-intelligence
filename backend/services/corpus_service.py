"""Service layer for corpus operations.

Implements business logic for corpus management including:
- Document creation and retrieval
- Chunk management for diarization results
- Metadata enrichment and validation

Clean Code: This service layer makes endpoints simple and focused.
"""

from __future__ import annotations

from typing import Any, Optional

from backend.logger import get_logger
from backend.repositories import CorpusRepository
from backend.type_defs import DiarizationChunkDict

logger = get_logger(__name__)


class CorpusService:
    """Service for corpus document management.

    Orchestrates corpus operations through repository pattern.
    Handles:
    - Validation of input data
    - Business rule enforcement
    - Cross-cutting concerns (logging, error handling)
    """

    def __init__(self, repository: CorpusRepository) -> None:
        """Initialize service with repository dependency.

        Args:
            repository: CorpusRepository instance for data access
        """
        self.repository = repository

    def create_document(
        self,
        document_id: str,
        content: str,
        source: Optional[str] = None,
        tags: list[str | None] | None = None,
    ) -> dict[str, Any]:
        """Create new corpus document with validation.

        Args:
            document_id: Unique identifier for document
            content: Document text content
            source: Source/origin of document
            tags: Classification tags

        Returns:
            Created document metadata

        Raises:
            ValueError: If document data is invalid
            IOError: If storage operation fails
        """
        # Input validation
        if not document_id or len(document_id) < 3:
            raise ValueError("document_id must be at least 3 characters")

        if not content or len(content.strip()) == 0:
            raise ValueError("content cannot be empty")

        if len(content) > 10_000_000:  # 10MB limit
            raise ValueError("content exceeds maximum size (10MB)")

        # Prepare metadata
        metadata = {
            "source": source or "unknown",
            "tags": tags or [],
            "content_length": len(content),
        }

        try:
            # Delegate to repository
            doc_id = self.repository.create(
                document_id=document_id,
                content=content,
                metadata=metadata,
            )

            logger.info(
                "DOCUMENT_CREATED",
                document_id=doc_id,
                content_length=len(content),
            )

            return {
                "document_id": doc_id,
                "status": "created",
                "metadata": metadata,
            }

        except ValueError as e:
            logger.warning("DOCUMENT_CREATION_VALIDATION_FAILED", error=str(e))  # type: ignore[call-arg]
            raise
        except OSError as e:
            logger.error("DOCUMENT_CREATION_FAILED", error=str(e))  # type: ignore[call-arg]
            raise

    def get_document(self, document_id: str) -> dict[str, Any | None] | None:
        """Retrieve document with full content.

        Args:
            document_id: Document identifier

        Returns:
            Document data with content and metadata

        Raises:
            IOError: If retrieval fails
        """
        try:
            return self.repository.read(document_id)
        except OSError as e:
            logger.error("DOCUMENT_RETRIEVAL_FAILED", document_id=document_id, error=str(e))  # type: ignore[call-arg]
            raise

    def get_document_summary(self, document_id: str) -> dict[str, Any | None] | None:
        """Retrieve document metadata without full content.

        Useful for listing documents without loading full content.

        Args:
            document_id: Document identifier

        Returns:
            Document metadata summary
        """
        doc = self.repository.read(document_id)
        if not doc:
            return None

        return {
            "document_id": document_id,
            "metadata": doc.get("metadata", {}),
            "content_length": len(doc.get("content", "")),
        }

    def list_documents(
        self,
        limit: Optional[int] = None,
        source: Optional[str] = None,
    ) -> list[dict[str, Any] | None]:
        """List documents with optional filtering.

        Args:
            limit: Maximum documents to return
            source: Filter by document source

        Returns:
            List of document summaries
        """
        docs = self.repository.list_all(limit=limit)

        if source:
            docs = [d for d in docs if d.get("metadata", {}).get("source") == source]

        return [self.get_document_summary(d["document_id"]) for d in docs]

    def add_diarization_chunk(
        self,
        document_id: str,
        chunk: DiarizationChunkDict,
    ) -> bool:
        """Add diarization result chunk to document.

        Args:
            document_id: Parent document ID
            chunk: Diarization chunk data

        Returns:
            True if chunk was added successfully

        Raises:
            ValueError: If chunk data is invalid
            IOError: If storage fails
        """
        # Validate chunk has required fields
        required_fields = {"chunk_idx", "text", "speaker"}
        if not all(field in chunk for field in required_fields):
            raise ValueError(f"Chunk missing required fields: {required_fields}")

        chunk_idx = chunk.get("chunk_idx")
        if chunk_idx is None or chunk_idx < 0:
            raise ValueError("chunk_idx must be >= 0")

        try:
            success = self.repository.add_chunk(chunk, document_id)
            if success:
                logger.info(
                    "DIARIZATION_CHUNK_ADDED",
                    document_id=document_id,
                    chunk_idx=chunk_idx,
                )
            return success

        except OSError as e:
            logger.error("CHUNK_ADDITION_FAILED", document_id=document_id, error=str(e))
            raise

    def get_chunks(self, document_id: str) -> list[DiarizationChunkDict]:
        """Retrieve all diarization chunks for document.

        Args:
            document_id: Document identifier

        Returns:
            List of chunks sorted by index
        """
        try:
            return self.repository.get_chunks(document_id)
        except OSError as e:
            logger.error("CHUNKS_RETRIEVAL_FAILED", document_id=document_id, error=str(e))  # type: ignore[call-arg]
            raise

    def delete_document(self, document_id: str) -> bool:
        """Delete document (soft delete for append-only compliance).

        Args:
            document_id: Document identifier

        Returns:
            True if deletion successful
        """
        try:
            success = self.repository.delete(document_id)
            if success:
                logger.info("DOCUMENT_DELETED", document_id=document_id)  # type: ignore[call-arg]
            return success
        except OSError as e:
            logger.error("DOCUMENT_DELETION_FAILED", document_id=document_id, error=str(e))  # type: ignore[call-arg]
            raise
