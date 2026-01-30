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

Card: FI-API-FEAT-020
Author: Bernard Uriza Orozco
Created: 2025-12-08
"""

from __future__ import annotations
from backend.container import get_container


import asyncio
import contextlib
import json
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

from backend.infrastructure.auth.adapters.fastapi_adapter import User, get_current_user
from backend.utils.common.logging.logger import get_logger
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

# ============================================================================
# CRITICAL: Document Repository NOT IMPLEMENTED
# ============================================================================
# TODO(document-repository): Implement complete document repository layer
#
# Required Components (Estimated: 8-10 hours):
# 1. Domain Models:
#    - Document (dataclass): doc_id, title, content, metadata
#    - DocumentOrigin (enum): ADMIN_UPLOAD, API_UPLOAD, EMAIL_IMPORT
#    - DocumentStatus (enum): PENDING, INDEXED, ERROR
#    - DocumentChunk (dataclass): chunk_id, text, embedding
#
# 2. Repository Interface (IDocumentRepository):
#    - create_document(content, metadata) -> Document
#    - get_document(doc_id, include_content=False) -> Document | None
#    - list_documents(status_filter=None, persona_filter=None) -> list[Document]
#    - update_document_metadata(doc_id, **updates) -> Document | None
#    - update_document_status(doc_id, status) -> bool
#    - delete_document(doc_id) -> bool
#    - save_document_text(doc_id, extracted_text) -> bool
#    - save_document_chunks(doc_id, chunks: list[DocumentChunk]) -> bool
#    - search_documents_by_embedding(query_embedding, top_k, persona_filter) -> list[tuple]
#
# 3. HDF5 Implementation (HDF5DocumentRepository):
#    - Schema: /documents/{doc_id}/
#      - content (bytes dataset)
#      - metadata (JSON attrs)
#      - text (string dataset)
#      - chunks/{chunk_id} (embedding + text datasets)
#    - Multi-tenancy: Filter by clinic_id in queries
#    - Semantic search: Cosine similarity on embeddings
#
# 4. FastAPI Dependencies:
#    - get_document_repository() -> IDocumentRepository
#    - Inject into all endpoints below
#
# 5. Integration:
#    - Replace direct function calls with repository.method() calls
#    - Add clinic_id filtering (multi-tenancy)
#    - Update tests to use repository mocks
#
# Status: ALL ENDPOINTS BELOW ARE BROKEN (functions don't exist)
# Priority: Medium (Knowledge Base feature not critical for pilot)
# Alternative: Use external document storage (S3 + Pinecone/Qdrant) instead of HDF5
# ============================================================================

logger = get_logger(__name__)
router = APIRouter()

# Thread pool for async document processing
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="doc_processor")


# ============================================================================
# Request/Response Models
# ============================================================================


class DocumentUploadResponse(BaseModel):
    """Response after uploading a document."""

    doc_id: str = Field(..., description="Unique document ID")
    title: str = Field(..., description="Document title")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")


class DocumentListResponse(BaseModel):
    """Response for listing documents."""

    documents: list[dict] = Field(..., description="List of document metadata")
    total: int = Field(..., description="Total number of documents")


class DocumentDetailResponse(BaseModel):
    """Response for document details."""

    doc_id: str
    title: str
    filename: str | None = None  # Original filename
    doc_type: str
    origin: str
    uploaded_by: str
    uploaded_at: str
    usage_instructions: str
    assigned_personas: list[str]
    status: str
    size_bytes: int
    sha256: str
    chunks_count: int
    error_message: str | None = None
    text: str | None = None  # Extracted text (optional)


class DocumentUpdateRequest(BaseModel):
    """Request to update document metadata."""

    title: str | None = Field(None, description="New title")
    usage_instructions: str | None = Field(None, description="New usage instructions")
    assigned_personas: list[str] | None = Field(None, description="New persona assignments")


class DocumentSearchRequest(BaseModel):
    """Request for semantic search."""

    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")
    persona_filter: str | None = Field(None, description="Filter by persona")


class DocumentSearchResult(BaseModel):
    """A single search result."""

    doc_id: str
    chunk_id: int
    similarity: float
    text: str
    title: str
    usage_instructions: str


class DocumentSearchResponse(BaseModel):
    """Response for semantic search."""

    results: list[DocumentSearchResult]
    total: int


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/documents/upload", response_model=DocumentDetailResponse)
async def upload_document(
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    title: str = Form(None),
    usage_instructions: str = Form(""),
    assigned_personas: str = Form(""),  # Comma-separated or JSON array
    origin: str = Form("admin_upload"),
) -> DocumentDetailResponse:
    """Upload a new document to the knowledge base.

    The document will be queued for processing (text extraction + embedding).

    Supported formats: PDF, DOCX, TXT, MD, PNG, JPG
    Max size: 10 MB
    """
    # Validate file size (10 MB max)
    MAX_SIZE = 10 * 1024 * 1024
    MIN_SIZE = 10  # Minimum 10 bytes - empty files are rejected
    content = await file.read()
    filename = file.filename or "unknown"

    # ==========================================================================
    # STRICT CONTENT VALIDATION - Fail loudly on corrupted/empty uploads
    # ==========================================================================

    # 1. Reject empty files
    if len(content) == 0:
        logger.error(
            "UPLOAD_REJECTED_EMPTY_FILE",
            filename=filename,
            content_type=file.content_type,
            reason="File content is empty (0 bytes)",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío. Por favor selecciona un archivo válido.",
        )

    # 2. Reject suspiciously small files
    if len(content) < MIN_SIZE:
        logger.error(
            "UPLOAD_REJECTED_TOO_SMALL",
            filename=filename,
            size_bytes=len(content),
            min_required=MIN_SIZE,
            reason="File too small to be valid",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo es demasiado pequeño ({len(content)} bytes). Mínimo {MIN_SIZE} bytes.",
        )

    # 3. Reject files that are too large
    if len(content) > MAX_SIZE:
        logger.error(
            "UPLOAD_REJECTED_TOO_LARGE",
            filename=filename,
            size_bytes=len(content),
            max_allowed=MAX_SIZE,
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Archivo demasiado grande. Máximo 10 MB, recibido {len(content) / 1024 / 1024:.1f} MB",
        )

    # 4. Detect HTML content masquerading as other file types (common browser bug)
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
            declared_type=file.content_type,
            actual_content_start=content[:50].decode("utf-8", errors="replace"),
            reason="Browser sent HTML instead of actual file content",
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
                "UPLOAD_REJECTED_INVALID_MAGIC",
                filename=filename,
                extension=ext,
                expected_magic=expected_magic.hex(),
                actual_magic=content[:10].hex(),
                actual_start=content[:20].decode("utf-8", errors="replace"),
                reason=error_msg,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El archivo no es un {ext.upper()} válido. {error_msg}. "
                f"Contenido recibido: '{content[:30].decode('utf-8', errors='replace')}...'",
            )

    # Log successful validation
    logger.info(
        "UPLOAD_CONTENT_VALIDATED",
        filename=filename,
        size_bytes=len(content),
        extension=ext,
        content_type=file.content_type,
        magic_bytes=content[:8].hex(),
    )

    # Parse personas (supports JSON array or comma-separated)
    personas = []
    if assigned_personas:
        assigned_personas = assigned_personas.strip()
        # Check if it's a JSON array
        if assigned_personas.startswith("["):
            try:
                personas = json.loads(assigned_personas)
                if not isinstance(personas, list):
                    personas = [personas]
            except json.JSONDecodeError:
                personas = [p.strip() for p in assigned_personas.split(",") if p.strip()]
        else:
            # Comma-separated format
            personas = [p.strip() for p in assigned_personas.split(",") if p.strip()]

    # Parse origin
    try:
        doc_origin = DocumentOrigin(origin)
    except ValueError:
        doc_origin = DocumentOrigin.ADMIN_UPLOAD

    # Create document with user isolation
    # Multi-tenancy: Extract clinic_id from Auth0 app_metadata
    # Falls back to empty string if clinic_id not set (backward compatibility)
    clinic_id = current_user.clinic_id or ""

    try:
        metadata = create_document(
            content=content,
            filename=file.filename or "unknown",
            uploaded_by=current_user.email,  # Legacy field for backward compat
            owner_user_id=current_user.user_id,  # SECURITY: Auth0 sub claim
            clinic_id=clinic_id,
            origin=doc_origin,
            title=title,
            usage_instructions=usage_instructions,
            assigned_personas=personas,
        )
    except Exception as e:
        logger.error("DOCUMENT_UPLOAD_FAILED", error=str(e), user_id=current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {e}",
        )

    # Queue async processing
    asyncio.get_event_loop().run_in_executor(
        _executor,
        _process_document,
        metadata.doc_id,
    )

    # Return full document metadata for frontend to use immediately
    return DocumentDetailResponse(
        doc_id=metadata.doc_id,
        title=metadata.title,
        filename=file.filename,  # Use original filename from upload
        doc_type=metadata.doc_type.value,
        origin=metadata.origin.value,
        uploaded_by=metadata.uploaded_by,
        uploaded_at=metadata.uploaded_at,
        usage_instructions=metadata.usage_instructions,
        assigned_personas=metadata.assigned_personas,
        status=metadata.status.value,
        size_bytes=metadata.size_bytes,
        sha256=metadata.sha256,
        chunks_count=metadata.chunks_count,
        error_message=metadata.error_message,
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_all_documents(
    current_user: User = Depends(get_current_user),
    persona: str | None = None,
    origin: str | None = None,
    document_status: str | None = None,
) -> DocumentListResponse:
    """List documents accessible to current user (HIPAA isolation).

    SECURITY: Only returns documents owned by the user or explicitly shared with them.
    """
    # Parse filters
    origin_filter = None
    if origin:
        with contextlib.suppress(ValueError):
            origin_filter = DocumentOrigin(origin)

    status_filter = None
    if document_status:
        with contextlib.suppress(ValueError):
            status_filter = DocumentStatus(document_status)

    # CRITICAL: Pass user_id for access control (HIPAA compliance)
    documents = list_documents(
        user_id=current_user.user_id,
        persona_filter=persona,
        origin_filter=origin_filter,
        status_filter=status_filter,
    )

    return DocumentListResponse(
        documents=[d.to_dict() for d in documents],
        total=len(documents),
    )


@router.get("/documents/{doc_id}", response_model=DocumentDetailResponse)
async def get_document_details(
    doc_id: str,
    include_text: bool = False,
) -> DocumentDetailResponse:
    """Get document details by ID."""
    doc = get_document(doc_id, include_content=False)

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {doc_id}",
        )

    return DocumentDetailResponse(
        doc_id=doc.metadata.doc_id,
        title=doc.metadata.title,
        filename=None,  # Not stored in metadata, optional field
        doc_type=doc.metadata.doc_type.value,
        origin=doc.metadata.origin.value,
        uploaded_by=doc.metadata.uploaded_by,
        uploaded_at=doc.metadata.uploaded_at,
        usage_instructions=doc.metadata.usage_instructions,
        assigned_personas=doc.metadata.assigned_personas,
        status=doc.metadata.status.value,
        size_bytes=doc.metadata.size_bytes,
        sha256=doc.metadata.sha256,
        chunks_count=doc.metadata.chunks_count,
        error_message=doc.metadata.error_message,
        text=doc.text if include_text else None,
    )


@router.put("/documents/{doc_id}", response_model=DocumentDetailResponse)
async def update_document(
    doc_id: str,
    request: DocumentUpdateRequest,
) -> DocumentDetailResponse:
    """Update document metadata (title, instructions, personas)."""
    updated = update_document_metadata(
        doc_id=doc_id,
        title=request.title,
        usage_instructions=request.usage_instructions,
        assigned_personas=request.assigned_personas,
    )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {doc_id}",
        )

    # Re-fetch full document
    doc = get_document(doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return DocumentDetailResponse(
        doc_id=doc.metadata.doc_id,
        title=doc.metadata.title,
        filename=None,  # Not stored in metadata, optional field
        doc_type=doc.metadata.doc_type.value,
        origin=doc.metadata.origin.value,
        uploaded_by=doc.metadata.uploaded_by,
        uploaded_at=doc.metadata.uploaded_at,
        usage_instructions=doc.metadata.usage_instructions,
        assigned_personas=doc.metadata.assigned_personas,
        status=doc.metadata.status.value,
        size_bytes=doc.metadata.size_bytes,
        sha256=doc.metadata.sha256,
        chunks_count=doc.metadata.chunks_count,
        error_message=doc.metadata.error_message,
    )


@router.delete("/documents/{doc_id}")
async def remove_document(doc_id: str) -> dict:
    """Delete a document from the knowledge base."""
    deleted = delete_document(doc_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {doc_id}",
        )

    return {"success": True, "message": f"Document {doc_id} deleted"}


@router.post("/documents/{doc_id}/reindex")
async def reindex_document(doc_id: str) -> dict:
    """Re-process a document (extract text + generate embeddings)."""
    doc = get_document(doc_id)

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {doc_id}",
        )

    # Reset status and queue processing
    update_document_status(doc_id, DocumentStatus.PENDING)

    asyncio.get_event_loop().run_in_executor(
        _executor,
        _process_document,
        doc_id,
    )

    return {"success": True, "message": "Re-indexing queued", "doc_id": doc_id}


@router.post("/documents/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    current_user: User = Depends(get_current_user),
) -> DocumentSearchResponse:
    """Search documents using semantic similarity (HIPAA isolation).

    SECURITY: Only searches documents owned by the user or explicitly shared with them.

    Returns chunks of text that are most relevant to the query.
    """
    # FIXME: Broken import - search_documents_by_embedding
    # Use document repository from DI container

    # Generate query embedding
    try:
        query_embedding = await _get_embedding(request.query)
    except Exception as e:
        logger.error("EMBEDDING_GENERATION_FAILED", error=str(e), user_id=current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {e}",
        )

    # CRITICAL: Search with user_id for access control (HIPAA compliance)
    results = search_documents_by_embedding(
        query_embedding=query_embedding,
        user_id=current_user.user_id,
        top_k=request.top_k,
        persona_filter=request.persona_filter,
    )

    logger.info(
        "DOCUMENT_SEARCH_EXECUTED",
        user_id=current_user.user_id,
        query_length=len(request.query),
        results_count=len(results),
    )

    # Enrich with document metadata
    enriched_results = []
    for doc_id, chunk_id, similarity, text in results:
        doc = get_document(doc_id)
        if doc:
            enriched_results.append(
                DocumentSearchResult(
                    doc_id=doc_id,
                    chunk_id=chunk_id,
                    similarity=similarity,
                    text=text,
                    title=doc.metadata.title,
                    usage_instructions=doc.metadata.usage_instructions,
                )
            )

    return DocumentSearchResponse(
        results=enriched_results,
        total=len(enriched_results),
    )


# ============================================================================
# Processing Functions
# ============================================================================


def _process_document(doc_id: str) -> None:
    """Process a document: extract text and generate embeddings.

    This runs in a thread pool worker.
    """
    # FIXME: Broken imports - DocumentChunk, save_document_chunks, save_document_text

    logger.info("DOCUMENT_PROCESSING_STARTED", doc_id=doc_id)

    try:
        # Update status to processing
        update_document_status(doc_id, DocumentStatus.PROCESSING)

        # Get document with content
        doc = get_document(doc_id, include_content=True)
        if doc is None:
            logger.error("DOCUMENT_NOT_FOUND", doc_id=doc_id)
            return

        # Extract text based on document type
        text = _extract_text(doc)

        if not text:
            update_document_status(doc_id, DocumentStatus.ERROR, "Failed to extract text")
            return

        # Save extracted text
        save_document_text(doc_id, text)

        # Split into chunks
        chunks_text = _split_text(text)

        # Generate embeddings for all chunks in batch (10-50x faster)
        try:
            model = _get_embedding_model()
            embeddings = model.encode(
                chunks_text,
                batch_size=32,
                convert_to_numpy=True,
                show_progress_bar=False,  # Avoid clutter in logs
            )
            chunks = [
                DocumentChunk(chunk_id=i, text=text, embedding=emb)
                for i, (text, emb) in enumerate(zip(chunks_text, embeddings, strict=True))
            ]
            logger.info("BATCH_EMBEDDING_SUCCESS", num_chunks=len(chunks))
        except RuntimeError as e:
            # CUDA OOM or driver error - fallback to CPU
            if "CUDA" in str(e) or "out of memory" in str(e).lower():
                import torch

                logger.warning(
                    "CUDA_OOM_FALLBACK",
                    error=str(e),
                    action="retrying on CPU",
                )
                torch.cuda.empty_cache()  # Clear GPU memory

                # Retry on CPU
                try:
                    model = _get_embedding_model()
                    # Force CPU device
                    model = model.to("cpu")
                    embeddings = model.encode(
                        chunks_text,
                        batch_size=16,  # Smaller batch for CPU
                        convert_to_numpy=True,
                        show_progress_bar=False,
                    )
                    chunks = [
                        DocumentChunk(chunk_id=i, text=text, embedding=emb)
                        for i, (text, emb) in enumerate(zip(chunks_text, embeddings, strict=True))
                    ]
                    logger.info("CPU_FALLBACK_SUCCESS", num_chunks=len(chunks))
                except Exception as cpu_error:
                    logger.error("CPU_FALLBACK_FAILED", error=str(cpu_error))
                    chunks = [
                        DocumentChunk(chunk_id=i, text=text, embedding=None)
                        for i, text in enumerate(chunks_text)
                    ]
            else:
                # Non-CUDA error
                logger.error("BATCH_EMBEDDING_FAILED", error=str(e))
                chunks = [
                    DocumentChunk(chunk_id=i, text=text, embedding=None)
                    for i, text in enumerate(chunks_text)
                ]
        except Exception as e:
            logger.error("BATCH_EMBEDDING_FAILED", error=str(e))
            # Fallback: create chunks without embeddings
            chunks = [
                DocumentChunk(chunk_id=i, text=text, embedding=None)
                for i, text in enumerate(chunks_text)
            ]

        # Save chunks
        save_document_chunks(doc_id, chunks)

        # Update status to indexed
        update_document_status(doc_id, DocumentStatus.INDEXED)

        logger.info(
            "DOCUMENT_PROCESSING_COMPLETED",
            doc_id=doc_id,
            text_length=len(text),
            chunks_count=len(chunks),
        )

        # =====================================================================
        # POST-STEP: Generate initial questions using RAG (tests the embedding)
        # =====================================================================
        try:
            questions_text = _generate_initial_questions_via_rag(doc_id)

            if questions_text:
                from datetime import UTC, datetime

                # FIXME: Broken imports - DocumentQuestion, save_document_questions

                questions = [
                    DocumentQuestion(
                        question_id=i,
                        question=q,
                        source="llm_initial",
                        timestamp=datetime.now(UTC).isoformat(),
                    )
                    for i, q in enumerate(questions_text)
                ]
                save_document_questions(doc_id, questions)
                logger.info(
                    "DOCUMENT_QUESTIONS_GENERATED",
                    doc_id=doc_id,
                    count=len(questions),
                )
        except Exception as qe:
            logger.warning(
                "QUESTION_GENERATION_FAILED",
                doc_id=doc_id,
                error=str(qe),
            )
            # Non-fatal: document already indexed successfully

    except Exception as e:
        logger.error("DOCUMENT_PROCESSING_FAILED", doc_id=doc_id, error=str(e))
        update_document_status(doc_id, DocumentStatus.ERROR, str(e))


def _extract_text(doc: Document) -> str | None:
    """Extract text from document based on type."""
    # FIXME: Broken import - DocumentType

    if doc.content is None:
        return None

    doc_type = doc.metadata.doc_type

    try:
        if doc_type == DocumentType.TXT or doc_type == DocumentType.MARKDOWN:
            return doc.content.decode("utf-8")

        elif doc_type == DocumentType.PDF:
            return _extract_pdf_text(doc.content)

        elif doc_type == DocumentType.DOCX:
            return _extract_docx_text(doc.content)

        elif doc_type == DocumentType.IMAGE:
            return _extract_image_text(doc.content)

        else:
            # Try as plain text
            return doc.content.decode("utf-8", errors="ignore")

    except Exception as e:
        logger.error("TEXT_EXTRACTION_FAILED", doc_type=doc_type.value, error=str(e))
        return None


def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF using pdfplumber or PyPDF2."""
    try:
        import io

        import pdfplumber

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n\n".join(text_parts)
    except ImportError:
        # Fallback to PyPDF2
        try:
            import io

            from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(content))
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text())
            return "\n\n".join(text_parts)
        except ImportError:
            error_msg = "PDF extraction requires 'pdfplumber' or 'PyPDF2'. Install with: pip install pdfplumber"
            logger.error("PDF_EXTRACTION_LIBS_MISSING", fix=error_msg)
            raise ImportError(error_msg)


