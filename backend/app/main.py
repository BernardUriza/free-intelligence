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
    # from backend.src.fi_coder.storage.database import init_db  # Removed: storage simplified
    from backend.src.fi_coder.observability.logger import get_logger

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
        from backend.src.fi_events.application.event_bus import configure_event_bus
        from backend.src.fi_events.infrastructure.hdf5_store import HDF5EventStore

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
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=allowed_headers,
    )
    internal_app.add_middleware(InternalOnlyMiddleware)

    # Include all API routers (lazy load to avoid circular imports)
    try:
        from backend.src.fi_admin.api.internal.admin.users import (
            router as users_router,  # Admin user management
        )
        from backend.src.fi_assistant.api.public import aurity_personas  # , personas_admin

        # Internal API imports
        from backend.src.fi_audit.api.internal.audit import router as internal_audit_router
        from backend.src.fi_audit.api.public import audit
        from backend.src.fi_auth.adapters.fastapi_adapter import auth_router
        from backend.src.fi_checkin.api.public import checkin
        from backend.src.fi_clinic.api.public import clinics
        from backend.src.fi_coder.api.internal.fi_coder import router as fi_coder_router
        from backend.src.fi_common.api.internal.exports import router as exports_router
        from backend.src.fi_common.api.public import notifications
        from backend.src.fi_kpi.api.internal.kpis import router as kpis_router
        from backend.src.fi_license.api.internal import router as licenses_admin_router
        from backend.src.fi_license.api.public import router as licenses_router
        from backend.src.fi_llm.api.internal.llm import router as llm_router
        from backend.src.fi_llm.api.public import llm_models_admin
        from backend.src.fi_model_catalog.api.public import catalog_admin
        from backend.src.fi_patient.api.public import patients
        from backend.src.fi_payment.api.public import payments
        from backend.src.fi_policy.api.public import policy
        from backend.src.fi_provider.api.public import providers
        from backend.src.fi_session.api.internal.sessions import router as sessions_router

        # from backend.src.fi_session.api.internal.sessions.checkpoint import (
        #     router as sessions_checkpoint_router,
        # )
        from backend.src.fi_session.api.internal.sessions.finalize import (
            router as sessions_finalize_router,
        )
        from backend.src.fi_system.api.public import system_resources
        from backend.src.fi_timeline.api.internal.timeline import router as timeline_internal_router
        from backend.src.fi_timeline.api.public import timeline
        from backend.src.fi_transcription.api.internal.diarization import (
            router as diarization_router,
        )
        from backend.src.fi_transcription.api.internal.transcribe import router as transcribe_router
        from backend.src.fi_tts.api.public import tts
        from backend.src.fi_user.api.public import user_clinic
        from backend.src.fi_workflow.api.internal.triage import router as triage_router

        # Observability (LLM call logging for FI Edge Monitor)
        from backend.src.fi_observability.api import router as observability_router
        from backend.src.fi_observability import init_observability_db

        # Initialize observability database on startup
        try:
            init_observability_db()
        except Exception as obs_err:
            pass  # Non-critical, log to structlog in observability module

        # Import individual routers from new fi_* package structure
        from backend.src.fi_workflow.api.public.workflows_router import (
            router as public_workflows_router,
        )

        # PUBLIC API (CORS enabled, orchestrators)
        public_app.include_router(auth_router)  # Auth0 Authentication (HIPAA G-003)
        public_app.include_router(public_workflows_router)  # AURITY orchestrator
        public_app.include_router(timeline.router)  # Timeline/sessions listing
        public_app.include_router(aurity_personas.router)  # Personas list (public)
        public_app.include_router(patients.router)  # Patient CRUD (FI-DATA-DB-001)
        public_app.include_router(providers.router)  # Provider CRUD (FI-DATA-DB-001)
        # NOTE: System router moved to workflows/system.py (/api/workflows/aurity/system/*)
        public_app.include_router(
            audit.router, prefix="/audit", tags=["Audit"]
        )  # Audit logs (FI-UI-FEAT-206)
        public_app.include_router(policy.router)  # Policy viewer (FI-UI-FEAT-204)
        # public_app.include_router(personas_admin.router)  # Personas Admin (FI-UI-DESIGN-003)
        public_app.include_router(tts.router)  # Text-to-Speech (Azure OpenAI)
        public_app.include_router(checkin.router)  # FI Receptionist Check-in (FI-CHECKIN-001)
        public_app.include_router(payments.router)  # Stripe Payments (FI-CHECKIN-002)
        public_app.include_router(clinics.router)  # Clinic/Doctor CRUD (FI-CHECKIN-002)
        public_app.include_router(
            user_clinic.router
        )  # User-Clinic membership (link Auth0 user to clinic)
        public_app.include_router(notifications.router)  # SMS/Email Notifications (FI-CHECKIN-003)
        public_app.include_router(llm_models_admin)  # LLM Models Admin (superadmin CRUD)
        public_app.include_router(
            catalog_admin.router
        )  # Model Catalog (GPT4All, HuggingFace, Ollama)
        public_app.include_router(
            system_resources.router
        )  # System Resources Monitor (RAM, Running Models)
        public_app.include_router(observability_router)  # LLM Observability (FI Edge Monitor)
        public_app.include_router(licenses_router)  # License renewal API (Desktop App renewals)
        public_app.include_router(
            licenses_admin_router
        )  # License generation (superadmin only, needs frontend access)
        # NOTE: Assistant router now in workflows/assistant.py (AURITY-specific)

        # INTERNAL API (atomic resources, AURITY-only)
        internal_app.include_router(internal_audit_router, prefix="/audit", tags=["audit"])
        internal_app.include_router(diarization_router, prefix="/diarization", tags=["diarization"])
        internal_app.include_router(exports_router, prefix="/exports", tags=["exports"])
        # Timeline internal compatibility router (verify-hash)
        internal_app.include_router(
            timeline_internal_router
        )  # No hasattr check - let it fail if missing
        internal_app.include_router(kpis_router, prefix="/kpis", tags=["kpis"])
        internal_app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
        # internal_app.include_router(
        #     sessions_checkpoint_router, prefix="", tags=["sessions-checkpoint"]
        # )  # Session checkpoint - incremental audio concatenation
        internal_app.include_router(
            sessions_finalize_router, prefix="", tags=["sessions-finalize"]
        )  # Session finalization + encryption + diarization
        internal_app.include_router(triage_router, prefix="/triage", tags=["triage"])
        internal_app.include_router(transcribe_router, prefix="/transcribe", tags=["transcribe"])
        internal_app.include_router(
            llm_router
        )  # Ultra observable LLM layer (prefix already in router)
        internal_app.include_router(
            users_router, tags=["admin"]
        )  # Admin user management (Auth0 Management API)
        internal_app.include_router(
            fi_coder_router, prefix="/fi_coder", tags=["fi_coder"]
        )  # FI Coder task orchestrator

        # Add health/version endpoints to public_app (they must be here, not on app,
        # because app.mount("/api", public_app) captures ALL /api/* routes)
        @public_app.get("/health")
        async def public_health_check() -> dict[str, str]:
            """Health check endpoint (on /api prefix)."""
            return {"status": "ok"}

        @public_app.get("/")
        async def public_root() -> dict:
            """Root endpoint for /api/ path."""
            from datetime import datetime

            return {
                "service": "AURITY",
                "version": "0.1.1",
                "status": "operational",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        @public_app.get("/llm/health")
        async def public_llm_health() -> dict:
            """LLM health check for /api/llm/health."""
            import asyncio

            import requests as req

            def _check_ollama() -> dict:
                try:
                    response = req.get("http://localhost:11434/api/tags", timeout=2)
                    if response.status_code == 200:
                        data = response.json()
                        models = [m.get("name", "") for m in data.get("models", [])]
                        return {
                            "status": "ok",
                            "ollama": True,
                            "models": models,
                            "model_count": len(models),
                        }
                    return {"status": "degraded", "ollama": False, "models": [], "model_count": 0}
                except Exception as e:
                    return {"status": "degraded", "ollama": False, "models": [], "error": str(e)}

            return await asyncio.to_thread(_check_ollama)

        @public_app.get("/version")
        async def public_version() -> dict:
            """Version endpoint for /api/version."""
            from datetime import datetime

            return {
                "service": "AURITY",
                "version": "0.1.1",
                "build_timestamp": datetime.now(UTC).isoformat(),
                "environment": os.getenv("ENVIRONMENT", "development"),
            }

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

    @app.get("/")
    @app.get("/api")
    @app.get("/api/")
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
                        "assistant": "/api/workflows/aurity/assistant/*",
                        "timeline": "/api/sessions/*",
                        "audit": "/api/audit/*",
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
                        "llm": "/internal/llm/*",
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
    @app.get("/api/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/api/llm/health")
    async def llm_health_check() -> dict:
        """LLM health check endpoint for CI/CD validation.

        Checks if Ollama is available and lists models.
        Used by E2E tests to verify LLM infrastructure.
        """
        import asyncio

        import requests as req

        def _check_ollama() -> dict:
            """Sync helper to check Ollama - runs in threadpool."""
            try:
                response = req.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    return {
                        "status": "ok",
                        "ollama": True,
                        "models": models,
                        "model_count": len(models),
                    }
                return {"status": "degraded", "ollama": False, "models": [], "model_count": 0}
            except Exception as e:
                return {
                    "status": "degraded",
                    "ollama": False,
                    "models": [],
                    "model_count": 0,
                    "error": str(e),
                }

        # Run blocking request in threadpool to avoid blocking event loop
        return await asyncio.to_thread(_check_ollama)

    @app.get("/version")
    @app.get("/api/version")
    async def version_info() -> dict:
        """Version endpoint for E2E testing.

        Returns version info and sample Python code for validation.
        This endpoint is used by CI/CD to verify successful deployment.
        """
        from datetime import datetime

        version = "0.1.1"
        build_timestamp = datetime.now(UTC).isoformat()

        # Python code that validates the system is working
        python_e2e_code = f'''#!/usr/bin/env python3
"""
AURITY E2E Validation Script
Generated: {build_timestamp}
Version: {version}
"""
import requests
import sys

def validate_aurity(base_url: str = "https://app.aurity.io") -> bool:
    """Validate AURITY deployment is working."""
    checks = []

    # 1. Health check
    try:
        r = requests.get(f"{{base_url}}/api/health", timeout=5)
        checks.append(("health", r.status_code == 200))
    except Exception as e:
        checks.append(("health", False))

    # 2. Version endpoint (this one)
    try:
        r = requests.get(f"{{base_url}}/api/version", timeout=5)
        data = r.json()
        checks.append(("version", data.get("version") == "{version}"))
    except Exception as e:
        checks.append(("version", False))

    # 3. Root endpoint
    try:
        r = requests.get(f"{{base_url}}/api/", timeout=5)
        data = r.json()
        checks.append(("root", data.get("service", {{}}).get("codename") == "AURITY"))
    except Exception as e:
        checks.append(("root", False))

    # Report
    print(f"AURITY E2E Validation - {{base_url}}")
    print("-" * 40)
    all_pass = True
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {{status}} {{name}}")
        if not passed:
            all_pass = False

    print("-" * 40)
    if all_pass:
        print("✅ All checks passed!")
    else:
        print("❌ Some checks failed")

    return all_pass

if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "https://app.aurity.io"
    success = validate_aurity(base)
    sys.exit(0 if success else 1)
'''

        return {
            "service": "AURITY",
            "version": version,
            "build_timestamp": build_timestamp,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "python_e2e_code": python_e2e_code,
            "usage": {
                "curl": "curl -s https://app.aurity.io/version | jq -r .python_e2e_code | python3",
                "save": "curl -s https://app.aurity.io/version | jq -r .python_e2e_code > validate.py && python3 validate.py",
            },
        }

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
