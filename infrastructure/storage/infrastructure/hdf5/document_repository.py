"""Document Repository for Knowledge Base.

Storage and retrieval of documents for RAG (Retrieval-Augmented Generation).
Documents are stored in HDF5 with full-text extraction and embedding support.

Structure:
  /documents/{doc_id}/
    ├── content (bytes - original file)
    ├── text (string - extracted text)
    ├── metadata (attrs - JSON metadata)
    └── chunks/
        ├── chunk_0/
        │   ├── text (string)
        │   └── embedding (float32[768])
        └── chunk_N/

Philosophy:
  - Documents are append-only (immutable once created)
  - Each document has a unique doc_id (UUID)
  - Text is chunked for efficient RAG retrieval
  - Embeddings enable semantic search

Author: Bernard Uriza Orozco
Created: 2025-12-08
Card: FI-API-FEAT-020
"""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import h5py
import numpy as np
from backend.utils.common.logging.logger import get_logger
from infrastructure.storage.infrastructure.hdf5.session_h5_manager import CORPUS_PATH
from pathlib import Path

logger = get_logger(__name__)

# Lock for thread-safe HDF5 access
_doc_lock = threading.RLock()

# Chunk size for text splitting (in characters)
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50

# Embedding dimension (sentence-transformers all-MiniLM-L6-v2)
EMBEDDING_DIM = 384


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    """Uploaded, waiting for processing."""

    PROCESSING = "processing"
    """Text extraction and embedding in progress."""

    INDEXED = "indexed"
    """Ready for RAG queries."""

    ERROR = "error"
    """Processing failed."""