def _extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        import io

        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(content))
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n\n".join(text_parts)
    except ImportError:
        error_msg = "DOCX extraction requires 'python-docx'. Install with: pip install python-docx"
        logger.error("DOCX_EXTRACTION_LIB_MISSING", fix=error_msg)
        raise ImportError(error_msg)


def _extract_image_text(content: bytes) -> str:
    """Extract text from image using OCR (Tesseract)."""
    try:
        import io

        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image, lang="spa+eng")
        return text
    except ImportError as e:
        missing_lib = "pytesseract" if "pytesseract" in str(e) else "Pillow"
        error_msg = "OCR extraction requires 'pytesseract' and 'Pillow'. Install with: pip install pytesseract Pillow (and install Tesseract OCR engine)"
        logger.error("OCR_LIBS_MISSING", fix=error_msg, missing=missing_lib)
        raise ImportError(error_msg)
    except Exception as e:
        logger.error("OCR_FAILED", error=str(e))
        raise


def _split_text(text: str, chunk_size_tokens: int = 256, overlap_tokens: int = 50) -> list[str]:
    """Split text into overlapping chunks based on tokens (not characters).

    Args:
        text: Input text to split
        chunk_size_tokens: Maximum tokens per chunk (default: 256 tokens ≈ 512 chars)
        overlap_tokens: Overlap between chunks (default: 50 tokens)

    Returns:
        List of text chunks
    """
    try:
        from transformers import AutoTokenizer

        # Use same tokenizer as embedding model for consistency
        tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

        # Tokenize entire text
        tokens = tokenizer.encode(text, add_special_tokens=False)

        # If text is short enough, return as-is
        if len(tokens) <= chunk_size_tokens:
            return [text]

        chunks = []
        start_token = 0

        while start_token < len(tokens):
            end_token = start_token + chunk_size_tokens

            # Get chunk tokens
            chunk_tokens = tokens[start_token:end_token]

            # Decode back to text
            chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True).strip()

            if chunk_text:  # Only add non-empty chunks
                chunks.append(chunk_text)

            # Move start with overlap
            start_token = end_token - overlap_tokens

        return chunks

    except Exception as e:
        logger.warning(
            "TOKEN_CHUNKING_FAILED",
            error=str(e),
            fallback="using character-based chunking",
        )
        # Fallback to character-based chunking (old method)
        chunk_size_chars = chunk_size_tokens * 2  # Rough approximation
        overlap_chars = overlap_tokens * 2

        if len(text) <= chunk_size_chars:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size_chars

            # Try to break at sentence boundary
            if end < len(text):
                search_start = max(end - 100, start)
                for i in range(end, search_start, -1):
                    if text[i] in ".!?\n":
                        end = i + 1
                        break

            chunks.append(text[start:end].strip())
            start = end - overlap_chars

        return [c for c in chunks if c]


