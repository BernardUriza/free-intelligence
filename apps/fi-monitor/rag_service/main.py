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

import os
import sys
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
