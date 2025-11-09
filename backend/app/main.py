"""FastAPI application entry point.

Creates and configures the main FastAPI app with all routers and middleware.

Architecture:
- Public API (/api/workflows, /api/katniss): CORS enabled, orchestrators only
- Internal API (/internal/*): No CORS, atomic resources, localhost-only in production
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    # Sub-app: Internal API (atomic resources, no CORS, localhost-only)
    internal_app = FastAPI(title="Internal API")
    internal_app.add_middleware(InternalOnlyMiddleware)

    # Include all API routers (lazy load to avoid circular imports)
    try:
        from backend.api import (
            athlete_sessions,
            athletes,
            audit,
            coaches,
            diarization,
            exports,
            fi_diag,
            katniss,
            kpis,
            library,
            session_designs,
            sessions,
            system,
            t21_resources,
            timeline_verify,
            transcribe,
            triage,
            workflows,
        )

        # PUBLIC API (CORS enabled, orchestrators)
        public_app.include_router(workflows.router)  # Aurity orchestrator
        public_app.include_router(katniss.router)
        public_app.include_router(t21_resources.router)
        public_app.include_router(system.router, prefix="/system", tags=["system"])

        # INTERNAL API (no CORS, atomic resources, localhost-only)
        internal_app.include_router(
            athlete_sessions.router, prefix="/athlete-sessions", tags=["athlete-sessions"]
        )
        internal_app.include_router(athletes.router, prefix="/athletes", tags=["athletes"])
        internal_app.include_router(audit.router, prefix="/audit", tags=["audit"])
        internal_app.include_router(coaches.router, prefix="/coaches", tags=["coaches"])
        internal_app.include_router(diarization.router, prefix="/diarization", tags=["diarization"])
        internal_app.include_router(exports.router, prefix="/exports", tags=["exports"])
        internal_app.include_router(fi_diag.router, prefix="/fi-diag", tags=["fi-diag"])
        internal_app.include_router(kpis.router, prefix="/kpis", tags=["kpis"])
        internal_app.include_router(library.router, prefix="/library", tags=["library"])
        internal_app.include_router(
            session_designs.router, prefix="/session-designs", tags=["session-designs"]
        )
        internal_app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
        internal_app.include_router(timeline_verify.router, prefix="/timeline", tags=["timeline"])
        internal_app.include_router(triage.router, prefix="/triage", tags=["triage"])
        internal_app.include_router(transcribe.router, prefix="/transcribe", tags=["transcribe"])

        # Mount sub-apps
        app.mount("/api", public_app)
        app.mount("/internal", internal_app)
    except (ImportError, AttributeError) as e:
        # If routers fail to load, log and continue with health check only
        import sys

        print(f"WARNING: Failed to load routers: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7001)
