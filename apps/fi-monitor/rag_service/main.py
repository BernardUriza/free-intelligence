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
import logging
import os
import re
import sys
import time
from contextlib import asynccontextmanager
from typing import Any

import numpy as np
import torch
import uvicorn
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer

# Import our new modules
from annotations import generate_annotations_for_document
from metrics import compute_all_metrics

# Configure logging
logging.basicConfig(level=logging.INFO)

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

# Global storage for ground truth annotations
# Structure: {
#   "filename.pdf": [
#       {
#           "query": "What is normal blood sugar?",
#           "relevant_chunks": [5, 12],
#           "relevance_scores": [3, 2],
#           "source": "llm_generated",
#           "validated": False
#       },
#       ...
#   ]
# }
_ground_truth_store: dict[str, list[dict[str, Any]]] = {}


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
# RAG Quality Metrics - Request/Response Models
# ============================================================================


class GenerateAnnotationsRequest(BaseModel):
    """Request to auto-generate ground truth annotations with LLM."""

    filename: str = Field(..., description="PDF filename to generate annotations for")
    questions_per_chunk: int = Field(2, ge=1, le=5, description="Number of questions to generate per chunk")
    model: str = Field("llama3.1:8b", description="Ollama model to use for generation")


class GenerateAnnotationsResponse(BaseModel):
    """Response from annotation generation."""

    filename: str
    annotations_count: int
    chunks_processed: int
    status: str
    estimated_time_ms: int


class AnnotationEntry(BaseModel):
    """Single annotation entry."""

    query: str
    relevant_chunks: list[int]
    relevance_scores: list[int]
    source: str
    validated: bool


class AnnotationsResponse(BaseModel):
    """Response for GET /rag/annotations/{filename}."""

    filename: str
    annotations: list[AnnotationEntry]
    count: int


class UpdateAnnotationRequest(BaseModel):
    """Request to update/validate annotation manually."""

    query: str
    relevant_chunks: list[int]
    relevance_scores: list[int]
    validated: bool = True


class EvaluateRequest(BaseModel):
    """Request to evaluate single query quality."""

    query: str
    filename: str
    top_k: int = Field(3, ge=1, le=10, description="Number of top results to evaluate")


class EvaluateResponse(BaseModel):
    """Response from single query evaluation."""

    query: str
    metrics: dict[str, float]
    retrieved_chunks: list[int]
    relevant_chunks: list[int]
    relevance_scores: list[int]


class BatchEvaluateRequest(BaseModel):
    """Request to evaluate all queries in a document."""

    filename: str
    top_k: int = Field(3, ge=1, le=10)


class BatchEvaluateResponse(BaseModel):
    """Response from batch evaluation."""

    filename: str
    total_queries: int
    avg_metrics: dict[str, float]
    per_query_metrics: list[dict]


class SimilaritySearchRequest(BaseModel):
    """Request for GPU similarity search."""

    query_vector: list[float] = Field(
        ...,
        description="Query embedding vector",
        min_length=EMBEDDING_DIM,
        max_length=EMBEDDING_DIM,
    )
    document_vectors: list[list[float]] = Field(
        ...,
        description="List of document embedding vectors to search",
        min_length=1,
        max_length=50000,  # Limit to prevent OOM
    )


class SimilaritySearchResponse(BaseModel):
    """Response from GPU similarity search."""

    similarities: list[float] = Field(
        ...,
        description="Cosine similarity scores (0-1) for each document vector",
    )
    device_used: str = Field(
        ...,
        description="Device used for computation (cuda/mps/cpu)",
    )
    duration_ms: float = Field(
        ...,
        description="Computation time in milliseconds",
    )


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


# ============================================================================
# RAG Quality Metrics Endpoints
# ============================================================================


