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

import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.storage.document_repository import (
    Document,
    DocumentOrigin,
    DocumentStatus,
    create_document,
    delete_document,
    get_document,
    list_documents,
    update_document_metadata,
    update_document_status,
)

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


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(None),
    usage_instructions: str = Form(""),
    assigned_personas: str = Form(""),  # Comma-separated
    origin: str = Form("admin_upload"),
    uploaded_by: str = Form("anonymous"),
) -> DocumentUploadResponse:
    """Upload a new document to the knowledge base.

    The document will be queued for processing (text extraction + embedding).

    Supported formats: PDF, DOCX, TXT, MD, PNG, JPG
    Max size: 10 MB
    """
    # Validate file size (10 MB max)
    MAX_SIZE = 10 * 1024 * 1024
    content = await file.read()

    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is 10 MB, got {len(content) / 1024 / 1024:.1f} MB",
        )

    # Parse personas
    personas = [p.strip() for p in assigned_personas.split(",") if p.strip()]

    # Parse origin
    try:
        doc_origin = DocumentOrigin(origin)
    except ValueError:
        doc_origin = DocumentOrigin.ADMIN_UPLOAD

    # Create document
    try:
        metadata = create_document(
            content=content,
            filename=file.filename or "unknown",
            uploaded_by=uploaded_by,
            origin=doc_origin,
            title=title,
            usage_instructions=usage_instructions,
            assigned_personas=personas,
        )
    except Exception as e:
        logger.error("DOCUMENT_UPLOAD_FAILED", error=str(e))
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

    return DocumentUploadResponse(
        doc_id=metadata.doc_id,
        title=metadata.title,
        status=metadata.status.value,
        message="Document uploaded successfully. Processing queued.",
    )


@router.get("/documents", response_model=DocumentListResponse)
async def list_all_documents(
    persona: str | None = None,
    origin: str | None = None,
    document_status: str | None = None,
) -> DocumentListResponse:
    """List all documents with optional filters."""
    # Parse filters
    origin_filter = None
    if origin:
        try:
            origin_filter = DocumentOrigin(origin)
        except ValueError:
            pass

    status_filter = None
    if document_status:
        try:
            status_filter = DocumentStatus(document_status)
        except ValueError:
            pass

    documents = list_documents(
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
async def search_documents(request: DocumentSearchRequest) -> DocumentSearchResponse:
    """Search documents using semantic similarity.

    Returns chunks of text that are most relevant to the query.
    """
    from backend.storage.document_repository import search_documents_by_embedding

    # Generate query embedding
    try:
        query_embedding = await _get_embedding(request.query)
    except Exception as e:
        logger.error("EMBEDDING_GENERATION_FAILED", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {e}",
        )

    # Search
    results = search_documents_by_embedding(
        query_embedding=query_embedding,
        top_k=request.top_k,
        persona_filter=request.persona_filter,
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
    from backend.storage.document_repository import (
        DocumentChunk,
        save_document_chunks,
        save_document_text,
    )

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

        # Generate embeddings for each chunk
        chunks = []
        for i, chunk_text in enumerate(chunks_text):
            try:
                embedding = _get_embedding_sync(chunk_text)
                chunks.append(
                    DocumentChunk(
                        chunk_id=i,
                        text=chunk_text,
                        embedding=embedding,
                    )
                )
            except Exception as e:
                logger.warning("CHUNK_EMBEDDING_FAILED", chunk_id=i, error=str(e))
                chunks.append(DocumentChunk(chunk_id=i, text=chunk_text, embedding=None))

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

    except Exception as e:
        logger.error("DOCUMENT_PROCESSING_FAILED", doc_id=doc_id, error=str(e))
        update_document_status(doc_id, DocumentStatus.ERROR, str(e))


def _extract_text(doc: Document) -> str | None:
    """Extract text from document based on type."""
    from backend.storage.document_repository import DocumentType

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


def _split_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence end (.!?) in last 100 chars
            search_start = max(end - 100, start)
            for i in range(end, search_start, -1):
                if text[i] in ".!?\n":
                    end = i + 1
                    break

        chunks.append(text[start:end].strip())
        start = end - overlap

    return [c for c in chunks if c]  # Filter empty chunks


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


# Lazy-loaded embedding model
_embedding_model = None


def _get_embedding_model():
    """Get or create the embedding model (singleton)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("EMBEDDING_MODEL_LOADED", model="all-MiniLM-L6-v2")
    return _embedding_model
