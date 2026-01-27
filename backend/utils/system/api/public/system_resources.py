"""System Resources API - Monitor system and AI model resources.

PUBLIC endpoint for monitoring system RAM, running Ollama models,
and hardware compatibility with AI models.

Author: Bernard Uriza Orozco
Created: 2025-12-12
"""

from __future__ import annotations

import json
import time
from datetime import datetime

import httpx
import os
import psutil
from fastapi import APIRouter, HTTPException, Query, status
from pathlib import Path
from pydantic import BaseModel

router = APIRouter(prefix="/admin/system", tags=["System Resources"])


# =============================================================================
# Response Models
# =============================================================================


class MemoryInfo(BaseModel):
    """System memory information."""

    total_gb: float
    available_gb: float
    used_gb: float
    percent_used: float


class SystemResources(BaseModel):
    """Complete system resource snapshot."""

    memory: MemoryInfo
    cpu_percent: float
    cpu_count: int
    platform: str
    timestamp: str


class RunningModel(BaseModel):
    """An Ollama model currently loaded in memory."""

    name: str
    model_id: str
    size_bytes: int
    size_gb: float
    vram_bytes: int | None = None
    vram_gb: float | None = None
    processor: str  # 'cpu', 'gpu', 'partial'
    until: str | None = None  # When model will be unloaded


class RunningModelsResponse(BaseModel):
    """Response for running models endpoint."""

    models: list[RunningModel]
    total_loaded_gb: float
    ollama_available: bool


class ModelCompatibility(BaseModel):
    """Hardware compatibility check for a model."""

    model_id: str
    ram_required_gb: float
    ram_available_gb: float
    can_run: bool
    warning: str | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/resources", response_model=SystemResources)
async def get_system_resources() -> SystemResources:
    """Get current system resource usage.

    Returns:
        System memory, CPU, and platform information
    """
    mem = psutil.virtual_memory()

    return SystemResources(
        memory=MemoryInfo(
            total_gb=round(mem.total / (1024**3), 2),
            available_gb=round(mem.available / (1024**3), 2),
            used_gb=round(mem.used / (1024**3), 2),
            percent_used=mem.percent,
        ),
        cpu_percent=psutil.cpu_percent(interval=0.1),
        cpu_count=psutil.cpu_count() or 1,
        platform=f"{os.uname().sysname} {os.uname().machine}",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/ollama/running", response_model=RunningModelsResponse)
async def get_running_models() -> RunningModelsResponse:
    """Get currently loaded Ollama models.

    Uses `ollama ps` to get models currently in memory.

    Returns:
        List of running models with memory usage
    """
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{ollama_host}/api/ps", timeout=5.0)
            response.raise_for_status()
            data = response.json()

        models = []
        total_size = 0

        for m in data.get("models", []):
            size_bytes = m.get("size", 0)
            vram_bytes = m.get("size_vram", 0)
            total_size += size_bytes

            # Determine processor type
            if vram_bytes and vram_bytes >= size_bytes * 0.9:
                processor = "gpu"
            elif vram_bytes and vram_bytes > 0:
                processor = "partial"
            else:
                processor = "cpu"

            models.append(
                RunningModel(
                    name=m.get("name", "unknown"),
                    model_id=m.get("model", m.get("name", "unknown")),
                    size_bytes=size_bytes,
                    size_gb=round(size_bytes / (1024**3), 2),
                    vram_bytes=vram_bytes if vram_bytes else None,
                    vram_gb=round(vram_bytes / (1024**3), 2) if vram_bytes else None,
                    processor=processor,
                    until=m.get("expires_at"),
                )
            )

        return RunningModelsResponse(
            models=models,
            total_loaded_gb=round(total_size / (1024**3), 2),
            ollama_available=True,
        )

    except httpx.ConnectError:
        return RunningModelsResponse(
            models=[],
            total_loaded_gb=0,
            ollama_available=False,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying Ollama: {e!s}",
        ) from e


@router.get("/compatibility/{model_id}", response_model=ModelCompatibility)
async def check_model_compatibility(model_id: str) -> ModelCompatibility:
    """Check if system can run a specific model.

    Args:
        model_id: Model identifier to check

    Returns:
        Compatibility assessment with warnings
    """
    from backend.services.llm.services.llm_model_service import llm_model_service

    model = llm_model_service.get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    mem = psutil.virtual_memory()
    available_gb = round(mem.available / (1024**3), 2)
    ram_required = model.ram_required_gb or 4.0  # Default estimate

    can_run = available_gb >= ram_required
    warning = None

    if not can_run:
        warning = f"Necesitas {ram_required - available_gb:.1f}GB más de RAM disponible"
    elif available_gb < ram_required * 1.2:
        warning = "RAM ajustada - puede haber lentitud"

    return ModelCompatibility(
        model_id=model_id,
        ram_required_gb=ram_required,
        ram_available_gb=available_gb,
        can_run=can_run,
        warning=warning,
    )


@router.post("/ollama/unload/{model_name}")
async def unload_model(model_name: str) -> dict:
    """Unload a model from Ollama memory.

    Args:
        model_name: Name of the model to unload

    Returns:
        Success status
    """
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    try:
        async with httpx.AsyncClient() as client:
            # Ollama unloads by setting keep_alive to 0
            response = await client.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": model_name,
                    "keep_alive": 0,
                },
                timeout=30.0,
            )
            response.raise_for_status()

        return {"success": True, "message": f"Model {model_name} unloaded"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unload model: {e!s}",
        ) from e


