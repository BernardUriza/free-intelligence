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

import logging
import sys
from contextlib import asynccontextmanager

import torch
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer

import state
from config import EMBEDDING_MODEL
from gpu import DEVICE

# Configure logging
logging.basicConfig(level=logging.INFO)


# ============================================================================
# Lifespan - Load model on startup
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup, cleanup on shutdown.

    Performs GPU allocation test before loading model to catch issues early.
    """
    # GPU Allocation Test (catch driver issues, VRAM exhaustion)
    if DEVICE in ("cuda", "mps"):
        try:
            print("[RAG Service] Testing GPU memory allocation...")
            test_tensor = torch.zeros(100, 100, device=DEVICE)
            del test_tensor
            print("[RAG Service] GPU memory allocation test passed")
        except Exception as e:
            print(f"\nERROR: GPU detected but allocation failed: {e}")
            print("Possible causes:")
            print("  - GPU driver crashed")
            print("  - VRAM exhausted by another process")
            print("  - GPU in use by another application")
            print("\nTroubleshooting:")
            print("  - Restart GPU drivers")
            print("  - Close other GPU-intensive apps (games, video editing, etc.)")
            print("  - Check GPU usage: nvidia-smi (CUDA) or Activity Monitor (MPS)")
            sys.exit(1)

    print(f"[RAG Service] Loading model: {EMBEDDING_MODEL}")
    print(f"[RAG Service] Device: {DEVICE}")

    state._model = SentenceTransformer(EMBEDDING_MODEL, device=DEVICE)

    # Warm-up inference (first run is slow due to model loading)
    print("[RAG Service] Warming up model...")
    _ = state._model.encode(["warm-up query"], convert_to_numpy=True, show_progress_bar=False)
    print(f"[RAG Service] Model ready on {DEVICE}")

    # Log GPU memory usage (CUDA only - MPS doesn't expose VRAM)
    if DEVICE == "cuda":
        allocated_mb = torch.cuda.memory_allocated(0) / (1024**2)
        reserved_mb = torch.cuda.memory_reserved(0) / (1024**2)
        print(f"[RAG Service] GPU Memory: {allocated_mb:.0f}MB allocated, {reserved_mb:.0f}MB reserved")

    yield

    # Cleanup
    print("[RAG Service] Shutting down...")
    if DEVICE == "cuda":
        torch.cuda.empty_cache()
        print("[RAG Service] GPU memory cleared")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="FI Monitor RAG Service",
    description="GPU-accelerated embedding generation for RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configured for Tauri dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:1420"],  # Tauri dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routes
from routes import api_router  # noqa: E402

app.include_router(api_router)


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
