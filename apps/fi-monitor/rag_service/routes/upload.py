"""PDF upload endpoint."""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException, status

import state
from auth import verify_api_key
from gpu import DEVICE
from schemas import PDFUploadRequest, PDFUploadResponse
from text_processing import chunk_text, extract_text_from_pdf

router = APIRouter()


@router.post("/rag/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    request: PDFUploadRequest,
    _auth: None = Depends(verify_api_key),
) -> PDFUploadResponse:
    """Upload and process PDF for RAG embeddings.

    SECURITY: Requires API key authentication.

    Args:
        request: PDF upload request with filename and base64 content

    Returns:
        Upload status with chunk count

    Example:
        curl -X POST http://localhost:11435/rag/upload \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"filename":"test.pdf","content":"base64-content"}'
    """
    if state._model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded yet",
        )

    try:
        # 1. Decode base64
        pdf_bytes = base64.b64decode(request.content)
        print(f"[RAG Service] PDF received: {request.filename} ({len(pdf_bytes)} bytes)")

        # 2. Extract text from PDF
        text = extract_text_from_pdf(pdf_bytes)
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text could be extracted from PDF",
            )
        print(f"[RAG Service] Text extracted: {len(text)} characters")

        # 3. Chunk the text (500 chars with overlap of 50)
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        print(f"[RAG Service] Text chunked: {len(chunks)} chunks")

        # 4. Generate embeddings
        embeddings = state._model.encode(
            chunks,
            batch_size=32,
            convert_to_numpy=True,
            show_progress_bar=False,
            device=DEVICE,
        )
        print(f"[RAG Service] Embeddings generated: {embeddings.shape}")

        # 5. Store in document store
        state._document_store[request.filename] = {
            "chunks": chunks,
            "embeddings": embeddings,
        }
        print(f"[RAG Service] Document stored: {request.filename}")

        return PDFUploadResponse(
            status="success",
            filename=request.filename,
            chunks=len(chunks),
            message=f"PDF processed successfully: {len(chunks)} chunks, {embeddings.shape[0]} embeddings generated",
        )

    except base64.binascii.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 content: {e}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF processing failed: {e}",
        )
