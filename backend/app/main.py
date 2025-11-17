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
    # Main app (no global CORS, uses sub-apps)
    app = FastAPI(
        title="Free Intelligence",
        description="Advanced Universal Reliable Intelligence for Telemedicine Yield",
        version="0.1.0",
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
        public_app.include_router(public.system.router, prefix="/system", tags=["system"])

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
        from datetime import datetime, timezone

        environment = os.getenv("ENVIRONMENT", "development")

        return {
            "service": {
                "name": "Free Intelligence",
                "codename": "AURITY",
                "description": "Advanced Universal Reliable Intelligence for Telemedicine Yield",
                "version": "0.1.0",
                "environment": environment,
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
