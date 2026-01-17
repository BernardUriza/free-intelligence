"""RAG Embedding Service for FI Monitor - GPU Acceleration.

Provides fast embedding generation using sentence-transformers with GPU support.
Exposes /rag/embed endpoint for FI Cloud to offload embeddings from CPU.

Architecture:
- GPU detection (CUDA/MPS) for acceleration
- Fallback to CPU if no GPU available
- API key authentication for security
- Batch embedding support
- Health check endpoint

Author: Bernard Uriza Orozco
Created: 2026-01-16
Card: FI-API-FEAT-020 (Phase 3)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import torch
import uvicorn
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

# ============================================================================
# Configuration
# ============================================================================

# Model: Same as backend for consistency
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

# Security: API key for authentication
RAG_API_KEY = os.getenv("RAG_API_KEY", "change-me-in-production")

# GPU Detection
def _detect_device() -> str:
    """Detect best available device (cuda > mps > cpu)."""
    if torch.cuda.is_available():
        print(f"[RAG Service] 🚀 GPU detected: {torch.cuda.get_device_name(0)}")
        return "cuda"
    elif torch.backends.mps.is_available():
        print("[RAG Service] 🚀 Apple Silicon GPU detected (MPS)")
        return "mps"
    else:
        print("[RAG Service] ⚠️ No GPU detected, using CPU")
        return "cpu"


DEVICE = _detect_device()

# Global model instance (lazy loaded)
_model: SentenceTransformer | None = None


# ============================================================================
# Lifespan - Load model on startup
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown."""
    global _model

    print(f"[RAG Service] Loading model: {EMBEDDING_MODEL}")
    print(f"[RAG Service] Device: {DEVICE}")

    _model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)

    # Warm-up inference (first run is slow due to model loading)
    print("[RAG Service] Warming up model...")
    _ = _model.encode(["warm-up query"], convert_to_numpy=True, show_progress_bar=False)
    print("[RAG Service] ✅ Model ready")

    yield

    # Cleanup
    print("[RAG Service] Shutting down...")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="FI Monitor RAG Service",
    description="GPU-accelerated embedding generation for RAG",
    version="1.0.0",
    lifespan=lifespan,
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
    model: str = Field(..., description="Model loaded")


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


@app.get("/rag/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check with GPU info.

    Public endpoint (no auth required).
    """
    gpu_name = None
    if DEVICE == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
    elif DEVICE == "mps":
        gpu_name = "Apple Silicon (MPS)"

    return HealthResponse(
        status="ok",
        device=DEVICE,
        gpu_name=gpu_name,
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
