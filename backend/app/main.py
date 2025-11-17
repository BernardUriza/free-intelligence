"""FastAPI application entry point.

Creates and configures the main FastAPI app with all routers and middleware.

Architecture:
- Public API (/api/workflows, /api/system): CORS enabled, orchestrators only
- Internal API (/internal/*): Localhost-only in production, atomic resources

AURITY-ONLY: All non-AURITY routers removed (FI-STRIDE apps deprecated)
Refactored: 2025-11-14 (Pruned unused endpoints)
"""

from __future__ import annotations

import os
from datetime import UTC
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.middleware import InternalOnlyMiddleware


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    # Enhanced documentation
    description = """
## 🏥 Free Intelligence - Medical AI Platform

### 🤖 **AI-Powered Medical Assistant**
Process natural language commands to update medical records using Claude AI.

### 🔑 **Key Features:**
- **AI Assistant** - Natural language processing with Claude
- **Audio Transcription** - Azure Whisper / Deepgram speech-to-text
- **SOAP Notes** - Structured medical documentation
- **HDF5 Storage** - Append-only data persistence

### 📚 **Main Endpoints:**

#### **AI Assistant** 🤖
```
POST /api/workflows/aurity/sessions/{session_id}/assistant
```
Send natural language commands like:
- "agrega que el paciente tiene diabetes tipo 2"
- "incluir alergia a penicilina"
- "nota: paciente hipertenso controlado"

#### **SOAP Notes** 📝
```
GET  /api/workflows/aurity/sessions/{session_id}/soap
PUT  /api/workflows/aurity/sessions/{session_id}/soap
```

#### **Audio Transcription** 🎤
```
POST /api/workflows/aurity/stream
GET  /api/workflows/aurity/jobs/{session_id}
```

#### **Sessions** 📊
```
GET  /api/workflows/aurity/sessions
POST /api/workflows/aurity/sessions/{session_id}/finalize
```

### 🔐 **Configuration**
Requires environment variables:
- `CLAUDE_API_KEY` - Anthropic Claude API
- `AZURE_OPENAI_KEY` - Azure Whisper transcription

### 📖 **Quick Start**
1. Check health: `GET /health`
2. View all endpoints: `GET /`
3. Try the AI assistant with the example above
"""

    # Tags for better organization
    tags_metadata = [
        {
            "name": "AI Assistant",
            "description": "Natural language medical assistant powered by Claude AI",
        },
        {
            "name": "SOAP Notes",
            "description": "Manage medical SOAP (Subjective, Objective, Assessment, Plan) notes",
        },
        {
            "name": "Transcription",
            "description": "Audio to text transcription using Azure Whisper",
        },
        {
            "name": "Sessions",
            "description": "Medical consultation session management",
        },
        {
            "name": "System",
            "description": "System health and monitoring",
        },
    ]

    # Main app (no global CORS, uses sub-apps)
    app = FastAPI(
        title="Free Intelligence",
        description=description,
        version="0.1.0",
        openapi_tags=tags_metadata,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "docExpansion": "list",
            "filter": True,
        },
    )

    # Sub-app: Public API (orchestrators, CORS enabled)
    public_app = FastAPI(title="Public API")
    allowed_origins = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:9000,http://localhost:9050"
    ).split(",")
    public_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Sub-app: Internal API (atomic resources, CORS for dev, localhost-only)
    internal_app = FastAPI(title="Internal API")

    # Add CORS for development (showcase testing)
    internal_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    internal_app.add_middleware(InternalOnlyMiddleware)

    # Include all API routers (lazy load to avoid circular imports)
    try:
        from backend.api import internal, public
        from backend.api.public.workflows import timeline

        # PUBLIC API (CORS enabled, orchestrators)
        public_app.include_router(public.workflows.router)  # AURITY orchestrator
        public_app.include_router(timeline.router)  # Timeline/sessions listing
        public_app.include_router(public.system.router, prefix="/system", tags=["System"])

        # INTERNAL API (atomic resources, AURITY-only)
        internal_app.include_router(internal.audit.router, prefix="/audit", tags=["audit"])
        internal_app.include_router(
            internal.diarization.router, prefix="/diarization", tags=["diarization"]
        )
        internal_app.include_router(internal.exports.router, prefix="/exports", tags=["exports"])
        internal_app.include_router(internal.kpis.router, prefix="/kpis", tags=["kpis"])
        internal_app.include_router(internal.sessions.router, prefix="/sessions", tags=["sessions"])
        internal_app.include_router(
            internal.sessions.checkpoint.router, prefix="", tags=["sessions-checkpoint"]
        )  # Session checkpoint - incremental audio concatenation
        internal_app.include_router(
            internal.sessions.finalize.router, prefix="", tags=["sessions-finalize"]
        )  # Session finalization + encryption + diarization
        internal_app.include_router(internal.triage.router, prefix="/triage", tags=["triage"])
        internal_app.include_router(
            internal.transcribe.router, prefix="/transcribe", tags=["transcribe"]
        )

        # Mount sub-apps
        app.mount("/api", public_app)
        app.mount("/internal", internal_app)
    except (ImportError, AttributeError) as e:
        # If routers fail to load, log and continue with health check only
        import sys

        print(f"WARNING: Failed to load routers: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()

    @app.get("/")
    async def root() -> dict:
        """Root endpoint - API discovery and system information.

        Well-designed root endpoint that acts as a directory for the API,
        providing essential information for developers discovering the service.
        """
        from datetime import datetime

        environment = os.getenv("ENVIRONMENT", "development")

        return {
            "service": {
                "name": "Free Intelligence",
                "codename": "AURITY",
                "description": "Advanced Universal Reliable Intelligence for Telemedicine Yield",
                "version": "0.1.0",
                "environment": environment,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            "status": {
                "operational": True,
                "message": "All systems operational",
            },
            "api": {
                "public": {
                    "base_url": "/api",
                    "description": "Public orchestration endpoints (CORS enabled)",
                    "endpoints": {
                        "workflows": "/api/workflows/aurity/*",
                        "sessions": "/api/workflows/aurity/sessions/*",
                        "timeline": "/api/sessions/*",
                        "system": "/api/system/*",
                    },
                },
                "internal": {
                    "base_url": "/internal",
                    "description": "Internal atomic resources (localhost-only in production)",
                    "note": "⚠️ Direct access blocked by InternalOnlyMiddleware in production",
                    "endpoints": {
                        "audit": "/internal/audit/*",
                        "diarization": "/internal/diarization/*",
                        "exports": "/internal/exports/*",
                        "kpis": "/internal/kpis/*",
                        "sessions": "/internal/sessions/*",
                        "transcribe": "/internal/transcribe/*",
                        "triage": "/internal/triage/*",
                    },
                },
            },
            "resources": {
                "health": "/health",
                "docs": "/docs",
                "openapi": "/openapi.json",
                "static": "/static",
            },
            "architecture": {
                "pattern": "Layered API (Public Orchestrators + Internal Resources)",
                "philosophy": "LAN-only, append-only HDF5, zero-cloud runtime",
                "security": "RBAC + PolicyEnforcer + InternalOnlyMiddleware",
            },
            "contact": {
                "repository": "https://github.com/BernardUriza/free-intelligence",
                "owner": "Bernard Uriza Orozco",
            },
            "examples": {
                "ai_assistant": {
                    "description": "Natural language SOAP modification",
                    "method": "POST",
                    "endpoint": "/api/workflows/aurity/sessions/{session_id}/assistant",
                    "body": {
                        "command": "agrega que el paciente tiene diabetes tipo 2 y es alérgico a penicilina",
                        "current_soap": {
                            "subjective": "Paciente refiere mareos frecuentes",
                            "objective": "PA: 140/90, Glucosa: 180 mg/dl",
                            "assessment": "Hipertensión arterial",
                            "plan": {
                                "medications": ["Metformina 850mg c/12h"],
                                "studies": ["Hemoglobina glucosilada"],
                            },
                        },
                    },
                    "expected_response": {
                        "updates": {
                            "pastMedicalHistory": "add_item:Diabetes mellitus tipo 2",
                            "allergies": "add_item:Penicilina",
                        },
                        "explanation": "Agregados diabetes tipo 2 y alergia a penicilina",
                        "success": True,
                    },
                },
                "get_soap": {
                    "description": "Retrieve SOAP note for a session",
                    "method": "GET",
                    "endpoint": "/api/workflows/aurity/sessions/{session_id}/soap",
                    "expected_response": {
                        "session_id": "test_001",
                        "soap_note": {
                            "subjective": "...",
                            "objective": "...",
                            "assessment": "...",
                            "plan": {},
                        },
                    },
                },
                "transcribe_audio": {
                    "description": "Upload audio chunk for transcription",
                    "method": "POST",
                    "endpoint": "/api/workflows/aurity/stream",
                    "body": "FormData with session_id, chunk_number, and audio file",
                    "expected_response": {
                        "status": "accepted",
                        "job_id": "session_id",
                        "message": "Audio chunk received",
                    },
                },
            },
            "quick_test": {
                "claude_ai": 'curl -X POST http://104.131.175.65:7001/api/workflows/aurity/sessions/test/assistant -H \'Content-Type: application/json\' -d \'{"command":"test","current_soap":{}}\'',
                "health": "curl http://104.131.175.65:7001/health",
                "sessions": "curl http://104.131.175.65:7001/api/workflows/aurity/sessions",
            },
        }

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    # Mount static files (for demo audio, etc.)
    # Note: StaticFiles doesn't inherit CORS from parent app, so we wrap it
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        static_app = StaticFiles(directory=str(static_dir))

        # Wrap with CORS for frontend access
        class CORSStaticFiles:
            def __init__(self, static_files):
                self.static_files = static_files

            async def __call__(self, scope, receive, send):
                if scope["type"] == "http":

                    async def send_with_cors(message):
                        if message["type"] == "http.response.start":
                            headers = list(message.get("headers", []))
                            headers.append((b"access-control-allow-origin", b"*"))
                            message["headers"] = headers
                        await send(message)

                    await self.static_files(scope, receive, send_with_cors)
                else:
                    await self.static_files(scope, receive, send)

        app.mount("/static", CORSStaticFiles(static_app), name="static")

    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7001)
