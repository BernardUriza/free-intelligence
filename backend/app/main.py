"""FastAPI application entry point.

Creates and configures the main FastAPI app with all routers and middleware.

Architecture:
- Public API (/api/workflows, /api/system): CORS enabled, orchestrators only
- Internal API (/internal/*): Localhost-only in production, atomic resources

AURITY-ONLY: All non-AURITY routers removed (FI-STRIDE apps deprecated)
Refactored: 2025-11-14 (Pruned unused endpoints)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC

import os
from backend.app.version import __version__
from backend.middleware.idempotency import IdempotencyMiddleware
from backend.middleware.internal_only import InternalOnlyMiddleware
from backend.middleware.tracing import TracingMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown events."""
    # Startup
    # from backend.utils.coder.storage.database import init_db  # Removed: storage simplified
    from backend.utils.coder.observability.logger import get_logger

    # Configure structured JSON logging for chat observability
    try:
        from backend.observability.logging import setup_json_logging

        setup_json_logging()
    except Exception:
        pass

    logger = get_logger(__name__)
    try:
        # init_db()  # Removed: storage simplified
        logger.info("DATABASE_INITIALIZED", status="success")
    except Exception as e:
        logger.error("DATABASE_INIT_FAILED", error=str(e))
        # Don't fail startup - continue with other services

    # Configure Event Bus with HDF5 store
    try:
        from backend.core.infrastructure.events.application.event_bus import configure_event_bus
        from backend.core.infrastructure.events.infrastructure.hdf5_store import HDF5EventStore

        event_store = HDF5EventStore()
        configure_event_bus(event_store)
        logger.info("EVENT_BUS_INITIALIZED", store="HDF5EventStore")
    except Exception as e:
        logger.warning("EVENT_BUS_INIT_FAILED", error=str(e))
        # Don't fail startup - events will be fire-and-forget without persistence

    yield

    # Shutdown (if needed in the future)
    # Add cleanup code here


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
- **Audio Transcription** - Deepgram speech-to-text (Azure Whisper endpoint removed)
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
- `DEEPGRAM_API_KEY` - Deepgram transcription (required)

