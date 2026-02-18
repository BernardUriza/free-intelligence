"""HDF5-based document repository implementation.

Stores documents and embeddings in HDF5 for efficient retrieval.
Uses in-memory vector store for semantic search (can switch to Chroma/FAISS later).

Security: ALL operations enforce clinic_id filtering.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-01-29
Card: Document Repository Implementation
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

import h5py
import numpy as np

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
from backend.utils.math.cpu import cosine_similarity_batch
from backend.services.assistant.services.monitor_client import similarity_search_gpu
from backend.utils.common.types import utc_now
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

# GPU delegation threshold: use GPU for >1000 vectors
GPU_SEARCH_THRESHOLD = 1000


class HDF5DocumentRepository(IDocumentRepository):
    """HDF5-based document repository.

    Structure:
        documents.h5
        ├── /documents/
        │   ├── {doc_id}/
        │   │   ├── metadata (JSON string)
        │   │   ├── content (text)
        │   │   └── chunks/
        │   │       ├── {chunk_id}/
        │   │       │   ├── text
        │   │       │   ├── embedding (vector)
        │   │       │   └── metadata (JSON)

    In-memory index for fast search (loaded on startup):
        {
            clinic_id: {
                doc_id: {
                    "chunks": [(chunk_id, embedding), ...]
                }
            }
        }
    """

    def __init__(self, storage_path: str | Path = "storage/documents.h5"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # In-memory vector index for semantic search
        # Structure: {clinic_id: {doc_id: [(chunk_id, embedding), ...]}}
        self._vector_index: dict[str, dict[str, list[tuple[str, np.ndarray]]]] = {}

        self._initialize_storage()
        self._load_vector_index()

    def _initialize_storage(self) -> None:
        """Create HDF5 file if it doesn't exist."""
        if not self.storage_path.exists():
            with h5py.File(self.storage_path, "w") as f:
                f.create_group("documents")
            logger.info("HDF5_STORAGE_INITIALIZED", path=str(self.storage_path))

    def _load_vector_index(self) -> None:
        """Load all embeddings into memory for fast search."""
        logger.info("VECTOR_INDEX_LOADING", path=str(self.storage_path))

        with h5py.File(self.storage_path, "r") as f:
            docs_group = f["documents"]

            for doc_id in docs_group.keys():
                doc_group = docs_group[doc_id]

                # Get clinic_id from metadata
                metadata_json = doc_group["metadata"][()]
                if isinstance(metadata_json, bytes):
                    metadata_json = metadata_json.decode("utf-8")
                metadata = json.loads(metadata_json)
                clinic_id = metadata.get("clinic_id")

                if not clinic_id:
                    continue

                # Initialize clinic index if needed
                if clinic_id not in self._vector_index:
                    self._vector_index[clinic_id] = {}

                # Load chunks
                if "chunks" in doc_group:
                    chunks_group = doc_group["chunks"]
                    chunk_data = []

                    for chunk_id in chunks_group.keys():
                        chunk_group = chunks_group[chunk_id]
                        if "embedding" in chunk_group:
                            embedding = chunk_group["embedding"][:]
                            chunk_data.append((chunk_id, embedding))

                    if chunk_data:
                        self._vector_index[clinic_id][doc_id] = chunk_data

        total_chunks = sum(
            len(chunks)
            for clinic_docs in self._vector_index.values()
            for chunks in clinic_docs.values()
        )
        logger.info(
            "VECTOR_INDEX_LOADED",
            clinics=len(self._vector_index),
            documents=sum(len(docs) for docs in self._vector_index.values()),
            chunks=total_chunks
        )

    # =============================================================================
    # DOCUMENT CRUD
    # =============================================================================

    def create_document(
        self,
        doc: Document,
        file_content: bytes | None = None
    ) -> Document:
        """Create a new document."""
        if not doc.clinic_id:
            raise ValueError("clinic_id is required")

        # Generate doc_id if not provided
        if not doc.doc_id:
            doc.doc_id = str(uuid.uuid4())

        with h5py.File(self.storage_path, "a") as f:
            docs_group = f["documents"]

            # Create document group
            doc_group = docs_group.create_group(doc.doc_id)

            # Store metadata (includes clinic_id for filtering)
            metadata_dict = {
                "doc_id": doc.doc_id,
                "clinic_id": doc.clinic_id,
                "title": doc.title,
                "status": doc.status.value,
                "origin": doc.origin.value,
                "uploaded_by": doc.uploaded_by,
                "uploaded_at": doc.uploaded_at.isoformat(),
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                "error_message": doc.error_message,
                "retry_count": doc.retry_count,
                "metadata": {
                    "specialty": doc.metadata.specialty,
                    "language": doc.metadata.language,
                    "keywords": doc.metadata.keywords,
                    "document_type": doc.metadata.document_type.value,
                    "file_size_bytes": doc.metadata.file_size_bytes,
                    "mime_type": doc.metadata.mime_type,
                    "original_filename": doc.metadata.original_filename,
                    "num_pages": doc.metadata.num_pages,
                    "num_chunks": doc.metadata.num_chunks,
                    "embedding_model": doc.metadata.embedding_model,
                    "custom": doc.metadata.custom,
                }
            }
            doc_group.create_dataset("metadata", data=json.dumps(metadata_dict))

            # Store content
            doc_group.create_dataset("content", data=doc.content)

            # Store file content if provided
            if file_content:
                doc_group.create_dataset("file_content", data=np.frombuffer(file_content, dtype=np.uint8))

        logger.info(
            "DOCUMENT_CREATED",
            doc_id=doc.doc_id,
            clinic_id=doc.clinic_id,
            title=doc.title,
            size_bytes=len(doc.content)
        )

        return doc

    def get_document(
        self,
        doc_id: str,
        clinic_id: str
    ) -> Document | None:
        """Get a document by ID (with clinic_id filter)."""
        try:
            with h5py.File(self.storage_path, "r") as f:
                if doc_id not in f["documents"]:
                    return None

                doc_group = f["documents"][doc_id]

                # Load metadata
                metadata_json = doc_group["metadata"][()]
                if isinstance(metadata_json, bytes):
                    metadata_json = metadata_json.decode("utf-8")
                metadata_dict = json.loads(metadata_json)

                # Security check: verify clinic_id
                if metadata_dict["clinic_id"] != clinic_id:
                    logger.warning(
                        "DOCUMENT_ACCESS_DENIED",
                        doc_id=doc_id,
                        requested_clinic=clinic_id,
                        actual_clinic=metadata_dict["clinic_id"]
                    )
                    return None

                # Load content
                content = doc_group["content"][()]
                if isinstance(content, bytes):
                    content = content.decode("utf-8")

                # Reconstruct Document entity
                doc_metadata = DocumentMetadata(
                    specialty=metadata_dict["metadata"].get("specialty"),
                    language=metadata_dict["metadata"].get("language", "es"),
                    keywords=metadata_dict["metadata"].get("keywords", []),
                    document_type=DocumentType(metadata_dict["metadata"].get("document_type", "other")),
                    file_size_bytes=metadata_dict["metadata"].get("file_size_bytes", 0),
                    mime_type=metadata_dict["metadata"].get("mime_type", "application/pdf"),
                    original_filename=metadata_dict["metadata"].get("original_filename", ""),
                    num_pages=metadata_dict["metadata"].get("num_pages", 0),
                    num_chunks=metadata_dict["metadata"].get("num_chunks", 0),
                    embedding_model=metadata_dict["metadata"].get("embedding_model", ""),
                    custom=metadata_dict["metadata"].get("custom", {})
                )

                return Document(
                    doc_id=metadata_dict["doc_id"],
                    clinic_id=metadata_dict["clinic_id"],
                    title=metadata_dict["title"],
                    content=content,
                    metadata=doc_metadata,
                    uploaded_by=metadata_dict["uploaded_by"],
                    status=DocumentStatus(metadata_dict["status"]),
                    origin=DocumentOrigin(metadata_dict["origin"]),
                    uploaded_at=datetime.fromisoformat(metadata_dict["uploaded_at"]),
                    updated_at=datetime.fromisoformat(metadata_dict["updated_at"]) if metadata_dict["updated_at"] else None,
                    error_message=metadata_dict.get("error_message"),
                    retry_count=metadata_dict.get("retry_count", 0)
                )

        except Exception as e:
            logger.error("DOCUMENT_GET_ERROR", doc_id=doc_id, clinic_id=clinic_id, error=str(e))
            return None

    def list_documents(
        self,
        clinic_id: str,
        status: DocumentStatus | None = None,
        skip: int = 0,
        limit: int = 50
    ) -> list[Document]:
        """List documents for a clinic."""
        documents = []

        try:
            with h5py.File(self.storage_path, "r") as f:
                docs_group = f["documents"]

                for doc_id in docs_group.keys():
                    doc = self.get_document(doc_id, clinic_id)
                    if doc is None:
                        continue  # Wrong clinic or error

                    if status and doc.status != status:
                        continue  # Status filter

                    documents.append(doc)

            # Sort by uploaded_at (newest first)
            documents.sort(key=lambda d: d.uploaded_at, reverse=True)

            # Pagination
            return documents[skip:skip + limit]

        except Exception as e:
            logger.error("DOCUMENT_LIST_ERROR", clinic_id=clinic_id, error=str(e))
            return []

    def update_document(
        self,
        doc_id: str,
        clinic_id: str,
        updates: dict
    ) -> Document | None:
        """Update document metadata."""
        doc = self.get_document(doc_id, clinic_id)
        if doc is None:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(doc, key):
                setattr(doc, key, value)

        doc.updated_at = utc_now()

        # Re-save document
        try:
            with h5py.File(self.storage_path, "a") as f:
                doc_group = f["documents"][doc_id]

                # Update metadata
                metadata_dict = {
                    "doc_id": doc.doc_id,
                    "clinic_id": doc.clinic_id,
                    "title": doc.title,
                    "status": doc.status.value,
                    "origin": doc.origin.value,
                    "uploaded_by": doc.uploaded_by,
                    "uploaded_at": doc.uploaded_at.isoformat(),
                    "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
                    "error_message": doc.error_message,
                    "retry_count": doc.retry_count,
                    "metadata": {
                        "specialty": doc.metadata.specialty,
                        "language": doc.metadata.language,
                        "keywords": doc.metadata.keywords,
                        "document_type": doc.metadata.document_type.value,
                        "file_size_bytes": doc.metadata.file_size_bytes,
                        "mime_type": doc.metadata.mime_type,
                        "original_filename": doc.metadata.original_filename,
                        "num_pages": doc.metadata.num_pages,
                        "num_chunks": doc.metadata.num_chunks,
                        "embedding_model": doc.metadata.embedding_model,
                        "custom": doc.metadata.custom,
                    }
                }

                # Delete old metadata dataset and create new one
                del doc_group["metadata"]
                doc_group.create_dataset("metadata", data=json.dumps(metadata_dict))

            logger.info("DOCUMENT_UPDATED", doc_id=doc_id, clinic_id=clinic_id, updates=list(updates.keys()))
            return doc

        except Exception as e:
            logger.error("DOCUMENT_UPDATE_ERROR", doc_id=doc_id, clinic_id=clinic_id, error=str(e))
            return None

    def delete_document(
        self,
        doc_id: str,
        clinic_id: str,
        soft_delete: bool = True
    ) -> bool:
        """Delete a document."""
        doc = self.get_document(doc_id, clinic_id)
        if doc is None:
            return False

        if soft_delete:
            # Mark as ARCHIVED
            self.update_document(doc_id, clinic_id, {"status": DocumentStatus.ARCHIVED})
        else:
            # Hard delete
            try:
                with h5py.File(self.storage_path, "a") as f:
                    del f["documents"][doc_id]

                # Remove from vector index
                if clinic_id in self._vector_index:
                    self._vector_index[clinic_id].pop(doc_id, None)

                logger.info("DOCUMENT_DELETED", doc_id=doc_id, clinic_id=clinic_id, soft_delete=False)
            except Exception as e:
                logger.error("DOCUMENT_DELETE_ERROR", doc_id=doc_id, clinic_id=clinic_id, error=str(e))
                return False

        return True

    def get_document_count(
        self,
        clinic_id: str,
        status: DocumentStatus | None = None
    ) -> int:
        """Count documents for a clinic."""
        return len(self.list_documents(clinic_id, status=status, skip=0, limit=10000))

    # =============================================================================
    # DOCUMENT CHUNKS
    # =============================================================================

    def save_chunks(
        self,
        doc_id: str,
        clinic_id: str,
        chunks: list[DocumentChunk]
    ) -> int:
        """Save chunks for a document."""
        # Verify document belongs to clinic
        doc = self.get_document(doc_id, clinic_id)
        if doc is None:
            raise ValueError(f"Document {doc_id} not found or access denied")

        try:
            with h5py.File(self.storage_path, "a") as f:
                doc_group = f["documents"][doc_id]

                # Create chunks group if not exists
                if "chunks" not in doc_group:
                    chunks_group = doc_group.create_group("chunks")
                else:
                    chunks_group = doc_group["chunks"]

                for chunk in chunks:
                    chunk_group = chunks_group.create_group(chunk.chunk_id)
                    chunk_group.create_dataset("text", data=chunk.text)
                    chunk_group.create_dataset("embedding", data=np.array(chunk.embedding or []))
                    chunk_group.create_dataset("metadata", data=json.dumps(chunk.to_dict()))

                    # Add to vector index
                    if clinic_id not in self._vector_index:
                        self._vector_index[clinic_id] = {}
                    if doc_id not in self._vector_index[clinic_id]:
                        self._vector_index[clinic_id][doc_id] = []

                    if chunk.embedding:
                        self._vector_index[clinic_id][doc_id].append(
                            (chunk.chunk_id, np.array(chunk.embedding))
                        )

            logger.info("CHUNKS_SAVED", doc_id=doc_id, clinic_id=clinic_id, count=len(chunks))
            return len(chunks)

        except Exception as e:
            logger.error("CHUNKS_SAVE_ERROR", doc_id=doc_id, clinic_id=clinic_id, error=str(e))
            return 0

    def get_chunks(
        self,
        doc_id: str,
        clinic_id: str
    ) -> list[DocumentChunk]:
        """Get all chunks for a document."""
        # Verify document belongs to clinic
        doc = self.get_document(doc_id, clinic_id)
        if doc is None:
            return []

        chunks = []

        try:
            with h5py.File(self.storage_path, "r") as f:
                doc_group = f["documents"][doc_id]

                if "chunks" not in doc_group:
                    return []

                chunks_group = doc_group["chunks"]

                for chunk_id in chunks_group.keys():
                    chunk_group = chunks_group[chunk_id]
                    metadata_json = chunk_group["metadata"][()]
                    if isinstance(metadata_json, bytes):
                        metadata_json = metadata_json.decode("utf-8")
                    chunk_dict = json.loads(metadata_json)

                    chunk = DocumentChunk.from_dict(chunk_dict)
                    chunks.append(chunk)

            return sorted(chunks, key=lambda c: c.chunk_index)

        except Exception as e:
            logger.error("CHUNKS_GET_ERROR", doc_id=doc_id, clinic_id=clinic_id, error=str(e))
            return []

    def delete_chunks(
        self,
        doc_id: str,
        clinic_id: str
    ) -> int:
        """Delete all chunks for a document."""
        # Verify document belongs to clinic
        doc = self.get_document(doc_id, clinic_id)
        if doc is None:
            return 0

        try:
            with h5py.File(self.storage_path, "a") as f:
                doc_group = f["documents"][doc_id]

                if "chunks" not in doc_group:
                    return 0

                chunk_count = len(doc_group["chunks"].keys())
                del doc_group["chunks"]

            # Remove from vector index
            if clinic_id in self._vector_index:
                self._vector_index[clinic_id].pop(doc_id, None)

            logger.info("CHUNKS_DELETED", doc_id=doc_id, clinic_id=clinic_id, count=chunk_count)
            return chunk_count

        except Exception as e:
            logger.error("CHUNKS_DELETE_ERROR", doc_id=doc_id, clinic_id=clinic_id, error=str(e))
            return 0

    # =============================================================================
    # SEMANTIC SEARCH
    # =============================================================================

    async def search_by_embedding(
        self,
        query_embedding: list[float],
        clinic_id: str,
        limit: int = 10,
        min_score: float = 0.5,
        document_type: str | None = None
    ) -> list[SearchResult]:
        """Semantic search using query embedding.

        AUTO GPU DELEGATION: Uses fi_monitor GPU for >1000 vectors.

        CRITICAL SECURITY: Only searches within clinic_id boundary.
        """
        if clinic_id not in self._vector_index:
            return []

        results = []
        clinic_docs = self._vector_index[clinic_id]

        # Collect all vectors and metadata
        all_vectors = []
        all_metadata = []  # (doc_id, chunk_id, doc)

        for doc_id, chunk_data in clinic_docs.items():
            # Get document metadata
            doc = self.get_document(doc_id, clinic_id)
            if doc is None:
                continue

            # Document type filter
            if document_type and doc.metadata.document_type.value != document_type:
                continue

            # Skip non-indexed documents
            if doc.status != DocumentStatus.INDEXED:
                continue

            # Collect vectors
            for chunk_id, chunk_embedding in chunk_data:
                all_vectors.append(chunk_embedding.tolist())
                all_metadata.append((doc_id, chunk_id, doc))

        # Compute similarities (GPU or CPU based on size)
        if len(all_vectors) > GPU_SEARCH_THRESHOLD:
            # GPU delegation to fi_monitor
            try:
                similarities = await similarity_search_gpu(
                    query_embedding,
                    all_vectors,
                )
            except (ConnectionError, ValueError) as e:
                # Fallback to CPU if fi_monitor unavailable
                logger.warning(
                    "GPU_SEARCH_FALLBACK",
                    vectors=len(all_vectors),
                    error=str(e),
                )
                similarities = cosine_similarity_batch(query_embedding, all_vectors)
        else:
            # CPU local (sufficient for <1000 vectors)
            similarities = cosine_similarity_batch(query_embedding, all_vectors)

        # Filter by min_score and collect results
        for idx, (doc_id, chunk_id, doc) in enumerate(all_metadata):
            score = similarities[idx]

            if score >= min_score:
                # Get chunk text
                chunks = self.get_chunks(doc_id, clinic_id)
                chunk = next((c for c in chunks if c.chunk_id == chunk_id), None)
                if chunk is None:
                    continue

                result = SearchResult(
                    doc_id=doc.doc_id,
                    title=doc.title,
                    chunk_id=chunk_id,
                    chunk_text=chunk.text,
                    page_num=chunk.page_num,
                    score=score,
                    document_type=doc.metadata.document_type,
                    specialty=doc.metadata.specialty
                )
                results.append(result)

        # Sort by score (highest first) and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    # =============================================================================
    # BULK OPERATIONS
    # =============================================================================

    def reindex_document(
        self,
        doc_id: str,
        clinic_id: str
    ) -> bool:
        """Mark document for re-indexing."""
        return self.update_document(
            doc_id,
            clinic_id,
            {"status": DocumentStatus.PENDING, "retry_count": 0, "error_message": None}
        ) is not None

    def get_pending_documents(
        self,
        clinic_id: str | None = None,
        limit: int = 100
    ) -> list[Document]:
        """Get documents pending indexing."""
        pending = []

        try:
            with h5py.File(self.storage_path, "r") as f:
                docs_group = f["documents"]

                for doc_id in docs_group.keys():
                    # Get document metadata
                    doc_group = docs_group[doc_id]
                    metadata_json = doc_group["metadata"][()]
                    if isinstance(metadata_json, bytes):
                        metadata_json = metadata_json.decode("utf-8")
                    metadata = json.loads(metadata_json)

                    # Clinic filter (if specified)
                    if clinic_id and metadata["clinic_id"] != clinic_id:
                        continue

                    # Status filter
                    if metadata["status"] in [DocumentStatus.PENDING.value, DocumentStatus.INDEXING.value]:
                        doc = self.get_document(doc_id, metadata["clinic_id"])
                        if doc:
                            pending.append(doc)

            return pending[:limit]

        except Exception as e:
            logger.error("PENDING_DOCUMENTS_ERROR", clinic_id=clinic_id, error=str(e))
            return []


__all__ = ["HDF5DocumentRepository"]
