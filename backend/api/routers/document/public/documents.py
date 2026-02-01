"""Document Upload & Knowledge Base API.

PUBLIC endpoints for document management and RAG integration.

Endpoints:
- POST   /documents/upload      - Upload a new document
- GET    /documents             - List all documents
- GET    /documents/{doc_id}    - Get document details
- PUT    /documents/{doc_id}    - Update document metadata
- DELETE /documents/{doc_id}    - Delete a document
- POST   /documents/{doc_id}/reindex - Re-process document
- POST   /documents/search      - Semantic search

Multi-Tenancy: ALL endpoints filter by current_user.clinic_id

Card: FI-API-FEAT-020
Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2025-12-08
Updated: 2026-01-29 (Document Repository Implementation)
"""

from __future__ import annotations

import io
from typing import Any

from backend.infrastructure.auth.adapters.fastapi_adapter import User, get_current_user
from backend.repositories.hdf5_document_repository import HDF5DocumentRepository
from backend.domain.document.models import (
    DocumentMetadata,
    DocumentOrigin,
    DocumentStatus,
    DocumentType,
)
from backend.services.document.services.document_service import DocumentService
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["Documents"])


# ============================================================================
# Request/Response Models
# ============================================================================


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""

    doc_id: str = Field(..., description="Unique document ID")
    title: str = Field(..., description="Document title")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Human-readable message")


class DocumentListResponse(BaseModel):
    """Response for document list."""

    documents: list[DocumentResponse]
    total: int
    page: int
    limit: int


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


class DocumentUpdateRequest(BaseModel):
    """Request to update document metadata."""

    title: str | None = None
    specialty: str | None = None
    document_type: DocumentType | None = None
    keywords: list[str] | None = None


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


# ============================================================================
# Dependencies
# ============================================================================


def get_document_service() -> DocumentService:
    """Get document service instance with HDF5 repository.

    Note: In production, this could use DI container to manage repository lifecycle.
    For now, we create repository per-request (stateless, thread-safe).
    """
    repository = HDF5DocumentRepository()
    return DocumentService(repository=repository)


# ============================================================================
# Helper Functions
# ============================================================================


def validate_file_upload(file: UploadFile, content: bytes) -> None:
    """Validate uploaded file (size, format, magic bytes).

    Args:
        file: Uploaded file metadata
        content: File binary content

    Raises:
        HTTPException: If validation fails
    """
    filename = file.filename or "unknown"

    # 1. Reject empty files
    if len(content) == 0:
        logger.error(
            "UPLOAD_REJECTED_EMPTY_FILE",
            filename=filename,
            content_type=file.content_type,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío. Por favor selecciona un archivo válido.",
        )

    # 2. Reject suspiciously small files (< 10 bytes)
    MIN_SIZE = 10
    if len(content) < MIN_SIZE:
        logger.error(
            "UPLOAD_REJECTED_TOO_SMALL",
            filename=filename,
            size_bytes=len(content),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo es demasiado pequeño ({len(content)} bytes). Mínimo {MIN_SIZE} bytes.",
        )

    # 3. Reject files that are too large (10 MB max)
    MAX_SIZE = 10 * 1024 * 1024
    if len(content) > MAX_SIZE:
        logger.error(
            "UPLOAD_REJECTED_TOO_LARGE",
            filename=filename,
            size_bytes=len(content),
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Archivo demasiado grande. Máximo 10 MB, recibido {len(content) / 1024 / 1024:.1f} MB",
        )

    # 4. Detect HTML content masquerading as other file types
    content_start = content[:100].lower()
    is_html = (
        content_start.startswith(b"<!doctype html")
        or content_start.startswith(b"<html")
        or (content_start.startswith(b"<?xml") and b"<html" in content_start)
    )
    if is_html and not filename.lower().endswith((".html", ".htm")):
        logger.error(
            "UPLOAD_REJECTED_HTML_MASQUERADE",
            filename=filename,
            actual_content_start=content[:50].decode("utf-8", errors="replace"),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de navegador: Se recibió HTML en lugar del archivo. "
            "Intenta recargar la página y subir el archivo nuevamente.",
        )

    # 5. Validate magic bytes for known file types
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    magic_checks = {
        "pdf": (b"%PDF", "PDF debe comenzar con %PDF"),
        "png": (b"\x89PNG", "PNG debe tener header válido"),
        "jpg": (b"\xff\xd8\xff", "JPEG debe tener header válido"),
        "jpeg": (b"\xff\xd8\xff", "JPEG debe tener header válido"),
        "docx": (b"PK\x03\x04", "DOCX debe ser un archivo ZIP válido"),
    }

    if ext in magic_checks:
        expected_magic, error_msg = magic_checks[ext]
        if not content.startswith(expected_magic):
            logger.error(
                "UPLOAD_REJECTED_INVALID_MAGIC_BYTES",
                filename=filename,
                ext=ext,
                expected=expected_magic.hex(),
                actual=content[:10].hex(),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Archivo corrupto: {error_msg}",
            )


