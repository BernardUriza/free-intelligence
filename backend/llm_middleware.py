from __future__ import annotations

"""
Free Intelligence - LLM Middleware (FastAPI)

HTTP/CLI middleware for LLM prompt handling.

File: backend/llm_middleware.py
Created: 2025-10-29
Card: FI-CORE-FEAT-001
Port: 9001 (shares with fi_corpus_api)

Endpoints:
  POST   /llm/generate           - Generate LLM response (new contract)
  POST   /llm/prompt             - Send prompt to LLM and save interaction (legacy)
  GET    /health                 - Health check

Usage:
  uvicorn backend.llm_middleware:app --reload --port 9001 --host 0.0.0.0
"""

import hashlib
import json
import time
import uuid
from datetime import timezone, datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from backend.config_loader import load_config
from backend.corpus_ops import append_interaction
from backend.kpis_aggregator import get_kpis_aggregator
from backend.llm_adapter import LLMRequest
from backend.llm_cache import get_cache
from backend.llm_metrics import get_metrics
from backend.logger import get_logger
from backend.policy_enforcer import PolicyViolation, get_policy_enforcer, redact
from backend.providers.claude import ClaudeAdapter
from backend.providers.ollama import OllamaAdapter

logger = get_logger(__name__)

# Initialize policy enforcer
policy = get_policy_enforcer()

# Initialize cache, metrics, and KPIs aggregator
cache = get_cache(ttl_minutes=30)
metrics = get_metrics()
kpis_aggregator = get_kpis_aggregator()

# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class GenerateRequest(BaseModel):
    """Request model for /llm/generate endpoint (new contract)"""

    provider: str = Field(..., description="Provider: ollama or claude")
    model: str = Field(..., description="Model identifier")
    prompt: str = Field(..., description="User prompt", min_length=1)
    system: Optional[str] = Field("", description="System prompt")
    params: Optional[dict[str, Any]] = Field(
        default_factory=lambda: {"temperature": 0.2, "max_tokens": 512},
        description="Parameters (temperature, max_tokens)",
    )
    stream: bool = Field(False, description="Stream response (not supported in v1)")

    @validator("provider")
    def validate_provider(cls, v):
        if v not in ["ollama", "claude"]:
            raise ValueError("provider must be 'ollama' or 'claude'")
        return v

    @validator("stream")
    def validate_stream(cls, v):
        if v:
            raise ValueError("stream=true not supported in v1")
        return v


class GenerateResponse(BaseModel):
    """Response model for /llm/generate endpoint (new contract)"""

    ok: bool = Field(..., description="Success status")
    text: str = Field(..., description="Generated text")
    usage: dict[str, int] = Field(..., description="Token usage (in, out)")
    latency_ms: int = Field(..., description="Latency in milliseconds")
    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model identifier")
    prompt_hash: str = Field(..., description="SHA-256 hash of prompt")
    cache_hit: bool = Field(..., description="Whether response was from cache")


class PromptRequest(BaseModel):
    """Request model for /llm/prompt endpoint (legacy)"""

    prompt: str = Field(..., description="User prompt text", min_length=1)
    model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Model identifier (claude-3-5-sonnet-20241022 or ollama/mistral)",
    )
    session_id: str = Field(..., description="Session identifier")
    max_tokens: int = Field(default=4096, description="Max tokens in response", ge=1, le=100000)
    temperature: float = Field(default=0.7, description="Temperature (0.0-1.0)", ge=0.0, le=1.0)
    system_prompt: Optional[str] = Field(None, description="System prompt override")


class PromptResponse(BaseModel):
    """Response model for /llm/prompt endpoint"""

    interaction_id: str = Field(..., description="UUID of saved interaction")
    response: str = Field(..., description="LLM response text")
    model: str = Field(..., description="Model used")
    latency_ms: int = Field(..., description="Latency in milliseconds")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    content_hash: str = Field(..., description="SHA-256 hash of prompt + response")


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    timestamp: str
    llm_adapters: dict[str, str]


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Free Intelligence - LLM Middleware",
    description="HTTP/CLI middleware for LLM prompt handling",
    version="0.1.0",
)

# CORS middleware (allow localhost:9000 for Aurity UI)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9000", "http://127.0.0.1:9000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# LLM ADAPTERS
# ============================================================================

# Initialize adapters
try:
    claude_adapter = ClaudeAdapter()
    logger.info("Claude adapter initialized")
except Exception as e:
    logger.warning(f"Claude adapter failed: {e}")
    claude_adapter = None

try:
    ollama_adapter = OllamaAdapter()
    logger.info("Ollama adapter initialized")
except Exception as e:
    logger.warning(f"Ollama adapter failed: {e}")
    ollama_adapter = None