async def _get_embedding(text: str) -> np.ndarray:
    """Generate embedding for text (async wrapper)."""
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _get_embedding_sync, text)


def _get_embedding_sync(text: str) -> np.ndarray:
    """Generate embedding for text using sentence-transformers."""
    import numpy as np

    try:
        from sentence_transformers import SentenceTransformer

        # Use cached model (loaded once)
        model = _get_embedding_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding
    except ImportError:
        logger.warning("SENTENCE_TRANSFORMERS_MISSING", msg="Install sentence-transformers")
        # Return zero vector as fallback
        return np.zeros(384, dtype=np.float32)


# Lazy-loaded embedding model (thread-safe singleton)
_embedding_model = None
_embedding_model_lock = __import__("threading").Lock()


def _get_embedding_model():
    """Get or create the embedding model (thread-safe singleton)."""
    global _embedding_model
    # Double-checked locking pattern for performance
    if _embedding_model is None:
        with _embedding_model_lock:
            # Check again inside lock (another thread may have initialized it)
            if _embedding_model is None:
                import torch
                from sentence_transformers import SentenceTransformer

                # Use GPU if available (leverages CUDA libraries like cuBLAS, cuDNN)
                device = "cuda" if torch.cuda.is_available() else "cpu"
                _embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
                logger.info(
                    "EMBEDDING_MODEL_LOADED",
                    model="all-MiniLM-L6-v2",
                    device=device,
                    gpu_available=torch.cuda.is_available(),
                )
    return _embedding_model