def extract_text_from_file(file: UploadFile, content: bytes) -> str:
    """Extract text content from uploaded file.

    Supports: TXT, PDF, DOCX, MD

    Args:
        file: Uploaded file metadata
        content: File binary content

    Returns:
        Extracted text content

    Raises:
        HTTPException: If text extraction fails
    """
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    try:
        # Plain text files
        if ext in ("txt", "md"):
            return content.decode("utf-8")

        # PDF files
        if ext == "pdf":
            try:
                import PyPDF2
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PDF processing not available (PyPDF2 not installed)",
                )

            try:
                pdf_file = io.BytesIO(content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n\n"
                return text.strip()
            except Exception as e:
                logger.error("PDF_EXTRACTION_ERROR", filename=filename, error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No se pudo extraer texto del PDF: {str(e)}",
                )

        # DOCX files
        if ext == "docx":
            try:
                import docx
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="DOCX processing not available (python-docx not installed)",
                )

            try:
                docx_file = io.BytesIO(content)
                doc = docx.Document(docx_file)
                text = "\n\n".join([para.text for para in doc.paragraphs])
                return text.strip()
            except Exception as e:
                logger.error("DOCX_EXTRACTION_ERROR", filename=filename, error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No se pudo extraer texto del DOCX: {str(e)}",
                )

        # Unsupported format
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato no soportado: .{ext}. Formatos válidos: TXT, MD, PDF, DOCX",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("TEXT_EXTRACTION_ERROR", filename=filename, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar archivo: {str(e)}",
        )


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    specialty: str | None = Form(None),
    document_type: str = Form("other"),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    """Upload a new document to the knowledge base.

    The document will be automatically processed:
    1. Text extraction (PDF/DOCX → plain text)
    2. Chunking (paragraph-aware for medical context)
    3. Embedding generation (sentence-transformers)
    4. Indexing (stored in HDF5 + vector index)

    Supported formats: PDF, DOCX, TXT, MD
    Max size: 10 MB

    Multi-Tenancy: Document assigned to current_user.clinic_id
    """
    # Validate user has clinic_id
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no clinic assigned. Contact administrator.",
        )

    # Read file content
    content = await file.read()
    filename = file.filename or "unknown"

    # Validate file
    validate_file_upload(file, content)

    # Extract text
    text_content = extract_text_from_file(file, content)

    if not text_content or not text_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo extraer texto del archivo. Verifica que no esté vacío.",
        )

    # Use filename as title if not provided
    if not title:
        title = filename

    # Create metadata
    metadata = DocumentMetadata(
        specialty=specialty,
        document_type=DocumentType(document_type),
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
        original_filename=filename,
    )

    try:
        # Upload document (auto-indexes by default)
        doc = doc_service.upload_document(
            clinic_id=current_user.clinic_id,
            title=title,
            content=text_content,
            uploaded_by=current_user.id,
            file_content=content,
            metadata=metadata,
            origin=DocumentOrigin.API_UPLOAD,
            auto_index=True,
        )

        logger.info(
            "DOCUMENT_UPLOADED",
            doc_id=doc.doc_id,
            clinic_id=current_user.clinic_id,
            title=title,
            size=len(content),
            user=current_user.id,
        )

        return DocumentUploadResponse(
            doc_id=doc.doc_id,
            title=doc.title,
            status=doc.status.value,
            message=f"Documento '{title}' subido y en procesamiento. Se indexará automáticamente.",
        )

    except Exception as e:
        logger.error(
            "DOCUMENT_UPLOAD_ERROR",
            filename=filename,
            clinic_id=current_user.clinic_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir documento: {str(e)}",
        )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """List documents for the current user's clinic.

    Multi-Tenancy: Only returns documents from current_user.clinic_id
    """
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no clinic assigned.",
        )

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = DocumentStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Valid: pending, indexing, indexed, error, archived",
            )

    # Get documents
    documents = doc_service.list_documents(
        clinic_id=current_user.clinic_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )

    # Convert to response
    doc_responses = [
        DocumentResponse(
            doc_id=doc.doc_id,
            clinic_id=doc.clinic_id,
            title=doc.title,
            status=doc.status.value,
            origin=doc.origin.value,
            uploaded_by=doc.uploaded_by,
            uploaded_at=doc.uploaded_at.isoformat(),
            updated_at=doc.updated_at.isoformat() if doc.updated_at else None,
            num_chunks=doc.metadata.num_chunks,
            file_size_bytes=doc.metadata.file_size_bytes,
            specialty=doc.metadata.specialty,
            document_type=doc.metadata.document_type.value,
            error_message=doc.error_message,
        )
        for doc in documents
    ]

    # Get total count
    total = doc_service.get_document_count(current_user.clinic_id, status=status_filter)

    return DocumentListResponse(
        documents=doc_responses,
        total=total,
        page=skip // limit if limit > 0 else 0,
        limit=limit,
    )


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
def get_document(
    doc_id: str,
    include_content: bool = False,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentDetailResponse:
    """Get document details by ID.

    Multi-Tenancy: Only returns document if it belongs to current_user.clinic_id
    """
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no clinic assigned.",
        )

    doc = doc_service.get_document(doc_id, current_user.clinic_id)

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found or access denied.",
        )

    return DocumentDetailResponse(
        doc_id=doc.doc_id,
        clinic_id=doc.clinic_id,
        title=doc.title,
        status=doc.status.value,
        origin=doc.origin.value,
        uploaded_by=doc.uploaded_by,
        uploaded_at=doc.uploaded_at.isoformat(),
        updated_at=doc.updated_at.isoformat() if doc.updated_at else None,
        num_chunks=doc.metadata.num_chunks,
        file_size_bytes=doc.metadata.file_size_bytes,
        specialty=doc.metadata.specialty,
        document_type=doc.metadata.document_type.value,
        error_message=doc.error_message,
        content=doc.content if include_content else None,
    )


