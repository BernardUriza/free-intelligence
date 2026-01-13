#!/usr/bin/env python3
"""
Aurity Minimal Backend for WSL/Development

This is a stripped-down version of the Aurity backend that:
1. Works on Windows (via WSL) and macOS/Linux
2. Has no fcntl or Unix-specific dependencies
3. Provides essential endpoints for the desktop app

Run with: uvicorn backend_minimal:app --host 0.0.0.0 --port 7001 --reload
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add backend/src to path for imports
backend_root = Path(__file__).parent.parent
src_path = backend_root / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

app = FastAPI(
    title="Aurity Backend (Minimal)",
    description="Lightweight backend for Aurity Desktop development",
    version="1.0.0-minimal",
)

# CORS for desktop app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Desktop app runs locally
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HEALTH & STATUS
# =============================================================================


@app.get("/api/health")
async def health_check():
    """Health check endpoint for backend readiness."""
    return {
        "status": "ok",
        "mode": "minimal",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/health/deep")
async def deep_health_check():
    """Deep health check with component status."""
    return {
        "status": "ok",
        "mode": "minimal",
        "components": {
            "api": "healthy",
            "ollama": "unchecked",
            "storage": "minimal",
        },
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# AUTH ENDPOINTS (Minimal/Mock)
# =============================================================================


class TokenRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    id_token: str | None = None


@app.post("/api/auth/token", response_model=TokenResponse)
async def exchange_token(request: TokenRequest):
    """
    Exchange authorization code for tokens.
    In minimal mode, this is a pass-through to Auth0.
    """
    # In minimal mode, we accept the code and return a mock token
    # The actual Auth0 flow is handled by the desktop app
    return TokenResponse(
        access_token=f"minimal_dev_token_{request.code[:8]}",
        token_type="Bearer",
        expires_in=86400,
        id_token=None,
    )


@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get current user info from token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    # In minimal mode, return a dev user
    return {
        "sub": "dev|minimal-user",
        "email": "dev@aurity.local",
        "name": "Development User",
        "roles": ["admin", "doctor"],
    }


# =============================================================================
# SESSIONS
# =============================================================================


class SessionCreate(BaseModel):
    patient_name: str | None = None
    metadata: dict[str, Any] = {}


class SessionResponse(BaseModel):
    session_id: str
    created_at: str
    status: str = "active"


# In-memory session storage for dev
_sessions: dict[str, dict] = {}


@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(data: SessionCreate):
    """Create a new session."""
    import uuid
    
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "id": session_id,
        "created_at": datetime.now().isoformat(),
        "patient_name": data.patient_name,
        "metadata": data.metadata,
        "status": "active",
    }
    
    return SessionResponse(
        session_id=session_id,
        created_at=_sessions[session_id]["created_at"],
        status="active",
    )


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sessions[session_id]


@app.get("/api/sessions")
async def list_sessions():
    """List all sessions."""
    return {"sessions": list(_sessions.values())}


# =============================================================================
# CHAT / LLM PROXY
# =============================================================================


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = "qwen3:1.7b"
    stream: bool = False


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Proxy chat to Ollama or return mock response.
    """
    import httpx
    
    ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": request.model,
                    "messages": [m.model_dump() for m in request.messages],
                    "stream": False,
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "message": data.get("message", {}),
                    "model": request.model,
                    "done": True,
                }
            else:
                # Ollama error, return mock
                return {
                    "message": {
                        "role": "assistant",
                        "content": "[Ollama no disponible] Esta es una respuesta de desarrollo.",
                    },
                    "model": request.model,
                    "done": True,
                    "error": "ollama_unavailable",
                }
    except Exception as e:
        # Network error, return mock
        return {
            "message": {
                "role": "assistant", 
                "content": f"[Modo offline] Ollama no está corriendo. Error: {e}",
            },
            "model": request.model,
            "done": True,
            "error": str(e),
        }


# =============================================================================
# TRANSCRIPTION (Mock)
# =============================================================================


@app.post("/api/transcribe")
async def transcribe_audio():
    """Mock transcription endpoint."""
    return {
        "text": "[Transcripción no disponible en modo minimal]",
        "segments": [],
        "language": "es",
    }


# =============================================================================
# STARTUP
# =============================================================================


@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("🏥 Aurity Backend (Minimal Mode)")
    print("=" * 60)
    print(f"  Mode:     MINIMAL (development)")
    print(f"  Time:     {datetime.now().isoformat()}")
    print(f"  Endpoints: /api/health, /api/chat, /api/sessions")
    print("=" * 60)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend_minimal:app",
        host="0.0.0.0",
        port=7001,
        reload=True,
    )
