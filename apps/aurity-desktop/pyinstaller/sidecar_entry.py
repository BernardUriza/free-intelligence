#!/usr/bin/env python3
"""
Aurity Backend Sidecar Entry Point

This is a self-contained FastAPI backend for Aurity Desktop.
Compile with PyInstaller to create the sidecar executable.

Usage:
    aurity-backend --port 7051
"""

import argparse
import os
import sys
from datetime import datetime
from typing import Any

# Import FastAPI and dependencies
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# =============================================================================
# FASTAPI APP (Self-contained minimal backend)
# =============================================================================

app = FastAPI(
    title="Aurity Backend (Sidecar)",
    description="Embedded backend for Aurity Desktop",
    version="1.0.0-sidecar",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "mode": "sidecar",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/health/deep")
async def deep_health_check():
    return {
        "status": "ok",
        "mode": "sidecar",
        "components": {
            "api": "healthy",
            "ollama": "unchecked",
            "storage": "minimal",
        },
        "timestamp": datetime.now().isoformat(),
    }


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
    return TokenResponse(
        access_token=f"sidecar_token_{request.code[:8]}",
        token_type="Bearer",
        expires_in=86400,
        id_token=None,
    )


@app.get("/api/auth/me")
async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    return {
        "sub": "dev|sidecar-user",
        "email": "dev@aurity.local",
        "name": "Sidecar User",
        "roles": ["admin", "doctor"],
    }


class SessionCreate(BaseModel):
    patient_name: str | None = None
    metadata: dict[str, Any] = {}


class SessionResponse(BaseModel):
    session_id: str
    created_at: str
    status: str = "active"


_sessions: dict[str, dict] = {}


@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(data: SessionCreate):
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
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sessions[session_id]


@app.get("/api/sessions")
async def list_sessions():
    return {"sessions": list(_sessions.values())}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = "qwen3:1.7b"
    stream: bool = False


@app.post("/api/chat")
async def chat(request: ChatRequest):
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
                return {
                    "message": {
                        "role": "assistant",
                        "content": "[Ollama no disponible] Respuesta de desarrollo.",
                    },
                    "model": request.model,
                    "done": True,
                    "error": "ollama_unavailable",
                }
    except Exception as e:
        return {
            "message": {
                "role": "assistant", 
                "content": f"[Modo offline] Ollama no está corriendo. Error: {e}",
            },
            "model": request.model,
            "done": True,
            "error": str(e),
        }


@app.post("/api/transcribe")
async def transcribe_audio():
    return {
        "text": "[Transcripcion no disponible en modo sidecar]",
        "segments": [],
        "language": "es",
    }


# =============================================================================
# TTS ENDPOINTS
# =============================================================================

@app.get("/api/tts/providers")
async def get_tts_providers():
    """Return available TTS providers."""
    return {
        "providers": [
            {
                "id": "browser",
                "name": "Browser TTS",
                "available": True,
                "voices": []
            }
        ],
        "default": "browser"
    }


@app.api_route("/api/tts/synthesize", methods=["GET", "POST", "OPTIONS"])
async def synthesize_tts(request: Request):
    """TTS synthesis - returns empty audio for sidecar mode."""
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return {"status": "ok"}
    return {
        "audio": None,
        "message": "TTS not available in sidecar mode - use browser TTS",
        "provider": "browser"
    }


# =============================================================================
# ASSISTANT CHAT STREAMING ENDPOINT
# =============================================================================

from fastapi.responses import StreamingResponse
import json

class AssistantChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str = "qwen3:1.7b"
    session_id: str | None = None
    persona_id: str | None = None


async def stream_ollama_response(messages: list, model: str):
    """Stream response from Ollama in OpenAI-compatible format."""
    import httpx
    
    ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                },
            ) as response:
                if response.status_code != 200:
                    yield f"data: {json.dumps({'error': 'Ollama not available'})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            message = data.get("message", {})
                            content = message.get("content", "")
                            done = data.get("done", False)
                            
                            # Skip empty content chunks (thinking tokens)
                            if content:
                                # Format as OpenAI-compatible SSE
                                chunk = {
                                    "choices": [{
                                        "delta": {"content": content},
                                        "index": 0,
                                        "finish_reason": None
                                    }],
                                    "model": model
                                }
                                yield f"data: {json.dumps(chunk)}\n\n"
                            
                            if done:
                                # Send final chunk with finish_reason
                                final_chunk = {
                                    "choices": [{
                                        "delta": {},
                                        "index": 0,
                                        "finish_reason": "stop"
                                    }],
                                    "model": model
                                }
                                yield f"data: {json.dumps(final_chunk)}\n\n"
                                yield "data: [DONE]\n\n"
                                break
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"


