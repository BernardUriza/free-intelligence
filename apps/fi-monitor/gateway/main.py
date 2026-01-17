"""HTTP Gateway for FI Monitor - Single Port for Multiple Services.

Routes traffic to appropriate backend:
- /rag/* → RAG Service (port 11435, GPU embeddings)
- /api/* → Ollama (port 11434, LLM inference)
- /* → Ollama (default, for compatibility)

This allows Cloudflare Tunnel to expose a single port while
proxying to multiple backend services transparently.

Author: Bernard Uriza Orozco
Created: 2026-01-16
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

# ============================================================================
# Configuration
# ============================================================================

# Gateway listens on this port (what Cloudflare Tunnel will expose)
GATEWAY_PORT = 11400

# Backend services
OLLAMA_URL = "http://localhost:11434"
RAG_SERVICE_URL = "http://localhost:11435"

# ============================================================================
# Gateway App
# ============================================================================

# HTTP client for proxying (reuse connections)
client: httpx.AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage HTTP client lifecycle."""
    global client
    client = httpx.AsyncClient(timeout=300.0)  # 5min timeout for long-running LLM requests
    print("[Gateway] HTTP client initialized")
    yield
    await client.aclose()
    print("[Gateway] HTTP client closed")


app = FastAPI(
    title="FI Monitor Gateway",
    description="HTTP gateway routing traffic to Ollama and RAG services",
    version="1.0.0",
    lifespan=lifespan,
)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def gateway(request: Request, path: str) -> Response:
    """Route requests to appropriate backend service.

    Routing logic:
    - /rag/* → RAG Service (GPU embeddings)
    - /api/* → Ollama (LLM inference)
    - /* → Ollama (default)
    """
    # Determine backend URL based on path
    if path.startswith("rag/") or path.startswith("rag"):
        backend_url = f"{RAG_SERVICE_URL}/{path}"
        service_name = "RAG"
    else:
        # Everything else goes to Ollama (/api/*, /, etc.)
        backend_url = f"{OLLAMA_URL}/{path}"
        service_name = "Ollama"

    # Forward query parameters
    if request.url.query:
        backend_url = f"{backend_url}?{request.url.query}"

    # Read request body
    body = await request.body()

    # Forward headers (except Host, which we'll override)
    headers = dict(request.headers)
    headers.pop("host", None)  # Remove original host

    try:
        # Proxy the request
        backend_request = client.build_request(
            method=request.method,
            url=backend_url,
            headers=headers,
            content=body,
        )

        backend_response = await client.send(backend_request, stream=True)

        # Check if response is streaming (Server-Sent Events or chunked)
        is_streaming = "text/event-stream" in backend_response.headers.get("content-type", "")

        if is_streaming:
            # Stream response back to client
            async def stream_generator():
                async for chunk in backend_response.aiter_bytes():
                    yield chunk

            return StreamingResponse(
                stream_generator(),
                status_code=backend_response.status_code,
                headers=dict(backend_response.headers),
                media_type=backend_response.headers.get("content-type"),
            )
        else:
            # Non-streaming response
            content = await backend_response.aread()
            return Response(
                content=content,
                status_code=backend_response.status_code,
                headers=dict(backend_response.headers),
                media_type=backend_response.headers.get("content-type"),
            )

    except httpx.ConnectError as e:
        return Response(
            content=f'{{"error": "{service_name} service not available", "detail": "{str(e)}"}}',
            status_code=503,
            media_type="application/json",
        )
    except Exception as e:
        return Response(
            content=f'{{"error": "Gateway error", "detail": "{str(e)}"}}',
            status_code=500,
            media_type="application/json",
        )


@app.get("/gateway/health")
async def health() -> dict:
    """Gateway health check (doesn't check backends)."""
    return {
        "status": "ok",
        "gateway_port": GATEWAY_PORT,
        "backends": {
            "ollama": OLLAMA_URL,
            "rag_service": RAG_SERVICE_URL,
        },
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print(f"[Gateway] Starting on port {GATEWAY_PORT}")
    print(f"[Gateway] Routing /rag/* → {RAG_SERVICE_URL}")
    print(f"[Gateway] Routing /api/* → {OLLAMA_URL}")
    print(f"[Gateway] Routing /* → {OLLAMA_URL}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=GATEWAY_PORT,
        log_level="info",
    )
