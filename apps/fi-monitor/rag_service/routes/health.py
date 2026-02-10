"""Health check endpoint."""

from __future__ import annotations

import torch
from fastapi import APIRouter

from config import EMBEDDING_MODEL
from gpu import DEVICE
from schemas import HealthResponse

router = APIRouter()


@router.get("/rag/health", response_model=HealthResponse)
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
