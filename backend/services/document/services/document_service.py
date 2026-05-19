"""Document Service - Orchestrates document processing workflow.

Workflow:
1. Upload document (PDF, DOCX, TXT)
2. Extract text content
3. Chunk text (paragraph-aware for medical context)
4. Generate embeddings for each chunk
5. Store in repository + vector index
6. Mark as INDEXED

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Card: Document Repository Implementation
"""

from __future__ import annotations

import uuid
from datetime import datetime

from backend.repositories.interfaces.idocument_repository import IDocumentRepository
from backend.domain.document.models import (
    Document,
    DocumentChunk,
    DocumentMetadata,
    DocumentOrigin,
    DocumentStatus,
    DocumentType,
    SearchResult,
)
from fi_core.rag import (
    ChunkConfig,
    ChunkingStrategy,
    chunk_document,
)
from backend.services.document.services.embedding_service import (
    generate_embedding,
    generate_embeddings_batch,
)
from backend.utils.common.types import utc_now
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)
class DocumentService:
    """High-level document management service.

    Orchestrates:
    - Document upload and processing
    - Text extraction (PDF, DOCX, TXT)
    - Chunking and embedding generation
    - Semantic search

    Dependencies:
    - IDocumentRepository (storage)
    - Chunking strategy (text splitting)
    - Embedding service (vector generation)
    """

    def __init__(
        self,
        repository: IDocumentRepository,
    ):
        """Initialize document service with dependencies.

        Args:
            repository: Document repository implementation (required)
        """
        self.repository = repository

    # =============================================================================
    # DOCUMENT UPLOAD & PROCESSING
    # =============================================================================

    def upload_document(
        self,
        clinic_id: str,
        title: str,
        content: str,
        uploaded_by: str,
        file_content: bytes | None = None,
        metadata: DocumentMetadata | None = None,
        origin: DocumentOrigin = DocumentOrigin.API_UPLOAD,
        auto_index: bool = True
    ) -> Document:
        """Upload a new document.

        Args:
            clinic_id: Clinic ID (multi-tenancy)
            title: Document title
            content: Extracted text content
            uploaded_by: User ID (JWT subject)
            file_content: Optional binary file content (PDF, DOCX)
            metadata: Optional document metadata
            origin: How document was uploaded
            auto_index: If True, automatically chunk + embed (default: True)

        Returns:
            Created document (status=PENDING if auto_index, else INDEXED)

        Raises:
            ValueError: If clinic_id or content is empty
        """
        if not clinic_id or not clinic_id.strip():
            raise ValueError("clinic_id is required")

        if not content or not content.strip():
            raise ValueError("content is required (empty documents not allowed)")

        # Create document entity
        doc = Document(
            doc_id=str(uuid.uuid4()),
            clinic_id=clinic_id,
            title=title,
            content=content,
            metadata=metadata or DocumentMetadata(),
            uploaded_by=uploaded_by,
            status=DocumentStatus.PENDING if auto_index else DocumentStatus.INDEXED,
            origin=origin
        )

        # Store document
        doc = self.repository.create_document(doc, file_content=file_content)

        logger.info(
            "DOCUMENT_UPLOADED",
            doc_id=doc.doc_id,
            clinic_id=clinic_id,
            title=title,
            size=len(content),
            auto_index=auto_index
        )

        # Auto-index if requested
        if auto_index:
            try:
                self.index_document(doc.doc_id, clinic_id)
            except Exception as e:
                logger.error(
                    "DOCUMENT_AUTO_INDEX_FAILED",
                    doc_id=doc.doc_id,
                    clinic_id=clinic_id,
                    error=str(e)
                )
                # Mark as ERROR
                self.repository.update_document(
                    doc.doc_id,
                    clinic_id,
                    {
                        "status": DocumentStatus.ERROR,
                        "error_message": f"Auto-index failed: {str(e)}"
                    }
                )

        return doc

    def index_document(
        self,
        doc_id: str,
        clinic_id: str,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH_AWARE,
        chunk_config: ChunkConfig | None = None
    ) -> bool:
        """Index a document (chunk + embed).

        Args:
            doc_id: Document ID
            clinic_id: Clinic ID (security boundary)
            chunking_strategy: How to split text
            chunk_config: Optional chunking configuration

        Returns:
            True if indexed successfully, False otherwise
        """
        # Get document
        doc = self.repository.get_document(doc_id, clinic_id)
        if doc is None:
            logger.error("DOCUMENT_NOT_FOUND", doc_id=doc_id, clinic_id=clinic_id)
            return False

        # Mark as INDEXING
        self.repository.update_document(doc_id, clinic_id, {"status": DocumentStatus.INDEXING})

        try:
            # Step 1: Chunk text
            logger.info(
                "DOCUMENT_CHUNKING",
                doc_id=doc_id,
                strategy=chunking_strategy.value,
                size=len(doc.content)
            )
            chunk_texts = chunk_document(doc.content, chunking_strategy, chunk_config)

            if not chunk_texts:
                raise ValueError("No chunks generated (content too short?)")

            # Step 2: Generate embeddings (batched for efficiency)
            logger.info(
                "DOCUMENT_EMBEDDING",
                doc_id=doc_id,
                num_chunks=len(chunk_texts)
            )
            embeddings = generate_embeddings_batch(chunk_texts)

            # Step 3: Create DocumentChunk entities
            chunks = []
            for idx, (chunk_text, embedding) in enumerate(zip(chunk_texts, embeddings)):
                chunk = DocumentChunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    clinic_id=clinic_id,
                    text=chunk_text,
                    chunk_index=idx,
                    embedding=embedding
                )
                chunks.append(chunk)

            # Step 4: Save chunks to repository
            num_saved = self.repository.save_chunks(doc_id, clinic_id, chunks)

            if num_saved != len(chunks):
                raise ValueError(f"Only {num_saved}/{len(chunks)} chunks saved")

            # Step 5: Mark as INDEXED
            self.repository.update_document(
                doc_id,
                clinic_id,
                {
                    "status": DocumentStatus.INDEXED,
                    "error_message": None,
                    "updated_at": utc_now()
                }
            )

            # Update metadata with chunk count
            doc.metadata.num_chunks = len(chunks)
            self.repository.update_document(
                doc_id,
                clinic_id,
                {"metadata": doc.metadata}
            )

            logger.info(
                "DOCUMENT_INDEXED",
                doc_id=doc_id,
                clinic_id=clinic_id,
                num_chunks=len(chunks)
            )

            return True

        except Exception as e:
            logger.error(
                "DOCUMENT_INDEX_ERROR",
                doc_id=doc_id,
                clinic_id=clinic_id,
                error=str(e),
                error_type=type(e).__name__
            )

            # Mark as ERROR
            self.repository.update_document(
                doc_id,
                clinic_id,
                {
                    "status": DocumentStatus.ERROR,
                    "error_message": str(e),
                    "retry_count": (doc.retry_count or 0) + 1
                }
            )

            return False

    # =============================================================================
    # SEMANTIC SEARCH
    # =============================================================================

    async def search(
        self,
        query: str,
        clinic_id: str,
        limit: int = 10,
        min_score: float = 0.5,
        document_type: DocumentType | None = None
    ) -> list[SearchResult]:
        """Semantic search across documents.

        AUTO GPU DELEGATION: Uses GPU for >1000 vectors via fi_monitor.

        Args:
            query: Natural language query (e.g., "diabetes treatment guidelines")
            clinic_id: Clinic ID (security boundary)
            limit: Max results to return
            min_score: Minimum cosine similarity score (0-1)
            document_type: Optional filter by document type

        Returns:
            List of search results, sorted by relevance (highest first)

        Security:
            ONLY searches within clinic_id boundary
        """
        if not query or not query.strip():
            return []

        try:
            # Generate query embedding
            query_embedding = generate_embedding(query)

            # Search in repository (clinic_id filtered, GPU-accelerated)
            results = await self.repository.search_by_embedding(
                query_embedding=query_embedding,
                clinic_id=clinic_id,
                limit=limit,
                min_score=min_score,
                document_type=document_type.value if document_type else None
            )

            logger.info(
                "SEARCH_COMPLETED",
                query=query[:50],  # Truncate for logging
                clinic_id=clinic_id,
                results=len(results)
            )

            return results

        except Exception as e:
            logger.error(
                "SEARCH_ERROR",
                query=query[:50],
                clinic_id=clinic_id,
                error=str(e)
            )
            return []

    # =============================================================================
    # CRUD OPERATIONS (Proxies to repository)
    # =============================================================================

    def get_document(
        self,
        doc_id: str,
        clinic_id: str
    ) -> Document | None:
        """Get a document by ID."""
        return self.repository.get_document(doc_id, clinic_id)

    def list_documents(
        self,
        clinic_id: str,
        status: DocumentStatus | None = None,
        skip: int = 0,
        limit: int = 50
    ) -> list[Document]:
        """List documents for a clinic."""
        return self.repository.list_documents(clinic_id, status, skip, limit)

    def update_document(
        self,
        doc_id: str,
        clinic_id: str,
        updates: dict
    ) -> Document | None:
        """Update document metadata."""
        return self.repository.update_document(doc_id, clinic_id, updates)

    def delete_document(
        self,
        doc_id: str,
        clinic_id: str,
        soft_delete: bool = True
    ) -> bool:
        """Delete a document."""
        return self.repository.delete_document(doc_id, clinic_id, soft_delete)

    def get_document_count(
        self,
        clinic_id: str,
        status: DocumentStatus | None = None
    ) -> int:
        """Count documents for a clinic."""
        return self.repository.get_document_count(clinic_id, status)

    # =============================================================================
    # BATCH OPERATIONS
    # =============================================================================

    def reindex_document(
        self,
        doc_id: str,
        clinic_id: str
    ) -> bool:
        """Re-index a document (useful after embedding model upgrade)."""
        # Delete old chunks
        self.repository.delete_chunks(doc_id, clinic_id)

        # Mark as PENDING
        self.repository.reindex_document(doc_id, clinic_id)

        # Re-index
        return self.index_document(doc_id, clinic_id)

    def process_pending_documents(
        self,
        clinic_id: str | None = None,
        limit: int = 10
    ) -> tuple[int, int]:
        """Process pending documents (background worker).

        Args:
            clinic_id: Optional clinic filter (None = all clinics, for SUPERADMIN)
            limit: Max documents to process

        Returns:
            (success_count, error_count)
        """
        pending = self.repository.get_pending_documents(clinic_id, limit)

        success = 0
        errors = 0

        for doc in pending:
            indexed = self.index_document(doc.doc_id, doc.clinic_id)
            if indexed:
                success += 1
            else:
                errors += 1

        logger.info(
            "BATCH_PROCESSING_COMPLETED",
            clinic_id=clinic_id,
            total=len(pending),
            success=success,
            errors=errors
        )

        return (success, errors)


__all__ = ["DocumentService"]
