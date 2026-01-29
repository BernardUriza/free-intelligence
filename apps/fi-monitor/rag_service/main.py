"""RAG Embedding Service for FI Monitor - GPU Acceleration.

Provides fast embedding generation using sentence-transformers with GPU support.
Exposes /rag/embed endpoint for FI Cloud to offload embeddings from CPU.

Architecture:
- GPU detection (CUDA/MPS) - MANDATORY by default
- Fail-hard on startup if no GPU available (override: RAG_REQUIRE_GPU=false)
- API key authentication for security
- Batch embedding support
- Health check endpoint

Author: Bernard Uriza Orozco
Created: 2026-01-16
Card: FI-API-FEAT-020 (Phase 3)
"""

from __future__ import annotations

import base64
import io
import os
import re
import sys
from contextlib import asynccontextmanager

import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

# ============================================================================
# Configuration
# ============================================================================

# Model: Same as backend for consistency
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Security: API key for authentication
RAG_API_KEY = os.getenv("RAG_API_KEY", "change-me-in-production")

# GPU Requirement: Fail-hard if no GPU (override: RAG_REQUIRE_GPU=false)
RAG_REQUIRE_GPU = os.getenv("RAG_REQUIRE_GPU", "true").lower() in ("true", "1", "yes")

# GPU Detection
def _detect_device() -> str:
    """Detect best available device (cuda > mps > cpu).

    Exits with error if no GPU found and RAG_REQUIRE_GPU=true (default).
    """
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[RAG Service] 🚀 GPU detected: {gpu_name}")
        print(f"[RAG Service] 💾 VRAM: {vram_gb:.2f} GB")
        return "cuda"
    elif torch.backends.mps.is_available():
        print("[RAG Service] 🚀 Apple Silicon GPU detected (MPS)")
        return "mps"
    else:
        if RAG_REQUIRE_GPU:
            # Fail-hard: GPU is mandatory by default
            print("\n" + "="*80)
            print("❌ ERROR: No GPU detected - RAG Service requires GPU acceleration")
            print("="*80)
            print("\n📋 DIAGNOSIS:")
            print("   • CUDA available: No")
            print("   • MPS available: No")
            print("   • CPU-only mode: Not supported (performance <20ms required)")
            print("\n🔧 SOLUTIONS:")
            print("\n   Windows (NVIDIA):")
            print("   1. Install GPU drivers: https://www.nvidia.com/Download/index.aspx")
            print("   2. Install CUDA Toolkit 12.1+: https://developer.nvidia.com/cuda-downloads")
            print("   3. Verify: nvidia-smi (should show GPU)")
            print("   4. Reinstall PyTorch with CUDA: pip install torch --index-url https://download.pytorch.org/whl/cu121")
            print("\n   macOS (Apple Silicon):")
            print("   1. Upgrade to macOS 13+ (Ventura or newer)")
            print("   2. Reinstall PyTorch: pip install --upgrade torch")
            print("   3. Verify: python -c \"import torch; print(torch.backends.mps.is_available())\"")
            print("\n   Linux (NVIDIA):")
            print("   1. Install GPU drivers: sudo apt install nvidia-driver-535")
            print("   2. Install CUDA: sudo apt install nvidia-cuda-toolkit")
            print("   3. Verify: nvidia-smi")
            print("\n🔓 OVERRIDE (Dev/Testing ONLY):")
            print("   export RAG_REQUIRE_GPU=false  # Allow CPU mode (degraded performance)")
            print("\n" + "="*80 + "\n")
            sys.exit(1)
        else:
            # Override active - allow CPU with warning
            print("[RAG Service] ⚠️ No GPU detected - RAG_REQUIRE_GPU=false override active")
            print("[RAG Service] ⚠️ Performance will be degraded (100-300ms vs 20-50ms on GPU)")
            return "cpu"


DEVICE = _detect_device()

# Global model instance (lazy loaded)
_model: SentenceTransformer | None = None

# Global storage for document chunks and embeddings
# Structure: {
#   "filename.pdf": {
#       "chunks": ["text chunk 1", "text chunk 2", ...],
#       "embeddings": np.ndarray([[...], [...], ...])
#   }
# }
_document_store: dict[str, dict] = {}