### 📖 **Quick Start**
1. Check health: `GET /health`
2. View all endpoints: `GET /`
3. Try the AI assistant with the example above
"""

    # Tags for better organization
    tags_metadata = [
        {
            "name": "authentication",
            "description": "JWT authentication and RBAC for HIPAA compliance (G-003)",
        },
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
            "description": "Audio to text transcription using Deepgram",
        },
        {
            "name": "Sessions",
            "description": "Medical consultation session management",
        },
        {
            "name": "Patients",
            "description": "Patient demographic and identity records (PostgreSQL)",
        },
        {
            "name": "Providers",
            "description": "Healthcare provider credentials and specialty information (PostgreSQL)",
        },
        {
            "name": "Audit",
            "description": "Read-only audit logs for HIPAA compliance (FI-UI-FEAT-206)",
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
        lifespan=lifespan,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "docExpansion": "list",
            "filter": True,
        },
    )

    # Development-friendly fallback CORS: ensure browser dev servers (e.g. Next.js on :9000)
    # can access backend even if sub-app mounting fails during fast-refresh. This is
    # intentionally only enabled in non-production environments to avoid loosening CORS
    # in production.
    _env = os.getenv("ENVIRONMENT", os.getenv("ENV", "development"))
    if _env != "production":
        _dev_origins = [
            "http://localhost:9000",
            "http://127.0.0.1:9000",
            "http://localhost:9050",
            "http://127.0.0.1:9050",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=_dev_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    # Add explicit OPTIONS handler for CORS preflight requests
    # This ensures OPTIONS requests don't return 405 Method Not Allowed
    @app.options("/{full_path:path}", include_in_schema=False)
    async def options_handler(full_path: str):
        """Handle CORS preflight OPTIONS requests for all paths."""
        return {}

    # Sub-app: Public API (orchestrators, CORS enabled)
    public_app = FastAPI(title="Public API")

    # P2: Distributed tracing (must be first middleware - outermost layer)
    public_app.add_middleware(TracingMiddleware)

    # CORS configuration: more restrictive in production
    environment = os.getenv("ENVIRONMENT", os.getenv("ENV", "development"))

    if environment == "production":
        # In production, ALLOWED_ORIGINS must be explicitly set
        allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
        if not allowed_origins_str:
            raise ValueError(
                "ALLOWED_ORIGINS must be set in production environment. "
                "This is required for CORS security."
            )
        allowed_origins = [
            origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()
        ]
        allowed_headers = ["Content-Type", "Authorization", "X-Requested-With"]
    else:
        # In development, allow localhost origins
        allowed_origins = [
            "http://localhost:9000",
            "http://localhost:9050",
            "http://127.0.0.1:9000",
            "http://127.0.0.1:9050",
            "http://localhost:3000",  # Next.js dev server
            "http://127.0.0.1:3000",
            "http://localhost:8850",  # Art Collection dev server
            "http://127.0.0.1:8850",
        ]
        # Also allow any explicitly configured origins
        explicit_origins = os.getenv("ALLOWED_ORIGINS", "")
        if explicit_origins:
            allowed_origins.extend(
                [origin.strip() for origin in explicit_origins.split(",") if origin.strip()]
            )
        allowed_headers = ["*"]  # More permissive in development

    public_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=allowed_headers,
    )

    # P1: Idempotency middleware for workflow orchestration (prevents duplicate POST operations)
    public_app.add_middleware(
        IdempotencyMiddleware,
        paths=["/workflows/"],  # Relative to /api prefix
        require_key=False,  # Optional for now (non-breaking change)
        ttl=3600,  # 1 hour cache
    )

    # Sub-app: Internal API (atomic resources, CORS for dev, localhost-only)
    internal_app = FastAPI(title="Internal API")

    # P2: Distributed tracing (must be first middleware)
    internal_app.add_middleware(TracingMiddleware)

    # Add CORS for development (showcase testing)
    # Internal API uses same CORS config as public API
    internal_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=allowed_headers,
    )
    internal_app.add_middleware(InternalOnlyMiddleware)

    # Register all API routers (extracted to routers.py for maintainability)
    try:
        from backend.app.routers import init_observability, register_routers

        init_observability()
        register_routers(public_app, internal_app)

        # Mount sub-apps
        app.mount("/api", public_app)
        app.mount("/internal", internal_app)
    except (ImportError, AttributeError) as e:
        # If routers fail to load, log and continue with health check only
        import sys

        # Provide clearer guidance for missing dependencies or import errors
        print("WARNING: Failed to load API routers during startup.", file=sys.stderr)
        print(
            "This usually means a required Python package is missing or an import failed.",
            file=sys.stderr,
        )
        print(
            "Try: `pip install -r backend/requirements.txt` and restart the server.",
            file=sys.stderr,
        )
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()

    # Development-only debug route: list all mounted routes and methods
    # This helps frontend devs discover available endpoints without opening FastAPI docs.
    if environment != "production":

        @app.get("/__debug_routes")
        async def _debug_routes() -> dict:
            routes = []
            for r in app.routes:
                try:
                    path = getattr(r, "path", None) or getattr(r, "url", None) or str(r)
                    methods = sorted([m for m in getattr(r, "methods", []) if m not in ("HEAD",)])
                    routes.append(
                        {
                            "path": path,
                            "methods": methods,
                            "name": getattr(r, "name", None),
                        }
                    )
                except Exception:
                    continue
            # Sort for stable output
            routes = sorted(routes, key=lambda x: (x.get("path") or ""))
            return {"routes": routes, "count": len(routes)}

    # Include system routes on main app for root-level access (/health, /version, /llm/health)
    # Note: These also exist on public_app for /api/* paths
    from backend.app.system_routes import get_api_info
    from backend.app.system_routes import router as system_router_app

    @app.get("/")
    async def root() -> dict:
        """Root endpoint - API discovery and system information."""
        return get_api_info()

    app.include_router(system_router_app)

    # P2: Prometheus metrics endpoint for observability
    from backend.utils.metrics import setup_metrics_endpoint

    setup_metrics_endpoint(app)

    # Startup validation: ensure critical env vars are present in production
    env_now = os.getenv("ENVIRONMENT", os.getenv("ENV", "development"))
    if env_now == "production":
        # Azure OpenAI TTS is the required TTS provider
        has_azure_openai = bool(
            os.getenv("AZURE_OPENAI_TTS_API_KEY") or os.getenv("AZURE_TTS_API_KEY")
        )

        if not has_azure_openai:
            # Fail fast in production to avoid confusing 500 errors at runtime
            raise ValueError(
                "TTS provider must be configured in production. "
                "Set AZURE_OPENAI_TTS_API_KEY and AZURE_OPENAI_TTS_ENDPOINT"
            )

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
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Aurity Backend Server")
    parser.add_argument("--port", type=int, default=7001, help="Port to run on (default: 7001)")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind (default: 0.0.0.0)"
    )
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