@app.post("/api/workflows/aurity/assistant/chat/stream")
async def assistant_chat_stream(request: AssistantChatRequest):
    """Stream chat response from Ollama."""
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    return StreamingResponse(
        stream_ollama_response(messages, request.model),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/workflows/aurity/assistant/chat")
async def assistant_chat(request: AssistantChatRequest):
    """Non-streaming chat with Ollama."""
    import httpx
    
    ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": request.model,
                    "messages": messages,
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
                return {
                    "message": {
                        "role": "assistant",
                        "content": "Ollama no disponible. Asegurate de que Ollama esta corriendo.",
                    },
                    "model": request.model,
                    "done": True,
                }
    except Exception as e:
        return {
            "message": {
                "role": "assistant",
                "content": f"Error conectando a Ollama: {e}",
            },
            "model": request.model,
            "done": True,
        }


# =============================================================================
# OBSERVABILITY ENDPOINTS
# =============================================================================

@app.post("/api/observability/audio/events")
async def log_audio_event(request: Request):
    """Log audio events - stub for observability."""
    try:
        body = await request.json()
        print(f"[Audio Event] {body.get('event', 'unknown')}")
    except:
        pass
    return {"status": "logged"}


@app.post("/api/timeline/audio-error")
async def log_timeline_audio_error(request: Request):
    """Log timeline audio errors - stub."""
    try:
        body = await request.json()
        print(f"[Timeline Audio Error] {body}")
    except:
        pass
    return {"status": "logged"}


@app.get("/api/timeline/{session_id}")
async def get_timeline(session_id: str):
    """Get timeline for a session."""
    return {
        "session_id": session_id,
        "events": [],
        "created_at": datetime.now().isoformat()
    }


@app.post("/api/timeline/{session_id}/events")
async def add_timeline_event(session_id: str, request: Request):
    """Add event to timeline."""
    try:
        body = await request.json()
        return {
            "session_id": session_id,
            "event_id": "evt_" + session_id[:8],
            "created_at": datetime.now().isoformat(),
            **body
        }
    except:
        return {"error": "Invalid request"}


# =============================================================================
# WORKFLOW ENDPOINTS (Stubs)
# =============================================================================

@app.post("/api/workflows/aurity/sessions")
async def create_workflow_session():
    """Create a workflow session."""
    import uuid
    session_id = str(uuid.uuid4())
    return {
        "session_id": session_id,
        "status": "active",
        "created_at": datetime.now().isoformat()
    }


@app.get("/api/workflows/aurity/sessions/{session_id}")
async def get_workflow_session(session_id: str):
    """Get workflow session."""
    return {
        "session_id": session_id,
        "status": "active",
        "created_at": datetime.now().isoformat()
    }


# =============================================================================
# PERSONAS ENDPOINTS
# =============================================================================

@app.get("/api/workflows/aurity/personas")
async def get_personas():
    """Get available personas."""
    return {
        "personas": [
            {
                "id": "default",
                "name": "Asistente Medico",
                "description": "Asistente de IA para consultas medicas",
                "system_prompt": "Eres un asistente medico profesional.",
                "is_default": True
            }
        ]
    }


@app.post("/api/workflows/aurity/personas")
async def create_persona(request: Request):
    """Create a new persona."""
    try:
        body = await request.json()
        return {
            "id": "persona_" + datetime.now().strftime("%Y%m%d%H%M%S"),
            "created_at": datetime.now().isoformat(),
            **body
        }
    except:
        return {"error": "Invalid request"}


# =============================================================================
# VERSION ENDPOINT
# =============================================================================

@app.get("/api/version")
async def get_version():
    """Get backend version."""
    return {
        "version": "1.0.0-sidecar",
        "mode": "desktop",
        "build": "pyinstaller",
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Aurity Backend Sidecar")
    parser.add_argument("--port", type=int, default=7051, help="Port to run on")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Aurity Backend (Sidecar Mode)")
    print("=" * 60)
    print(f"  Port:     {args.port}")
    print(f"  Time:     {datetime.now().isoformat()}")
    print("=" * 60)
    
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