# ============================================================================
# Lifespan - Load model on startup
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown.

    Performs GPU allocation test before loading model to catch issues early.
    """
    global _model

    # GPU Allocation Test (catch driver issues, VRAM exhaustion)
    if DEVICE in ("cuda", "mps"):
        try:
            print("[RAG Service] Testing GPU memory allocation...")
            test_tensor = torch.zeros(100, 100, device=DEVICE)
            del test_tensor
            print("[RAG Service] ✅ GPU memory allocation test passed")
        except Exception as e:
            print(f"\n❌ ERROR: GPU detected but allocation failed: {e}")
            print("Possible causes:")
            print("  • GPU driver crashed")
            print("  • VRAM exhausted by another process")
            print("  • GPU in use by another application")
            print("\nTroubleshooting:")
            print("  • Restart GPU drivers")
            print("  • Close other GPU-intensive apps (games, video editing, etc.)")
            print("  • Check GPU usage: nvidia-smi (CUDA) or Activity Monitor (MPS)")
            sys.exit(1)

    print(f"[RAG Service] Loading model: {EMBEDDING_MODEL}")
    print(f"[RAG Service] Device: {DEVICE}")

    _model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)

    # Warm-up inference (first run is slow due to model loading)
    print("[RAG Service] Warming up model...")
    _ = _model.encode(["warm-up query"], convert_to_numpy=True, show_progress_bar=False)
    print(f"[RAG Service] ✅ Model ready on {DEVICE}")

    # Log GPU memory usage (CUDA only - MPS doesn't expose VRAM)
    if DEVICE == "cuda":
        allocated_mb = torch.cuda.memory_allocated(0) / (1024**2)
        reserved_mb = torch.cuda.memory_reserved(0) / (1024**2)
        print(f"[RAG Service] 💾 GPU Memory: {allocated_mb:.0f}MB allocated, {reserved_mb:.0f}MB reserved")

    yield

    # Cleanup
    print("[RAG Service] Shutting down...")
    if DEVICE == "cuda":
        torch.cuda.empty_cache()
        print("[RAG Service] ✅ GPU memory cleared")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="FI Monitor RAG Service",
    description="GPU-accelerated embedding generation for RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# 🔧 CORS configurado para permitir requests desde Tauri dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420"],  # Tauri dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class EmbedRequest(BaseModel):
    """Request for batch embedding generation."""

    texts: list[str] = Field(..., min_length=1, max_length=100, description="Texts to embed (max 100)")


class EmbedResponse(BaseModel):
    """Response with embeddings and metadata."""

    embeddings: list[list[float]] = Field(..., description="List of embeddings (384-dim each)")
    device: str = Field(..., description="Device used (cuda/mps/cpu)")
    model: str = Field(..., description="Model name")
    count: int = Field(..., description="Number of embeddings generated")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    device: str = Field(..., description="Device being used")
    gpu_name: str | None = Field(None, description="GPU name if available")
    gpu_memory_mb: float | None = Field(None, description="GPU memory allocated (MB) - CUDA only, MPS returns -1")
    model: str = Field(..., description="Model loaded")


class PDFUploadRequest(BaseModel):
    """Request for PDF upload and processing."""

    filename: str = Field(..., description="PDF filename")
    content: str = Field(..., description="PDF content as base64 string")


class PDFUploadResponse(BaseModel):
    """Response for PDF upload."""

    status: str = Field(..., description="Upload status (success/error)")
    filename: str = Field(..., description="Uploaded filename")
    chunks: int = Field(0, description="Number of chunks extracted")
    message: str = Field(..., description="Status message")


class RAGQueryRequest(BaseModel):
    """Request for RAG query."""

    query: str = Field(..., description="Question to ask")
    filename: str | None = Field(None, description="Specific PDF to query (optional, searches all if not provided)")
    top_k: int = Field(3, description="Number of top results to return")


class RAGQueryResponse(BaseModel):
    """Response for RAG query."""

    query: str = Field(..., description="Original query")
    results: list[dict] = Field(..., description="List of results with chunk text and similarity score")
    device: str = Field(..., description="Device used for search")


# ============================================================================
# Helper Functions
# ============================================================================


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes or plain text.

    Args:
        pdf_bytes: PDF file content or plain text as bytes

    Returns:
        Extracted text as string
    """
    # Try PDF extraction first
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)

        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"

        return text.strip()
    except Exception:
        # If PDF parsing fails, assume it's plain text
        try:
            return pdf_bytes.decode('utf-8').strip()
        except Exception:
            # Last resort: try latin-1 encoding
            return pdf_bytes.decode('latin-1').strip()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into semantic chunks (paragraph-aware).

    Args:
        text: Text to chunk
        chunk_size: Target size of each chunk in characters (soft limit)
        overlap: Number of characters to overlap between chunks

    Returns:
        List of text chunks (respects paragraph boundaries)
    """
    # Split by double newlines (paragraphs) first
    paragraphs = text.split('\n\n')

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If paragraph fits in current chunk, add it
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += para + "\n\n"
        else:
            # Save current chunk if not empty
            if current_chunk:
                chunks.append(current_chunk.strip())

            # If paragraph itself is too large, split it by sentences
            if len(para) > chunk_size:
                sentences = para.replace('. ', '.|').replace('? ', '?|').replace('! ', '!|').split('|')
                temp_chunk = ""
                for sent in sentences:
                    if len(temp_chunk) + len(sent) <= chunk_size:
                        temp_chunk += sent + " "
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = sent + " "
                if temp_chunk:
                    current_chunk = temp_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = para + "\n\n"

    # Add remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


# ============================================================================
# Endpoints
# ============================================================================


@app.post("/rag/embed", response_model=EmbedResponse)
async def embed_texts(
    request: EmbedRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> EmbedResponse:
    """Generate embeddings for texts with GPU acceleration.

    SECURITY: Requires API key authentication.

    Args:
        request: List of texts to embed
        x_api_key: API key (from header)

    Returns:
        Embeddings with metadata

    Example:
        curl -X POST http://localhost:11435/rag/embed \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"texts": ["hello world"]}'
    """
    # Auth check
    if x_api_key != RAG_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    if _model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded yet",
        )

    # Generate embeddings
    try:
        embeddings = _model.encode(
            request.texts,
            batch_size=32,
            convert_to_numpy=True,
            show_progress_bar=False,
            device=DEVICE,
        )

        return EmbedResponse(
            embeddings=embeddings.tolist(),
            device=DEVICE,
            model=EMBEDDING_MODEL,
            count=len(embeddings),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {e}",
        )


@app.post("/rag/upload", response_model=PDFUploadResponse)
async def upload_pdf(
    request: PDFUploadRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> PDFUploadResponse:
    """Upload and process PDF for RAG embeddings.

    SECURITY: Requires API key authentication.

    Args:
        request: PDF upload request with filename and base64 content
        x_api_key: API key (from header)

    Returns:
        Upload status with chunk count

    Example:
        curl -X POST http://localhost:11435/rag/upload \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"filename":"test.pdf","content":"base64-content"}'
    """
    # Auth check
    if x_api_key != RAG_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    if _model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded yet",
        )

    try:
        # 1. Decodificar base64
        pdf_bytes = base64.b64decode(request.content)
        print(f"[RAG Service] 📄 PDF received: {request.filename} ({len(pdf_bytes)} bytes)")

        # 2. Extraer texto del PDF
        text = extract_text_from_pdf(pdf_bytes)
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text could be extracted from PDF",
            )
        print(f"[RAG Service] ✅ Text extracted: {len(text)} characters")

        # 3. Chunking del texto (500 chars con overlap de 50)
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        print(f"[RAG Service] ✅ Text chunked: {len(chunks)} chunks")

        # 4. Generar embeddings
        embeddings = _model.encode(
            chunks,
            batch_size=32,
            convert_to_numpy=True,
            show_progress_bar=False,
            device=DEVICE,
        )
        print(f"[RAG Service] ✅ Embeddings generated: {embeddings.shape}")

        # 5. Almacenar en document store
        global _document_store
        _document_store[request.filename] = {
            "chunks": chunks,
            "embeddings": embeddings,
        }
        print(f"[RAG Service] ✅ Document stored: {request.filename}")

        return PDFUploadResponse(
            status="success",
            filename=request.filename,
            chunks=len(chunks),
            message=f"PDF processed successfully: {len(chunks)} chunks, {embeddings.shape[0]} embeddings generated"
        )

    except base64.binascii.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 content: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF processing failed: {e}",
        )


def preprocess_query(query: str) -> str:
    """Preprocess query to improve matching by removing filler words.

    Args:
        query: Raw user query

    Returns:
        Cleaned query with better semantic signal
    """
    # Remove Spanish question words (qué, cuál, cómo, etc.)
    query = re.sub(r'\b(qué|cuál|cómo|dónde|por qué|cuándo|quién)\b', '', query, flags=re.IGNORECASE)

    # Remove "es la/el" filler (common in Spanish)
    query = re.sub(r'\bes (la|el|los|las)\b', '', query, flags=re.IGNORECASE)

    # Remove "son los/las" filler
    query = re.sub(r'\bson (los|las)\b', '', query, flags=re.IGNORECASE)

    # Remove multiple spaces
    query = re.sub(r'\s+', ' ', query)

    return query.strip()


@app.post("/rag/query", response_model=RAGQueryResponse)
async def query_documents(
    request: RAGQueryRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> RAGQueryResponse:
    """Query stored documents using semantic search (with query preprocessing).

    SECURITY: Requires API key authentication.

    Args:
        request: Query request with question and optional filename filter
        x_api_key: API key (from header)

    Returns:
        Top-K most relevant chunks with similarity scores

    Example:
        curl -X POST http://localhost:11435/rag/query \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"query":"¿Cuál fue el diagnóstico?","top_k":3}'
    """
    # Auth check
    if x_api_key != RAG_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    if _model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded yet",
        )

    if not _document_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents uploaded yet. Upload a PDF first.",
        )

    try:
        # 1. Preprocess query (remove filler words for better matching)
        processed_query = preprocess_query(request.query)

        # 2. Generar embedding de la query (usar query procesada)
        query_embedding = _model.encode(
            [processed_query],
            convert_to_numpy=True,
            show_progress_bar=False,
            device=DEVICE,
        )[0]  # Get first (and only) embedding

        # 2. Buscar en todos los documentos (o solo en el especificado)
        all_results = []

        docs_to_search = [request.filename] if request.filename else list(_document_store.keys())

        for filename in docs_to_search:
            if filename not in _document_store:
                continue

            doc_data = _document_store[filename]
            chunks = doc_data["chunks"]
            embeddings = doc_data["embeddings"]

            # 3. Calcular cosine similarity
            # Normalize vectors
            query_norm = query_embedding / np.linalg.norm(query_embedding)
            embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

            # Compute similarities
            similarities = embeddings_norm @ query_norm

            # 4. Get top-K results for this document
            top_indices = np.argsort(similarities)[::-1][:request.top_k]

            for idx in top_indices:
                all_results.append({
                    "filename": filename,
                    "chunk": chunks[idx],
                    "similarity": float(similarities[idx])
                })

        # 5. Sort all results by similarity and get top-K
        all_results.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = all_results[:request.top_k]

        print(f"[RAG Service] 🔍 Query: '{request.query}' -> {len(top_results)} results")

        return RAGQueryResponse(
            query=request.query,
            results=top_results,
            device=DEVICE,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {e}",
        )


@app.delete("/rag/documents/{filename}")
async def delete_document(
    filename: str,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> dict:
    """Delete a specific document from the store.

    Phase 3: Cleanup endpoint to remove old documents from memory.
    Prevents confusion when switching between different PDFs.
    """
    if x_api_key != RAG_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if filename not in _document_store:
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")

    del _document_store[filename]
    print(f"[RAG Service] 🗑️  Deleted document: {filename}")

    return {"status": "deleted", "filename": filename}


@app.delete("/rag/documents")
async def clear_all_documents(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> dict:
    """Clear all documents from the store.

    Phase 3: Nuclear option - wipe entire document store.
    Useful for resetting state or clearing accumulated old docs.
    """
    if x_api_key != RAG_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    count = len(_document_store)
    _document_store.clear()
    print(f"[RAG Service] 🗑️  Cleared {count} documents from store")

    return {"status": "cleared", "count": count}


@app.get("/rag/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check with GPU info.

    Public endpoint (no auth required).
    Returns GPU name and memory usage for validation.
    """
    gpu_name = None
    gpu_memory_mb = None

    if DEVICE == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory_mb = torch.cuda.memory_allocated(0) / (1024**2)
    elif DEVICE == "mps":
        gpu_name = "Apple Silicon (MPS)"
        gpu_memory_mb = -1.0  # Sentinel value - MPS doesn't expose VRAM

    return HealthResponse(
        status="ok",
        device=DEVICE,
        gpu_name=gpu_name,
        gpu_memory_mb=gpu_memory_mb,
        model=EMBEDDING_MODEL,
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",  # Listen on all interfaces (for tunnel)
        port=11435,
        log_level="info",
    )