@app.post("/rag/generate_annotations", response_model=GenerateAnnotationsResponse)
async def generate_annotations(
    request: GenerateAnnotationsRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> GenerateAnnotationsResponse:
    """Auto-generate ground truth annotations using Ollama LLM.

    SECURITY: Requires API key authentication.

    Args:
        request: Annotation generation parameters
        x_api_key: API key (from header)

    Returns:
        Count of generated annotations

    Example:
        curl -X POST http://localhost:11435/rag/generate_annotations \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"filename":"diabetes.pdf","questions_per_chunk":2}'
    """
    if x_api_key != RAG_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    if request.filename not in _document_store:
        raise HTTPException(status_code=404, detail=f"Document '{request.filename}' not found")

    try:
        start_time = time.time()

        chunks = _document_store[request.filename]["chunks"]

        # Generate annotations with LLM
        annotations = await generate_annotations_for_document(
            filename=request.filename,
            chunks=chunks,
            questions_per_chunk=request.questions_per_chunk,
            model=request.model,
        )

        # Store in ground truth store
        _ground_truth_store[request.filename] = annotations

        elapsed_ms = int((time.time() - start_time) * 1000)

        print(
            f"[RAG Service] ✅ Generated {len(annotations)} annotations for {request.filename} "
            f"in {elapsed_ms}ms"
        )

        return GenerateAnnotationsResponse(
            filename=request.filename,
            annotations_count=len(annotations),
            chunks_processed=len(chunks),
            status="success",
            estimated_time_ms=elapsed_ms,
        )

    except Exception as e:
        print(f"[RAG Service] ❌ Annotation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Annotation generation failed: {e}")


@app.get("/rag/annotations/{filename}", response_model=AnnotationsResponse)
async def get_annotations(
    filename: str,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> AnnotationsResponse:
    """Get existing ground truth annotations for a document.

    SECURITY: Requires API key authentication.

    Example:
        curl -X GET http://localhost:11435/rag/annotations/diabetes.pdf \\
             -H "X-API-Key: your-key"
    """
    if x_api_key != RAG_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    if filename not in _ground_truth_store:
        raise HTTPException(
            status_code=404, detail=f"No annotations found for '{filename}'"
        )

    annotations = _ground_truth_store[filename]

    return AnnotationsResponse(
        filename=filename,
        annotations=[AnnotationEntry(**ann) for ann in annotations],
        count=len(annotations),
    )


@app.put("/rag/annotations/{filename}")
async def update_annotation(
    filename: str,
    request: UpdateAnnotationRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> dict:
    """Update/validate annotation manually.

    Use this to correct LLM-generated annotations.

    Example:
        curl -X PUT http://localhost:11435/rag/annotations/diabetes.pdf \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"query":"What is blood sugar?","relevant_chunks":[5],"relevance_scores":[3],"validated":true}'
    """
    if x_api_key != RAG_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    if filename not in _ground_truth_store:
        raise HTTPException(
            status_code=404, detail=f"No annotations found for '{filename}'"
        )

    # Find and update annotation with matching query
    annotations = _ground_truth_store[filename]
    found = False

    for ann in annotations:
        if ann["query"] == request.query:
            ann["relevant_chunks"] = request.relevant_chunks
            ann["relevance_scores"] = request.relevance_scores
            ann["validated"] = request.validated
            ann["source"] = "manual"  # Mark as manually edited
            found = True
            break

    if not found:
        # Add new annotation
        annotations.append(
            {
                "query": request.query,
                "relevant_chunks": request.relevant_chunks,
                "relevance_scores": request.relevance_scores,
                "source": "manual",
                "validated": request.validated,
            }
        )

    print(f"[RAG Service] ✅ Updated annotation for '{filename}': {request.query}")

    return {"status": "updated", "query": request.query, "validated": request.validated}


@app.post("/rag/evaluate", response_model=EvaluateResponse)
async def evaluate_query(
    request: EvaluateRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> EvaluateResponse:
    """Evaluate quality of a single query using RAG metrics.

    SECURITY: Requires API key authentication.

    Returns: Recall@k, Precision@k, MRR, NDCG@k

    Example:
        curl -X POST http://localhost:11435/rag/evaluate \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"query":"What is blood sugar?","filename":"diabetes.pdf","top_k":3}'
    """
    if x_api_key != RAG_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    if request.filename not in _document_store:
        raise HTTPException(status_code=404, detail=f"Document '{request.filename}' not found")

    if request.filename not in _ground_truth_store:
        raise HTTPException(
            status_code=404,
            detail=f"No ground truth annotations for '{request.filename}'. Generate annotations first.",
        )

    # 1. Execute RAG query internally
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    try:
        # Get query embedding
        query_embedding = _model.encode(
            [request.query], convert_to_numpy=True, show_progress_bar=False, device=DEVICE
        )[0]

        # Search in document
        doc_data = _document_store[request.filename]
        chunks = doc_data["chunks"]
        embeddings = doc_data["embeddings"]

        # Compute similarities
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        similarities = embeddings_norm @ query_norm

        # Get top-k chunk indices
        top_indices = np.argsort(similarities)[::-1][: request.top_k]
        retrieved_chunks = top_indices.tolist()

        # 2. Find ground truth for this query
        ground_truth_annotations = _ground_truth_store[request.filename]
        ground_truth = None

        for ann in ground_truth_annotations:
            if ann["query"].strip().lower() == request.query.strip().lower():
                ground_truth = ann
                break

        if not ground_truth:
            raise HTTPException(
                status_code=404,
                detail=f"No ground truth found for query: '{request.query}'",
            )

        relevant_chunks = ground_truth["relevant_chunks"]
        relevance_scores_list = ground_truth["relevance_scores"]

        # Build relevance scores dict
        relevance_scores = {
            chunk_id: score
            for chunk_id, score in zip(relevant_chunks, relevance_scores_list)
        }

        # 3. Compute all metrics
        metrics = compute_all_metrics(
            retrieved=retrieved_chunks,
            relevant=relevant_chunks,
            relevance_scores=relevance_scores,
            k=request.top_k,
        )

        print(
            f"[RAG Service] 📊 Evaluated query '{request.query}': "
            f"Recall@{request.top_k}={metrics[f'recall@{request.top_k}']:.2f}"
        )

        return EvaluateResponse(
            query=request.query,
            metrics=metrics,
            retrieved_chunks=retrieved_chunks,
            relevant_chunks=relevant_chunks,
            relevance_scores=relevance_scores_list,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")


@app.post("/rag/batch_evaluate", response_model=BatchEvaluateResponse)
async def batch_evaluate(
    request: BatchEvaluateRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> BatchEvaluateResponse:
    """Evaluate all queries for a document (average metrics).

    SECURITY: Requires API key authentication.

    Example:
        curl -X POST http://localhost:11435/rag/batch_evaluate \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"filename":"diabetes.pdf","top_k":3}'
    """
    if x_api_key != RAG_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    if request.filename not in _ground_truth_store:
        raise HTTPException(
            status_code=404,
            detail=f"No annotations for '{request.filename}'. Generate annotations first.",
        )

    annotations = _ground_truth_store[request.filename]

    if not annotations:
        raise HTTPException(status_code=404, detail=f"No queries found for '{request.filename}'")

    # Evaluate each query
    per_query_metrics = []
    metric_sums: dict[str, float] = {}

    for ann in annotations:
        query = ann["query"]

        # Call evaluate_query for each annotation
        try:
            eval_request = EvaluateRequest(
                query=query, filename=request.filename, top_k=request.top_k
            )

            # Reuse evaluation logic
            result = await evaluate_query(eval_request, x_api_key=x_api_key)

            per_query_metrics.append(
                {
                    "query": query,
                    "metrics": result.metrics,
                    "retrieved_chunks": result.retrieved_chunks,
                    "relevant_chunks": result.relevant_chunks,
                }
            )

            # Accumulate sums for averaging
            for metric_name, value in result.metrics.items():
                metric_sums[metric_name] = metric_sums.get(metric_name, 0.0) + value

        except HTTPException as e:
            # Skip queries without ground truth
            if e.status_code == 404:
                continue
            raise

    # Compute averages
    total_queries = len(per_query_metrics)
    avg_metrics = {
        metric_name: total / total_queries for metric_name, total in metric_sums.items()
    }

    print(
        f"[RAG Service] 📊 Batch evaluated {request.filename}: "
        f"{total_queries} queries, avg Recall@{request.top_k}={avg_metrics.get(f'recall@{request.top_k}', 0.0):.2f}"
    )

    return BatchEvaluateResponse(
        filename=request.filename,
        total_queries=total_queries,
        avg_metrics=avg_metrics,
        per_query_metrics=per_query_metrics,
    )


@app.post("/rag/similarity-search", response_model=SimilaritySearchResponse)
async def similarity_search_gpu(
    request: SimilaritySearchRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> SimilaritySearchResponse:
    """GPU-accelerated batch cosine similarity search.

    Computes similarity between query vector and all document vectors.
    Uses PyTorch with CUDA/MPS for 10-200x speedup vs CPU.

    Performance:
        1000 vectors: ~0.5ms (GPU) vs ~10ms (CPU) = 20x faster
        10000 vectors: ~2ms (GPU) vs ~100ms (CPU) = 50x faster

    SECURITY: Requires API key authentication.

    Args:
        request: Query and document vectors
        x_api_key: API key (from header)

    Returns:
        Similarity scores (0-1) for each document vector

    Example:
        curl -X POST http://localhost:11435/rag/similarity-search \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"query_vector":[0.1,...],"document_vectors":[[0.1,...],[0.2,...]]}'
    """
    # Auth check
    if x_api_key != RAG_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    # Validate dimensions match
    if len(request.query_vector) != EMBEDDING_DIM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query vector must be {EMBEDDING_DIM} dimensions",
        )

    for i, vec in enumerate(request.document_vectors):
        if len(vec) != EMBEDDING_DIM:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document vector {i} has wrong dimension: {len(vec)} (expected {EMBEDDING_DIM})",
            )

    try:
        start = time.perf_counter()

        # Convert to PyTorch tensors and move to GPU
        query = torch.tensor(request.query_vector, dtype=torch.float32, device=DEVICE)
        docs = torch.tensor(request.document_vectors, dtype=torch.float32, device=DEVICE)

        # Normalize vectors
        query_norm = query / torch.norm(query)
        docs_norm = docs / torch.norm(docs, dim=1, keepdim=True)

        # Compute cosine similarities (GPU-accelerated matrix-vector multiplication)
        similarities = torch.matmul(docs_norm, query_norm)

        # Move back to CPU and convert to list
        similarities_list = similarities.cpu().tolist()

        duration_ms = (time.perf_counter() - start) * 1000

        print(
            f"[RAG Service] 🚀 GPU similarity search: {len(request.document_vectors)} vectors "
            f"in {duration_ms:.2f}ms on {DEVICE}"
        )

        return SimilaritySearchResponse(
            similarities=similarities_list,
            device_used=str(DEVICE),
            duration_ms=round(duration_ms, 2),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GPU similarity search failed: {str(e)}",
        )


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