@router.put("/{doc_id}", response_model=DocumentResponse)
def update_document(
    doc_id: str,
    updates: DocumentUpdateRequest,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Update document metadata.

    Multi-Tenancy: Only updates document if it belongs to current_user.clinic_id
    """
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no clinic assigned.",
        )

    # Build updates dict
    update_dict: dict[str, Any] = {}
    if updates.title:
        update_dict["title"] = updates.title
    if updates.specialty:
        update_dict["metadata.specialty"] = updates.specialty
    if updates.document_type:
        update_dict["metadata.document_type"] = updates.document_type
    if updates.keywords:
        update_dict["metadata.keywords"] = updates.keywords

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No updates provided",
        )

    doc = doc_service.update_document(doc_id, current_user.clinic_id, update_dict)

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found or access denied.",
        )

    logger.info(
        "DOCUMENT_UPDATED",
        doc_id=doc_id,
        clinic_id=current_user.clinic_id,
        updates=list(update_dict.keys()),
    )

    return DocumentResponse(
        doc_id=doc.doc_id,
        clinic_id=doc.clinic_id,
        title=doc.title,
        status=doc.status.value,
        origin=doc.origin.value,
        uploaded_by=doc.uploaded_by,
        uploaded_at=doc.uploaded_at.isoformat(),
        updated_at=doc.updated_at.isoformat() if doc.updated_at else None,
        num_chunks=doc.metadata.num_chunks,
        file_size_bytes=doc.metadata.file_size_bytes,
        specialty=doc.metadata.specialty,
        document_type=doc.metadata.document_type.value,
        error_message=doc.error_message,
    )


@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    hard_delete: bool = False,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
) -> dict[str, str]:
    """Delete a document.

    By default, soft-deletes (marks as ARCHIVED).
    Use hard_delete=true to permanently remove.

    Multi-Tenancy: Only deletes document if it belongs to current_user.clinic_id
    """
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no clinic assigned.",
        )

    success = doc_service.delete_document(
        doc_id, current_user.clinic_id, soft_delete=not hard_delete
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found or access denied.",
        )

    logger.info(
        "DOCUMENT_DELETED",
        doc_id=doc_id,
        clinic_id=current_user.clinic_id,
        hard_delete=hard_delete,
    )

    return {
        "message": f"Document {doc_id} {'permanently deleted' if hard_delete else 'archived'} successfully"
    }


@router.post("/{doc_id}/reindex")
def reindex_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
) -> dict[str, str]:
    """Re-index a document (re-chunk + re-embed).

    Useful when:
    - Embedding model upgraded
    - Chunking strategy changed
    - Document failed to index initially

    Multi-Tenancy: Only reindexes document if it belongs to current_user.clinic_id
    """
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no clinic assigned.",
        )

    success = doc_service.reindex_document(doc_id, current_user.clinic_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found, access denied, or reindex failed.",
        )

    logger.info(
        "DOCUMENT_REINDEXED",
        doc_id=doc_id,
        clinic_id=current_user.clinic_id,
    )

    return {"message": f"Document {doc_id} queued for re-indexing"}


@router.post("/search", response_model=SearchResponse)
def search_documents(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
) -> SearchResponse:
    """Semantic search across documents.

    Uses natural language queries to find relevant document chunks.

    Examples:
    - "diabetes treatment guidelines"
    - "hypertension medications"
    - "covid-19 diagnostic criteria"

    Multi-Tenancy: Only searches documents in current_user.clinic_id
    """
    if not current_user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no clinic assigned.",
        )

    # Search
    results = doc_service.search(
        query=request.query,
        clinic_id=current_user.clinic_id,
        limit=request.limit,
        min_score=request.min_score,
        document_type=request.document_type,
    )

    # Convert to response
    result_responses = [
        SearchResultResponse(
            doc_id=result.doc_id,
            title=result.title,
            chunk_text=result.chunk_text,
            score=result.score,
            page_num=result.page_num,
            document_type=result.document_type.value,
            specialty=result.specialty,
        )
        for result in results
    ]

    logger.info(
        "SEARCH_COMPLETED",
        query=request.query[:50],
        clinic_id=current_user.clinic_id,
        results=len(result_responses),
    )

    return SearchResponse(
        query=request.query,
        results=result_responses,
        total=len(result_responses),
    )


__all__ = ["router"]