class DocumentType(str, Enum):
    """Supported document types."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    IMAGE = "image"  # OCR
    MARKDOWN = "markdown"


class DocumentOrigin(str, Enum):
    """Where the document was uploaded from."""

    ADMIN_UPLOAD = "admin_upload"
    CHAT_WIDGET = "chat_widget"


@dataclass
class DocumentMetadata:
    """Document metadata stored as HDF5 attributes."""

    doc_id: str
    title: str
    doc_type: DocumentType
    origin: DocumentOrigin
    uploaded_by: str  # doctor_id or user_id
    uploaded_at: str  # ISO timestamp
    usage_instructions: str
    assigned_personas: list[str]
    status: DocumentStatus
    size_bytes: int
    sha256: str
    chunks_count: int = 0
    chunk_version: int = 2  # 1=char-based (512 chars), 2=token-based (256 tokens)
    error_message: str | None = None
    # Security & Multi-tenancy (Phase 1 - HIPAA compliance)
    owner_user_id: str = ""  # Auth0 user_id (sub claim) - primary owner
    clinic_id: str = ""  # Clinic/organization ID for multi-tenant isolation
    shared_with: list[str] = field(default_factory=list)  # User IDs with explicit access

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "doc_type": self.doc_type.value,
            "origin": self.origin.value,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at,
            "usage_instructions": self.usage_instructions,
            "assigned_personas": self.assigned_personas,
            "status": self.status.value,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "chunks_count": self.chunks_count,
            "chunk_version": self.chunk_version,
            "error_message": self.error_message,
            "owner_user_id": self.owner_user_id,
            "clinic_id": self.clinic_id,
            "shared_with": self.shared_with,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentMetadata:
        """Create from dictionary with backward compatibility."""
        # Backward compatibility: If owner_user_id is missing, use uploaded_by
        owner_user_id = data.get("owner_user_id", "") or data.get("uploaded_by", "")

        return cls(
            doc_id=data["doc_id"],
            title=data["title"],
            doc_type=DocumentType(data["doc_type"]),
            origin=DocumentOrigin(data["origin"]),
            uploaded_by=data["uploaded_by"],
            uploaded_at=data["uploaded_at"],
            usage_instructions=data["usage_instructions"],
            assigned_personas=data["assigned_personas"],
            status=DocumentStatus(data["status"]),
            size_bytes=data["size_bytes"],
            sha256=data["sha256"],
            chunks_count=data.get("chunks_count", 0),
            chunk_version=data.get("chunk_version", 1),  # Default to v1 for old documents
            error_message=data.get("error_message"),
            owner_user_id=owner_user_id,
            clinic_id=data.get("clinic_id", ""),
            shared_with=data.get("shared_with", []),
        )


@dataclass
class DocumentChunk:
    """A chunk of document text with its embedding."""

    chunk_id: int
    text: str
    embedding: np.ndarray | None = None


@dataclass
class Document:
    """Full document with content, text, and chunks."""

    metadata: DocumentMetadata
    content: bytes | None = None  # Original file bytes
    text: str | None = None  # Extracted text
    chunks: list[DocumentChunk] = field(default_factory=list)


@dataclass
class DocumentQuestion:
    """A question associated with a document.

    Questions can come from:
    - LLM initial generation (source="llm_initial")
    - User queries via RAG (source="user_query")
    """

    question_id: int
    question: str
    source: str  # "llm_initial" | "user_query"
    timestamp: str  # ISO format
    answer: str | None = None


def _ensure_documents_group(f: h5py.File) -> h5py.Group:
    """Ensure /documents group exists."""
    if "documents" not in f:
        f.create_group("documents")
        logger.info("DOCUMENTS_GROUP_CREATED")
    return f["documents"]  # type: ignore[return-value]


def _get_doc_type_from_filename(filename: str) -> DocumentType:
    """Infer document type from filename extension."""
    ext = Path(filename).suffix.lower()
    mapping = {
        ".pdf": DocumentType.PDF,
        ".docx": DocumentType.DOCX,
        ".doc": DocumentType.DOCX,
        ".txt": DocumentType.TXT,
        ".md": DocumentType.MARKDOWN,
        ".png": DocumentType.IMAGE,
        ".jpg": DocumentType.IMAGE,
        ".jpeg": DocumentType.IMAGE,
    }
    return mapping.get(ext, DocumentType.TXT)


def create_document(
    content: bytes,
    filename: str,
    uploaded_by: str,
    origin: DocumentOrigin = DocumentOrigin.ADMIN_UPLOAD,
    title: str | None = None,
    usage_instructions: str = "",
    assigned_personas: list[str] | None = None,
    owner_user_id: str | None = None,
    clinic_id: str = "",
) -> DocumentMetadata:
    """Create a new document in the knowledge base.

    Args:
        content: Raw file bytes
        filename: Original filename (used for type detection)
        uploaded_by: User/doctor ID who uploaded (legacy field)
        origin: Where the upload came from
        title: Document title (defaults to filename)
        usage_instructions: How the LLM should use this document
        assigned_personas: List of persona IDs that can use this document
        owner_user_id: Auth0 user_id (sub claim) - primary owner for HIPAA isolation
        clinic_id: Clinic/organization ID for multi-tenant isolation

    Returns:
        DocumentMetadata with doc_id and status=PENDING
    """
    doc_id = str(uuid.uuid4())
    doc_type = _get_doc_type_from_filename(filename)
    sha256 = hashlib.sha256(content).hexdigest()

    # Security: Default owner_user_id to uploaded_by if not explicitly provided
    # This ensures backward compatibility with existing code
    final_owner_user_id = owner_user_id if owner_user_id is not None else uploaded_by

    metadata = DocumentMetadata(
        doc_id=doc_id,
        title=title or filename,
        doc_type=doc_type,
        origin=origin,
        uploaded_by=uploaded_by,
        uploaded_at=datetime.now(UTC).isoformat(),
        usage_instructions=usage_instructions,
        assigned_personas=assigned_personas or [],
        status=DocumentStatus.PENDING,
        size_bytes=len(content),
        sha256=sha256,
        chunks_count=0,
        owner_user_id=final_owner_user_id,
        clinic_id=clinic_id,
        shared_with=[],  # Empty by default, explicit sharing required
    )

    # Store in HDF5
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _doc_lock, h5py.File(CORPUS_PATH, "a") as f:
        docs_group = _ensure_documents_group(f)

        # Create document group
        doc_group = docs_group.create_group(doc_id)

        # Store raw content
        doc_group.create_dataset(
            "content",
            data=np.frombuffer(content, dtype=np.uint8),
            compression="gzip",
            compression_opts=4,
        )

        # Store metadata as JSON attribute
        doc_group.attrs["metadata"] = json.dumps(metadata.to_dict())

        # Create chunks group (empty for now)
        doc_group.create_group("chunks")

        f.flush()

    logger.info(
        "DOCUMENT_CREATED",
        doc_id=doc_id,
        title=metadata.title,
        doc_type=doc_type.value,
        size_bytes=len(content),
        sha256=sha256[:16] + "...",
    )

    return metadata


def get_document(doc_id: str, include_content: bool = False) -> Document | None:
    """Retrieve a document by ID.

    Args:
        doc_id: Document UUID
        include_content: Whether to load raw file bytes

    Returns:
        Document object or None if not found
    """
    if not CORPUS_PATH.exists():
        return None

    with _doc_lock, h5py.File(CORPUS_PATH, "r") as f:
        if "documents" not in f:
            return None

        docs_group = f["documents"]
        if doc_id not in docs_group:
            return None

        doc_group = docs_group[doc_id]

        # Load metadata
        metadata_json = doc_group.attrs["metadata"]
        metadata = DocumentMetadata.from_dict(json.loads(metadata_json))

        # Load content if requested
        content = None
        if include_content and "content" in doc_group:
            content = bytes(doc_group["content"][:])

        # Load extracted text
        text = None
        if "text" in doc_group:
            text = doc_group["text"][()].decode("utf-8")

        # Load chunks
        chunks = []
        if "chunks" in doc_group:
            chunks_group = doc_group["chunks"]
            for chunk_name in sorted(chunks_group, key=lambda x: int(x.split("_")[1])):
                chunk_group = chunks_group[chunk_name]
                chunk_text = chunk_group["text"][()].decode("utf-8")
                chunk_embedding = None
                if "embedding" in chunk_group:
                    chunk_embedding = chunk_group["embedding"][:]
                chunks.append(
                    DocumentChunk(
                        chunk_id=int(chunk_name.split("_")[1]),
                        text=chunk_text,
                        embedding=chunk_embedding,
                    )
                )

        return Document(
            metadata=metadata,
            content=content,
            text=text,
            chunks=chunks,
        )


def list_documents(
    user_id: str | None = None,
    persona_filter: str | None = None,
    origin_filter: DocumentOrigin | None = None,
    status_filter: DocumentStatus | None = None,
) -> list[DocumentMetadata]:
    """List all documents with optional filters.

    SECURITY: If user_id is provided, only returns documents owned by that user
    or explicitly shared with them (HIPAA compliance).

    Args:
        user_id: Auth0 user_id for access control (None = no filtering - admin mode)
        persona_filter: Filter by assigned persona
        origin_filter: Filter by upload origin
        status_filter: Filter by processing status

    Returns:
        List of document metadata accessible to the user
    """
    if not CORPUS_PATH.exists():
        return []

    documents = []

    with _doc_lock, h5py.File(CORPUS_PATH, "r") as f:
        if "documents" not in f:
            return []

        docs_group = f["documents"]

        for doc_id in docs_group:
            doc_group = docs_group[doc_id]
            metadata_json = doc_group.attrs["metadata"]
            metadata = DocumentMetadata.from_dict(json.loads(metadata_json))

            # CRITICAL: User access control check (HIPAA isolation)
            if user_id is not None:
                # User must be owner OR explicitly shared with
                is_owner = metadata.owner_user_id == user_id
                is_shared = user_id in metadata.shared_with
                if not (is_owner or is_shared):
                    continue  # User doesn't have access - skip

            # Apply additional filters
            if persona_filter and persona_filter not in metadata.assigned_personas:
                continue
            if origin_filter and metadata.origin != origin_filter:
                continue
            if status_filter and metadata.status != status_filter:
                continue

            documents.append(metadata)

    # Sort by upload date (newest first)
    documents.sort(key=lambda d: d.uploaded_at, reverse=True)

    return documents


def update_document_metadata(
    doc_id: str,
    title: str | None = None,
    usage_instructions: str | None = None,
    assigned_personas: list[str] | None = None,
) -> DocumentMetadata | None:
    """Update document metadata (title, instructions, personas).

    Args:
        doc_id: Document UUID
        title: New title (optional)
        usage_instructions: New instructions (optional)
        assigned_personas: New persona list (optional)

    Returns:
        Updated metadata or None if not found
    """
    if not CORPUS_PATH.exists():
        return None

    with _doc_lock, h5py.File(CORPUS_PATH, "a") as f:
        if "documents" not in f:
            return None

        docs_group = f["documents"]
        if doc_id not in docs_group:
            return None

        doc_group = docs_group[doc_id]

        # Load current metadata
        metadata_json = doc_group.attrs["metadata"]
        metadata = DocumentMetadata.from_dict(json.loads(metadata_json))

        # Update fields
        if title is not None:
            metadata.title = title
        if usage_instructions is not None:
            metadata.usage_instructions = usage_instructions
        if assigned_personas is not None:
            metadata.assigned_personas = assigned_personas

        # Save updated metadata
        doc_group.attrs["metadata"] = json.dumps(metadata.to_dict())
        f.flush()

        logger.info(
            "DOCUMENT_METADATA_UPDATED",
            doc_id=doc_id,
            title=metadata.title,
        )

        return metadata


def update_document_status(
    doc_id: str,
    status: DocumentStatus,
    error_message: str | None = None,
) -> bool:
    """Update document processing status.

    Args:
        doc_id: Document UUID
        status: New status
        error_message: Error message (for ERROR status)

    Returns:
        True if updated, False if not found
    """
    if not CORPUS_PATH.exists():
        return False

    with _doc_lock, h5py.File(CORPUS_PATH, "a") as f:
        if "documents" not in f:
            return False

        docs_group = f["documents"]
        if doc_id not in docs_group:
            return False

        doc_group = docs_group[doc_id]

        # Load current metadata
        metadata_json = doc_group.attrs["metadata"]
        metadata = DocumentMetadata.from_dict(json.loads(metadata_json))

        # Update status
        metadata.status = status
        if error_message:
            metadata.error_message = error_message

        # Save updated metadata
        doc_group.attrs["metadata"] = json.dumps(metadata.to_dict())
        f.flush()

        logger.info(
            "DOCUMENT_STATUS_UPDATED",
            doc_id=doc_id,
            status=status.value,
        )

        return True


def save_document_text(doc_id: str, text: str) -> bool:
    """Save extracted text for a document.

    Args:
        doc_id: Document UUID
        text: Extracted text content

    Returns:
        True if saved, False if document not found
    """
    if not CORPUS_PATH.exists():
        return False

    with _doc_lock, h5py.File(CORPUS_PATH, "a") as f:
        if "documents" not in f:
            return False

        docs_group = f["documents"]
        if doc_id not in docs_group:
            return False

        doc_group = docs_group[doc_id]

        # Create or update text dataset
        if "text" in doc_group:
            del doc_group["text"]

        doc_group.create_dataset(
            "text",
            data=text.encode("utf-8"),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )

        f.flush()

        logger.info(
            "DOCUMENT_TEXT_SAVED",
            doc_id=doc_id,
            text_length=len(text),
        )

        return True


def save_document_chunks(doc_id: str, chunks: list[DocumentChunk]) -> bool:
    """Save text chunks with embeddings for a document.

    Args:
        doc_id: Document UUID
        chunks: List of chunks with text and embeddings

    Returns:
        True if saved, False if document not found
    """
    if not CORPUS_PATH.exists():
        return False

    with _doc_lock, h5py.File(CORPUS_PATH, "a") as f:
        if "documents" not in f:
            return False

        docs_group = f["documents"]
        if doc_id not in docs_group:
            return False

        doc_group = docs_group[doc_id]

        # Clear existing chunks
        if "chunks" in doc_group:
            del doc_group["chunks"]
        chunks_group = doc_group.create_group("chunks")

        # Save each chunk
        for chunk in chunks:
            chunk_group = chunks_group.create_group(f"chunk_{chunk.chunk_id}")
            chunk_group.create_dataset(
                "text",
                data=chunk.text.encode("utf-8"),
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            if chunk.embedding is not None:
                chunk_group.create_dataset(
                    "embedding",
                    data=chunk.embedding,
                    dtype="float32",
                )

        # Update chunks count in metadata
        metadata_json = doc_group.attrs["metadata"]
        metadata = DocumentMetadata.from_dict(json.loads(metadata_json))
        metadata.chunks_count = len(chunks)
        doc_group.attrs["metadata"] = json.dumps(metadata.to_dict())

        f.flush()

        logger.info(
            "DOCUMENT_CHUNKS_SAVED",
            doc_id=doc_id,
            chunks_count=len(chunks),
        )

        return True


def delete_document(doc_id: str) -> bool:
    """Delete a document from the knowledge base.

    Args:
        doc_id: Document UUID

    Returns:
        True if deleted, False if not found
    """
    if not CORPUS_PATH.exists():
        return False

    with _doc_lock, h5py.File(CORPUS_PATH, "a") as f:
        if "documents" not in f:
            return False

        docs_group = f["documents"]
        if doc_id not in docs_group:
            return False

        del docs_group[doc_id]
        f.flush()

        logger.info("DOCUMENT_DELETED", doc_id=doc_id)

        return True


def search_documents_by_embedding(
    query_embedding: np.ndarray,
    user_id: str | None = None,
    top_k: int = 5,
    persona_filter: str | None = None,
    doc_filter: str | None = None,
) -> list[tuple[str, int, float, str]]:
    """Search documents by semantic similarity.

    SECURITY: If user_id is provided, only searches documents owned by that user
    or explicitly shared with them (HIPAA compliance).

    Args:
        query_embedding: Query vector (same dimension as chunk embeddings)
        user_id: Auth0 user_id for access control (None = no filtering - admin mode)
        top_k: Number of results to return
        persona_filter: Only search documents assigned to this persona
        doc_filter: Only search within this specific document (by doc_id)

    Returns:
        List of (doc_id, chunk_id, similarity_score, chunk_text)
    """
    if not CORPUS_PATH.exists():
        return []

    results = []

    with _doc_lock, h5py.File(CORPUS_PATH, "r") as f:
        if "documents" not in f:
            return []

        docs_group = f["documents"]

        for doc_id in docs_group:
            # Skip if doc_filter is set and doesn't match
            if doc_filter and doc_id != doc_filter:
                continue

            doc_group = docs_group[doc_id]

            # Load metadata for access control and persona filter
            metadata_json = doc_group.attrs["metadata"]
            metadata = DocumentMetadata.from_dict(json.loads(metadata_json))

            # CRITICAL: User access control check (HIPAA isolation)
            if user_id is not None:
                # User must be owner OR explicitly shared with
                is_owner = metadata.owner_user_id == user_id
                is_shared = user_id in metadata.shared_with
                if not (is_owner or is_shared):
                    continue  # User doesn't have access - skip

            # Check persona filter
            if persona_filter:
                if persona_filter not in metadata.assigned_personas:
                    continue

            # Check if indexed
            if "chunks" not in doc_group:
                continue

            chunks_group = doc_group["chunks"]

            for chunk_name in chunks_group:
                chunk_group = chunks_group[chunk_name]

                if "embedding" not in chunk_group:
                    continue

                chunk_embedding = chunk_group["embedding"][:]
                chunk_text = chunk_group["text"][()].decode("utf-8")
                chunk_id = int(chunk_name.split("_")[1])

                # Cosine similarity
                similarity = np.dot(query_embedding, chunk_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                )

                results.append((doc_id, chunk_id, float(similarity), chunk_text))

    # Sort by similarity (descending) and return top_k
    results.sort(key=lambda x: x[2], reverse=True)
    return results[:top_k]


# =============================================================================
# DOCUMENT QUESTIONS (LLM-generated and user queries)
# =============================================================================


def save_document_questions(doc_id: str, questions: list[DocumentQuestion]) -> bool:
    """Save multiple questions for a document (used during initial generation).

    Args:
        doc_id: Document UUID
        questions: List of questions to save

    Returns:
        True if saved, False if document not found
    """
    if not CORPUS_PATH.exists():
        return False

    with _doc_lock, h5py.File(CORPUS_PATH, "a") as f:
        if "documents" not in f:
            return False

        docs_group = f["documents"]
        if doc_id not in docs_group:
            return False

        doc_group = docs_group[doc_id]

        # Create or clear questions group
        if "questions" in doc_group:
            del doc_group["questions"]
        q_group = doc_group.create_group("questions")

        # Save each question
        for q in questions:
            q_subgroup = q_group.create_group(f"q_{q.question_id}")
            q_subgroup.create_dataset(
                "question",
                data=q.question.encode("utf-8"),
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            q_subgroup.create_dataset(
                "source",
                data=q.source.encode("utf-8"),
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            q_subgroup.create_dataset(
                "timestamp",
                data=q.timestamp.encode("utf-8"),
                dtype=h5py.string_dtype(encoding="utf-8"),
            )
            if q.answer:
                q_subgroup.create_dataset(
                    "answer",
                    data=q.answer.encode("utf-8"),
                    dtype=h5py.string_dtype(encoding="utf-8"),
                )

        f.flush()

        logger.info(
            "DOCUMENT_QUESTIONS_SAVED",
            doc_id=doc_id,
            count=len(questions),
        )

        return True


def get_document_questions(doc_id: str) -> list[DocumentQuestion] | None:
    """Get all questions for a document.

    Args:
        doc_id: Document UUID

    Returns:
        List of questions or None if document not found
    """
    if not CORPUS_PATH.exists():
        return None

    with _doc_lock, h5py.File(CORPUS_PATH, "r") as f:
        if "documents" not in f:
            return None

        docs_group = f["documents"]
        if doc_id not in docs_group:
            return None

        doc_group = docs_group[doc_id]

        if "questions" not in doc_group:
            return []  # No questions yet, but document exists

        q_group = doc_group["questions"]
        questions = []

        for q_name in sorted(q_group, key=lambda x: int(x.split("_")[1])):
            q_subgroup = q_group[q_name]

            question = q_subgroup["question"][()].decode("utf-8")
            source = q_subgroup["source"][()].decode("utf-8")
            timestamp = q_subgroup["timestamp"][()].decode("utf-8")
            answer = None
            if "answer" in q_subgroup:
                answer = q_subgroup["answer"][()].decode("utf-8")

            questions.append(
                DocumentQuestion(
                    question_id=int(q_name.split("_")[1]),
                    question=question,
                    source=source,
                    timestamp=timestamp,
                    answer=answer,
                )
            )

        return questions


def add_document_question(doc_id: str, question: DocumentQuestion) -> bool:
    """Add a single question to a document (used for accumulating user queries).

    Args:
        doc_id: Document UUID
        question: Question to add (question_id is auto-assigned)

    Returns:
        True if added, False if document not found
    """
    if not CORPUS_PATH.exists():
        return False

    with _doc_lock, h5py.File(CORPUS_PATH, "a") as f:
        if "documents" not in f:
            return False

        docs_group = f["documents"]
        if doc_id not in docs_group:
            return False

        doc_group = docs_group[doc_id]

        # Create questions group if it doesn't exist
        if "questions" not in doc_group:
            doc_group.create_group("questions")

        q_group = doc_group["questions"]

        # Find next available ID
        existing_ids = [int(k.split("_")[1]) for k in q_group.keys() if k.startswith("q_")]
        next_id = max(existing_ids, default=-1) + 1

        # Create subgroup for the new question
        q_subgroup = q_group.create_group(f"q_{next_id}")
        q_subgroup.create_dataset(
            "question",
            data=question.question.encode("utf-8"),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )
        q_subgroup.create_dataset(
            "source",
            data=question.source.encode("utf-8"),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )
        q_subgroup.create_dataset(
            "timestamp",
            data=question.timestamp.encode("utf-8"),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )
        if question.answer:
            q_subgroup.create_dataset(
                "answer",
                data=question.answer.encode("utf-8"),
                dtype=h5py.string_dtype(encoding="utf-8"),
            )

        f.flush()

        logger.debug(
            "DOCUMENT_QUESTION_ADDED",
            doc_id=doc_id,
            question_id=next_id,
            source=question.source,
        )

        return True