def get_adapter(model: str):
    """Get appropriate LLM adapter based on model string"""
    if model.startswith("claude"):
        if claude_adapter is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Claude adapter not available (check API key)",
            )
        return claude_adapter
    elif model.startswith("ollama/"):
        if ollama_adapter is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ollama adapter not available (check Ollama server)",
            )
        return ollama_adapter
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model: {model}. Use 'claude-3-5-sonnet-20241022' or 'ollama/mistral'",
        )


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.post("/llm/generate", response_model=GenerateResponse, status_code=status.HTTP_200_OK)
async def generate_llm(request: GenerateRequest) -> GenerateResponse:
    """
    Generate LLM response with caching (new contract).

    Contract:
    - Input: {provider, model, prompt, system, params, stream}
    - Output: {ok, text, usage, latency_ms, provider, model, prompt_hash, cache_hit}

    Flow:
    1. Compute cache key (SHA-256)
    2. Check cache (if hit → return cached response)
    3. Route to adapter (Ollama or Claude)
    4. Call LLM
    5. Cache response
    6. Return with metadata

    Args:
        request: GenerateRequest with provider, model, prompt

    Returns:
        GenerateResponse with text and metadata

    Raises:
        HTTPException: If LLM fails or validation fails
    """
    start_time = time.time()

    # Extract params
    params = request.params or {}
    temperature = params.get("temperature", 0.2)
    max_tokens = params.get("max_tokens", 512)

    # Compute prompt hash
    prompt_content = f"{request.provider}|{request.model}|{request.prompt}|{request.system}|{json.dumps(params, sort_keys=True)}"
    prompt_hash = hashlib.sha256(prompt_content.encode()).hexdigest()

    logger.info(
        "LLM_GENERATE_REQUEST",
        provider=request.provider,
        model=request.model,
        prompt_hash=prompt_hash[:16],
        prompt_length=len(request.prompt),
    )

    # Check cache
    cached = cache.get(
        provider=request.provider,
        model=request.model,
        prompt=request.prompt,
        system=request.system or "",
        params=params,
    )

    if cached:
        # Record cache hit
        metrics.record_request(request.provider, latency_ms=0, cache_hit=True)

        # Record to KPIs aggregator
        kpis_aggregator.record_llm_event(
            provider=request.provider,
            tokens_in=cached["usage"].get("in"),
            tokens_out=cached["usage"].get("out"),
            latency_ms=0,
            cache_hit=True,
        )

        logger.info(
            "LLM_GENERATE_CACHE_HIT",
            provider=request.provider,
            model=request.model,
            prompt_hash=prompt_hash[:16],
        )
        return GenerateResponse(
            ok=True,
            text=cached["text"],
            usage=cached["usage"],
            latency_ms=0,  # Cache hit ~0ms
            provider=request.provider,
            model=request.model,
            prompt_hash=prompt_hash,
            cache_hit=True,
        )

    # Get adapter
    try:
        if request.provider == "ollama":
            if ollama_adapter is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Ollama adapter not available (check Ollama server)",
                )
            adapter = ollama_adapter
        elif request.provider == "claude":
            if claude_adapter is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Claude adapter not available (check API key)",
                )
            adapter = claude_adapter
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown provider: {request.provider}",
            )

        # Create LLM request
        llm_request = LLMRequest(
            prompt=request.prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=request.system,
            timeout_seconds=30,
        )

        # Call LLM
        llm_response = adapter.generate(llm_request)

        # Calculate total latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Build response dict
        response_data = {
            "text": llm_response.content,
            "usage": {
                "in": llm_response.metadata.get("input_tokens", 0),
                "out": llm_response.metadata.get("output_tokens", 0),
            },
        }

        # Cache response
        cache.set(
            provider=request.provider,
            model=request.model,
            prompt=request.prompt,
            response=response_data,
            system=request.system or "",
            params=params,
        )

        # Log to NDJSON (without prompt text)
        log_dir = Path("logs/llm")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"llm_{datetime.now(timezone.utc).strftime('%Y%m%d')}.ndjson"

        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat() + "Z",
            "provider": request.provider,
            "model": request.model,
            "ok": True,
            "latency_ms": latency_ms,
            "tokens": response_data["usage"]["in"] + response_data["usage"]["out"],
            "cache_hit": False,
            "prompt_hash": prompt_hash,
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        # Record metrics
        metrics.record_request(request.provider, latency_ms=latency_ms, cache_hit=False)

        # Record to KPIs aggregator
        kpis_aggregator.record_llm_event(
            provider=request.provider,
            tokens_in=response_data["usage"].get("in"),
            tokens_out=response_data["usage"].get("out"),
            latency_ms=latency_ms,
            cache_hit=False,
        )

        # Policy: Check cost (basic estimation: 1 token ≈ 0.0001 cents for estimation)
        # Note: Real cost should come from provider-specific pricing
        total_tokens = response_data["usage"]["in"] + response_data["usage"]["out"]
        estimated_cost_cents = total_tokens * 0.0001  # Placeholder estimation
        try:
            policy.check_cost(int(estimated_cost_cents), run_id=prompt_hash[:16])
        except PolicyViolation as e:
            logger.warning(
                "LLM_COST_VIOLATION",
                provider=request.provider,
                estimated_cents=int(estimated_cost_cents),
                error=str(e),
            )
            # Cost violation is logged but doesn't block response (post-generation check)

        # Policy: Redact sensitive info from response text
        original_text = llm_response.content
        redacted_text = redact(original_text)
        if redacted_text != original_text:
            logger.info(
                "LLM_RESPONSE_REDACTED",
                provider=request.provider,
                prompt_hash=prompt_hash[:16],
                redactions=len(
                    [c for c in redacted_text if c == "[" and "REDACTED" in redacted_text]
                ),
            )

        # Warn if latency > 2s
        if latency_ms > 2000:
            logger.warning(
                "LLM_GENERATE_SLOW",
                provider=request.provider,
                model=request.model,
                latency_ms=latency_ms,
                prompt_hash=prompt_hash[:16],
                p95_latency_ms=metrics.get_p95_latency(),
            )

        logger.info(
            "LLM_GENERATE_COMPLETED",
            provider=request.provider,
            model=request.model,
            latency_ms=latency_ms,
            tokens=response_data["usage"]["in"] + response_data["usage"]["out"],
            prompt_hash=prompt_hash[:16],
        )

        return GenerateResponse(
            ok=True,
            text=redacted_text,  # Use redacted text instead of raw LLM output
            usage=response_data["usage"],
            latency_ms=latency_ms,
            provider=request.provider,
            model=request.model,
            prompt_hash=prompt_hash,
            cache_hit=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "LLM_GENERATE_FAILED",
            provider=request.provider,
            model=request.model,
            error=str(e),
            prompt_hash=prompt_hash[:16],
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM generation failed: {str(e)}",
        )


