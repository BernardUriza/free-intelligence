"""Knowledge Base API routes.

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

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.api.domains.aurity.knowledge_base.dependencies import get_document_service
from backend.api.domains.aurity.knowledge_base.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentUploadResponse,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
)
from backend.api.domains.aurity.knowledge_base.services import (
    FileValidator,
    TextExtractor,
)
from backend.domain.document.models import (
    DocumentMetadata,
    DocumentOrigin,
    DocumentStatus,
    DocumentType,
)
from backend.infrastructure.auth.adapters.fastapi_adapter import User, get_current_user
from backend.services.document.services.document_service import DocumentService
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Helper: Require clinic_id
# =============================================================================


def require_clinic(user: User) -> str:
    """Validate user has clinic_id assigned."""
    if not user.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no clinic assigned. Contact administrator.",
        )
    return user.clinic_id


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    specialty: str | None = Form(None),
    document_type: str = Form("other"),
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
    audit_service: DIAuditService = Depends(get_audit_service),
) -> DocumentUploadResponse:
    """Upload a new document to the knowledge base.

    The document will be automatically processed:
    1. Text extraction (PDF/DOCX -> plain text)
    2. Chunking (paragraph-aware for medical context)
    3. Embedding generation (sentence-transformers)
    4. Indexing (stored in HDF5 + vector index)

    Supported formats: PDF, DOCX, TXT, MD
    Max size: 10 MB

    Multi-Tenancy: Document assigned to current_user.clinic_id
    """
    clinic_id = require_clinic(current_user)

    # Read file content
    content = await file.read()
    filename = file.filename or "unknown"

    # Validate file
    validator = FileValidator(audit_service=audit_service)
    validator.validate(file, content, current_user.id, clinic_id)

    # Extract text
    extractor = TextExtractor(audit_service=audit_service)
    text_content = extractor.extract(file, content, current_user.id, clinic_id)

    if not text_content or not text_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo extraer texto del archivo. Verifica que no este vacio.",
        )

    # Use filename as title if not provided
    doc_title = title or filename

    # Create metadata
    metadata = DocumentMetadata(
        specialty=specialty,
        document_type=DocumentType(document_type),
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
        original_filename=filename,
    )

    try:
        doc = doc_service.upload_document(
            clinic_id=clinic_id,
            title=doc_title,
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
            clinic_id=clinic_id,
            title=doc_title,
            size=len(content),
            user=current_user.id,
        )

        return DocumentUploadResponse(
            doc_id=doc.doc_id,
            title=doc.title,
            status=doc.status.value,
            message=f"Documento '{doc_title}' subido y en procesamiento.",
        )

    except Exception as e:
        logger.error(
            "DOCUMENT_UPLOAD_ERROR",
            filename=filename,
            clinic_id=clinic_id,
            error=str(e),
        )
        audit_service.log_action(
            action="document_upload_failed",
            user_id=current_user.id,
            clinic_id=clinic_id,
            resource=filename,
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir documento: {str(e)}",
        )


@router.get("/", response_model=DocumentListResponse)
def list_documents(
    doc_status: str | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    doc_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """List documents for the current user's clinic.

    Multi-Tenancy: Only returns documents from current_user.clinic_id
    """
    clinic_id = require_clinic(current_user)

    # Parse status filter
    status_filter = None
    if doc_status:
        try:
            status_filter = DocumentStatus(doc_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {doc_status}. "
                "Valid: pending, indexing, indexed, error, archived",
            )

    documents = doc_service.list_documents(
        clinic_id=clinic_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )

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

    total = doc_service.get_document_count(clinic_id, status=status_filter)

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
    clinic_id = require_clinic(current_user)

    doc = doc_service.get_document(doc_id, clinic_id)

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
    clinic_id = require_clinic(current_user)

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

    doc = doc_service.update_document(doc_id, clinic_id, update_dict)

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found or access denied.",
        )

    logger.info(
        "DOCUMENT_UPDATED",
        doc_id=doc_id,
        clinic_id=clinic_id,
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
    clinic_id = require_clinic(current_user)

    success = doc_service.delete_document(
        doc_id, clinic_id, soft_delete=not hard_delete
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found or access denied.",
        )

    logger.info(
        "DOCUMENT_DELETED",
        doc_id=doc_id,
        clinic_id=clinic_id,
        hard_delete=hard_delete,
    )

    action = "permanently deleted" if hard_delete else "archived"
    return {"message": f"Document {doc_id} {action} successfully"}


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
    clinic_id = require_clinic(current_user)

    success = doc_service.reindex_document(doc_id, clinic_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found, access denied, or reindex failed.",
        )

    logger.info("DOCUMENT_REINDEXED", doc_id=doc_id, clinic_id=clinic_id)

    return {"message": f"Document {doc_id} queued for re-indexing"}


@router.post("/search", response_model=SearchResponse)
async def search_documents(
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
    clinic_id = require_clinic(current_user)

    results = await doc_service.search(
        query=request.query,
        clinic_id=clinic_id,
        limit=request.limit,
        min_score=request.min_score,
        document_type=request.document_type,
    )

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
        clinic_id=clinic_id,
        results=len(result_responses),
    )

    return SearchResponse(
        query=request.query,
        results=result_responses,
        total=len(result_responses),
    )