# ============================================================================
# Question Generation (POST-STEP after indexing)
# ============================================================================


def _load_question_prompt() -> str:
    """Load question generation prompt from fi_prompts."""
    from backend.utils.prompts.yaml_provider import YAMLPromptProvider

    provider = YAMLPromptProvider(yaml_dir="backend/src/fi_prompts/yaml_presets")
    prompt = provider.get_yaml_system_prompt("question_generator")
    if not prompt:
        raise ValueError("question_generator prompt not found")
    return prompt


def _generate_initial_questions_via_rag(doc_id: str) -> list[str]:
    """Generate initial questions using RAG on the freshly indexed document.

    This tests that the embedding works correctly by searching within
    the specific document and using the LLM to generate questions.

    Args:
        doc_id: Document UUID (must be indexed)

    Returns:
        List of 3 questions (or empty if generation fails)
    """
    import json

    # FIXME: Broken import - search_documents_by_embedding

    # 1. Get document to extract owner_user_id for security
    doc = get_document(doc_id)
    if not doc:
        logger.warning("RAG_DOCUMENT_NOT_FOUND", doc_id=doc_id)
        return []
    owner_user_id = doc.metadata.owner_user_id

    # 2. Generate embedding for a generic query
    query = "¿Cuáles son los temas principales y puntos clave de este documento?"
    query_embedding = _get_embedding_sync(query)

    # 3. Search ONLY within this document (with owner's permissions)
    results = search_documents_by_embedding(
        query_embedding=query_embedding,
        user_id=owner_user_id,  # SECURITY: Use document owner's ID
        top_k=5,
        doc_filter=doc_id,  # Filter by specific document
    )

    if not results:
        logger.warning("RAG_NO_CHUNKS_FOUND", doc_id=doc_id)
        return []

    # 3. Get document metadata for context
    doc = get_document(doc_id)
    doc_title = doc.metadata.title if doc else "Documento"

    # 4. Format RAG context
    rag_parts = []
    for i, (_, _chunk_id, similarity, chunk_text) in enumerate(results):
        rag_parts.append(
            f"### Fragmento {i + 1} (Relevancia: {similarity * 100:.0f}%)\n"
            f"**Fuente:** {doc_title}\n"
            f"**Contenido:** {chunk_text}"
        )
    rag_context = "\n\n---\n\n".join(rag_parts)

    # 5. Call LLM to generate questions
    content = ""  # Initialize for fallback parsing
    try:
        from backend.providers.llm import llm_generate

        system_prompt = _load_question_prompt()
        prompt = f"{system_prompt}\n\nDOCUMENTO:\n{rag_context}"

        response = llm_generate(
            prompt=prompt,
            model="qwen3:1.7b",
            temperature=0.5,  # Lower for more consistent output
            max_tokens=1024,  # More space for 3 questions
            enable_thinking=True,  # Required for Ollama to return content
        )

        content = response.content.strip()

        # Log raw LLM response for debugging
        logger.info(
            "LLM_QUESTION_RESPONSE_RAW",
            doc_id=doc_id,
            content_length=len(content),
            content_preview=content[:500] if content else "(empty)",
        )

        # 6. Parse JSON response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = content[start:end]
            data = json.loads(json_str)
            questions = data.get("questions", [])[:3]
            logger.info(
                "LLM_QUESTIONS_PARSED",
                doc_id=doc_id,
                count=len(questions),
                questions=questions,
            )
            return questions
        else:
            # No JSON found - try fallback
            logger.warning(
                "LLM_QUESTION_NO_JSON_FOUND",
                doc_id=doc_id,
                content_preview=content[:200] if content else "(empty)",
            )
            # Fall through to fallback parsing below

    except json.JSONDecodeError as jde:
        logger.warning(
            "LLM_QUESTION_JSON_PARSE_ERROR",
            doc_id=doc_id,
            error=str(jde),
        )

    except Exception as e:
        logger.warning("LLM_QUESTION_GENERATION_FAILED", doc_id=doc_id, error=str(e))
        return []

    # Fallback: parse as numbered text (try if JSON failed or wasn't found)
    try:
        if content:
            lines = content.split("\n")
            questions = []
            for line in lines:
                line = line.strip()
                # Match lines starting with number or bullet
                if line and (line[0].isdigit() or line.startswith("¿")):
                    # Remove numbering like "1." or "- "
                    q = line.split(".", 1)[-1].strip() if line[0].isdigit() else line
                    if q and len(q) > 10:  # Minimum question length
                        questions.append(q)
            if questions:
                logger.info(
                    "LLM_QUESTIONS_PARSED_FALLBACK",
                    doc_id=doc_id,
                    count=len(questions),
                    questions=questions[:3],
                )
                return questions[:3]

        logger.warning(
            "LLM_QUESTION_FALLBACK_FAILED",
            doc_id=doc_id,
            reason="No questions extracted from response",
        )
    except Exception as fe:
        logger.warning(
            "LLM_QUESTION_FALLBACK_ERROR",
            doc_id=doc_id,
            error=str(fe),
        )

    return []


# ============================================================================
# Question Endpoints
# ============================================================================


class DocumentQuestionResponse(BaseModel):
    """Response for a document question."""

    question_id: int
    question: str
    source: str  # "llm_initial" | "user_query"
    timestamp: str
    answer: str | None = None


@router.get("/documents/{doc_id}/questions", response_model=list[DocumentQuestionResponse])
async def get_document_questions_endpoint(doc_id: str) -> list[DocumentQuestionResponse]:
    """Get all questions for a document.

    Returns accumulated questions from:
    - LLM initial generation (source="llm_initial") - created during indexing
    - User queries via RAG (source="user_query") - accumulated during usage
    """
    # FIXME: Broken import - get_document_questions

    questions = get_document_questions(doc_id)

    if questions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )

    return [
        DocumentQuestionResponse(
            question_id=q.question_id,
            question=q.question,
            source=q.source,
            timestamp=q.timestamp,
            answer=q.answer,
        )
        for q in questions
    ]