@app.post("/llm/prompt", response_model=PromptResponse, status_code=status.HTTP_200_OK)
async def prompt_llm(request: PromptRequest) -> PromptResponse:
    """
    Send prompt to LLM and save interaction to corpus.

    Flow:
    1. Get appropriate LLM adapter (Claude or Ollama)
    2. Send prompt to LLM
    3. Save interaction to corpus.h5 (append-only)
    4. Return response with interaction_id

    Args:
        request: PromptRequest with prompt, model, session_id

    Returns:
        PromptResponse with LLM response and metadata

    Raises:
        HTTPException: If LLM fails or corpus write fails
    """
    start_time = time.time()
    interaction_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat() + "Z"
    config = load_config()

    logger.info(
        f"[{interaction_id}] Received prompt",
        extra={
            "interaction_id": interaction_id,
            "session_id": request.session_id,
            "model": request.model,
            "prompt_length": len(request.prompt),
        },
    )

    try:
        # Get LLM adapter
        adapter = get_adapter(request.model)

        # Create LLM request
        llm_request = LLMRequest(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system_prompt=request.system_prompt,
            timeout_seconds=30,
            metadata={"session_id": request.session_id, "interaction_id": interaction_id},
        )

        # Call LLM
        logger.info(f"[{interaction_id}] Calling LLM: {request.model}")
        llm_response = adapter.generate(llm_request)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)

        # Calculate content hash
        content = request.prompt + llm_response.content
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        logger.info(
            f"[{interaction_id}] LLM response received",
            extra={
                "latency_ms": latency_ms,
                "response_length": len(llm_response.content),
                "content_hash": content_hash[:16],
            },
        )

        # Save to corpus (append-only)
        try:
            append_interaction(
                corpus_path=config["storage"]["corpus_path"],
                session_id=request.session_id,
                prompt=request.prompt,
                response=llm_response.content,
                model=request.model,
                tokens=llm_response.tokens_used,
                timestamp=timestamp,
            )
            logger.info(f"[{interaction_id}] Saved to corpus: {request.session_id}")
        except Exception as corpus_error:
            logger.error(
                f"[{interaction_id}] Failed to save to corpus: {corpus_error}",
                exc_info=True,
            )
            # Continue anyway (corpus write failure shouldn't block user)

        # Return response
        return PromptResponse(
            interaction_id=interaction_id,
            response=llm_response.content,
            model=request.model,
            latency_ms=latency_ms,
            timestamp=timestamp,
            content_hash=content_hash,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[{interaction_id}] LLM prompt failed: {e}",
            exc_info=True,
            extra={"session_id": request.session_id, "model": request.model},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM request failed: {str(e)}",
        )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with status and adapter availability
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        llm_adapters={
            "claude": "available" if claude_adapter else "unavailable",
            "ollama": "available" if ollama_adapter else "unavailable",
        },
    )


@app.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus-style metrics endpoint.

    Returns:
        Metrics in Prometheus format (text/plain)
    """
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(
        content=metrics.get_prometheus_metrics(),
        media_type="text/plain; version=0.0.4",
    )


@app.get("/metrics/json")
async def metrics_json_endpoint():
    """
    Metrics as JSON.

    Returns:
        Metrics as JSON dictionary
    """
    return metrics.get_stats()


# ============================================================================
# STARTUP
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9001)
