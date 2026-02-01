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
import sys

import os
from backend.app.version import __version__
from backend.middleware.idempotency import IdempotencyMiddleware
from backend.middleware.internal_only import InternalOnlyMiddleware
from backend.middleware.tracing import TracingMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import ValidationError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown events."""
    # Startup
    # from backend.utils.coder.storage.database import init_db  # Removed: storage simplified
    from backend.utils.coder.observability.logger import get_logger

    # P1: Validate all Pydantic configs FIRST (fail-fast on invalid config)
    validate_all_configs()

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

    # Verify Event Bus is accessible (Phase 2.3 Plutón - direct instantiation)
    try:
        from backend.infrastructure.events.event_bus import InMemoryEventBus
        _ = InMemoryEventBus()  # Verify EventBus can be instantiated
        logger.info("EVENT_BUS_READY", implementation="InMemoryEventBus", status="available")
    except Exception as e:
        logger.warning("EVENT_BUS_VERIFICATION_FAILED", error=str(e))
        # Don't fail startup - services will handle missing event bus gracefully

    yield

    # Shutdown (if needed in the future)
    # Add cleanup code here


def validate_all_configs() -> None:
    """Validate all Pydantic configs at startup (fail-fast).

    Validates type-safe configurations created in P0:
    - MemoryStoreConfig
    - TranscriptionConfig
    - WorkflowConfig
    - SOAPConfig
    - LLMClientConfig

    Raises:
        ValidationError: If any config is invalid (e.g., timeout_read <= 0)
        RuntimeError: If config validation fails
    """
    from backend.utils.common.logging.logger import get_logger

    logger = get_logger(__name__)

    try:
        # Import and validate all configs (triggers Pydantic validation)
        from backend.services.memory.dependencies import get_memory_config
        from backend.services.transcription.dependencies import get_transcription_config
        from backend.services.workflow.dependencies import get_workflow_config
        from backend.services.soap.dependencies import get_soap_config
        from backend.clients.dependencies import get_llm_client_config

        configs = {
            "MemoryStoreConfig": get_memory_config(),
            "TranscriptionConfig": get_transcription_config(),
            "WorkflowConfig": get_workflow_config(),
            "SOAPConfig": get_soap_config(),
            "LLMClientConfig": get_llm_client_config(),
        }

        logger.info(
            "CONFIG_VALIDATION_SUCCESS",
            config_count=len(configs),
            configs=list(configs.keys()),
        )

    except ValidationError as e:
        error_details = "\n".join([
            f"  - {err['loc'][0] if err['loc'] else 'unknown'}: {err['msg']}"
            for err in e.errors()
        ])
        error_msg = (
            "❌ STARTUP FAILED - Invalid configuration detected:\n"
            f"{error_details}\n\n"
            "Fix the configuration errors in environment variables and restart."
        )
        logger.error("CONFIG_VALIDATION_FAILED", error=str(e), exc_info=True)
        print(error_msg, file=sys.stderr)
        sys.exit(1)  # Fail fast

    except Exception as e:
        logger.error("CONFIG_VALIDATION_UNEXPECTED_ERROR", error=str(e), exc_info=True)
        print(f"❌ UNEXPECTED ERROR during config validation: {e}", file=sys.stderr)
        sys.exit(1)  # Fail fast


def validate_critical_env_vars() -> None:
    """Validate that all critical environment variables are present in production.

    Fails fast with clear error messages to prevent runtime failures.

    Raises:
        RuntimeError: If any critical env var is missing in production
    """
    env = os.getenv("ENVIRONMENT", os.getenv("ENV", "development"))
    if env != "production":
        return  # Skip validation in development

    # Critical env vars that MUST be present in production
    CRITICAL_ENV_VARS = {
        "CLAUDE_API_KEY": "AI assistant won't work without Claude API",
        "DEEPGRAM_API_KEY": "Audio transcription won't work without Deepgram",
        "DATABASE_URL": "PostgreSQL connection required for patients/providers",
        "ALLOWED_ORIGINS": "CORS will block frontend without allowed origins",
    }

    missing = []
    for var, reason in CRITICAL_ENV_VARS.items():
        if not os.getenv(var):
            missing.append(f"  - {var}: {reason}")

    if missing:
        error_msg = (
            "❌ PRODUCTION STARTUP FAILED - Missing critical environment variables:\n"
            + "\n".join(missing)
            + "\n\nSet these env vars before deploying to production."
        )
        raise RuntimeError(error_msg)


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    # Validate critical env vars FIRST (fail fast in production)
    validate_critical_env_vars()
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

    # Middleware stack (outside-in execution order):
    # 1. CORS - Fail fast on origin mismatch (outermost)
    # 2. Tracing - Only trace valid origins
    # 3. Idempotency - Only check cache for valid routes (innermost)
    public_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=allowed_headers,
    )

    # P2: Distributed tracing (after CORS to avoid tracing preflight noise)
    public_app.add_middleware(TracingMiddleware)

    # P1: Idempotency middleware for workflow orchestration (prevents duplicate POST operations)
    public_app.add_middleware(
        IdempotencyMiddleware,
        paths=["/workflows/"],  # Relative to /api prefix
        require_key=False,  # Optional for now (non-breaking change)
        ttl=3600,  # 1 hour cache
    )

    # Sub-app: Internal API (atomic resources, CORS for dev, localhost-only)
    internal_app = FastAPI(title="Internal API")

    # Middleware stack (same order as public_app):
    # 1. CORS - Fail fast on origin mismatch
    # 2. Tracing - Only trace valid origins
    # 3. InternalOnly - Localhost enforcement (innermost)
    internal_app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=allowed_headers,
    )

    # P2: Distributed tracing (after CORS)
    internal_app.add_middleware(TracingMiddleware)

    # P3: Internal-only enforcement (localhost check)
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
        import sys
        import traceback

        # Provide clearer guidance for missing dependencies or import errors
        print("❌ FATAL: Failed to load API routers during startup.", file=sys.stderr)
        print(
            "This usually means a required Python package is missing or an import failed.",
            file=sys.stderr,
        )
        print(
            "Try: `pip install -r backend/requirements.txt` and restart the server.",
            file=sys.stderr,
        )
        print(f"Error: {e}", file=sys.stderr)
        traceback.print_exc()

        # FAIL FAST in production - don't start app without routers
        if environment == "production":
            raise RuntimeError(
                "Cannot start app in production without API routers. "
                "This would result in all /api/* endpoints returning 404."
            ) from e
        # In development, log warning and continue (allow health check only)
        print("⚠️  DEV MODE: Continuing without routers (health check only)", file=sys.stderr)

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

    # Mount static files (for demo audio, etc.)
    # Note: StaticFiles mounted on main app (not sub-apps) to avoid CORS complexity
    static_dir = Path(__file__).parent.parent / "static"
    if static_dir.exists():
        # Static files inherit CORS from main app's fallback middleware (development)
        # In production, static files should be served by Nginx/CDN, not FastAPI
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


# Create app instance for uvicorn
app = create_app()

# Export public_app for dependency injection testing
# This allows tests to override dependencies on the correct sub-app
public_app = None
for route in app.routes:
    if hasattr(route, 'path') and route.path == '/api':
        # Found the mounted public API sub-app
        public_app = route.app
        break


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