# =============================================================================
# Ollama Source Configuration (FI-BACKEND-SOURCE-001)
# =============================================================================

CONFIG_FILE = Path.home() / ".aurity" / "ollama-source.json"

DEFAULT_CONFIG = {
    "source": "local",
    "tunnel_url": "",
    "local_url": "http://localhost:11434",
}


class OllamaSourceConfig(BaseModel):
    """Ollama source configuration."""

    source: str  # 'tunnel' or 'local'
    tunnel_url: str
    local_url: str


class ConnectionTestResult(BaseModel):
    """Result of testing Ollama connection."""

    connected: bool
    latency_ms: int | None = None
    error: str | None = None


@router.get("/ollama/config", response_model=OllamaSourceConfig)
async def get_ollama_config() -> OllamaSourceConfig:
    """Get current Ollama source configuration.

    Returns:
        Current configuration from ~/.aurity/ollama-source.json
    """
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
            return OllamaSourceConfig(**{**DEFAULT_CONFIG, **data})
        except (json.JSONDecodeError, OSError):
            pass

    return OllamaSourceConfig(**DEFAULT_CONFIG)


@router.post("/ollama/config", response_model=OllamaSourceConfig)
async def save_ollama_config(config: OllamaSourceConfig) -> OllamaSourceConfig:
    """Save Ollama source configuration.

    Args:
        config: New configuration to save

    Returns:
        Saved configuration
    """
    # Ensure directory exists
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Save config
    CONFIG_FILE.write_text(json.dumps(config.model_dump(), indent=2))

    return config


@router.get("/ollama/test", response_model=ConnectionTestResult)
async def test_ollama_connection(
    url: str = Query(default="http://localhost:11434", description="Ollama URL to test"),
) -> ConnectionTestResult:
    """Test connection to an Ollama endpoint.

    Args:
        url: Ollama URL to test

    Returns:
        Connection status with latency
    """
    try:
        start = time.time()
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}/api/tags", timeout=5.0)
            response.raise_for_status()
        latency = int((time.time() - start) * 1000)

        return ConnectionTestResult(connected=True, latency_ms=latency)

    except httpx.ConnectError:
        return ConnectionTestResult(
            connected=False,
            error="Connection refused - Ollama not running?",
        )
    except httpx.TimeoutException:
        return ConnectionTestResult(
            connected=False,
            error="Connection timeout (>5s)",
        )
    except Exception as e:
        return ConnectionTestResult(
            connected=False,
            error=str(e)[:100],
        )
