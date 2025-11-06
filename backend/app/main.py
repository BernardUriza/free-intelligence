"""FastAPI application entry point.

Creates and configures the main FastAPI app with all routers and middleware.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="Free Intelligence",
        description="Advanced Universal Reliable Intelligence for Telemedicine Yield",
        version="0.1.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all API routers (lazy load to avoid circular imports)
    try:
        from backend.api import (
            audit,
            diarization,
            exports,
            fi_diag,
            katniss,
            kpis,
            library,
            sessions,
            system,
            t21_resources,
            timeline_verify,
            transcribe,
            triage,
        )

        app.include_router(audit.router, prefix="/api/audit", tags=["audit"])
        app.include_router(diarization.router, prefix="/api/diarization", tags=["diarization"])
        app.include_router(exports.router, prefix="/api/exports", tags=["exports"])
        app.include_router(fi_diag.router, prefix="/api/fi-diag", tags=["fi-diag"])
        app.include_router(katniss.router)
        app.include_router(kpis.router, prefix="/api/kpis", tags=["kpis"])
        app.include_router(library.router)
        app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
        app.include_router(system.router, prefix="/api/system", tags=["system"])
        app.include_router(t21_resources.router)
        app.include_router(timeline_verify.router, prefix="/api/timeline", tags=["timeline"])
        app.include_router(triage.router, prefix="/api/triage", tags=["triage"])
        app.include_router(transcribe.router, prefix="/api/transcribe", tags=["transcribe"])
    except (ImportError, AttributeError) as e:
        # If routers fail to load, log and continue with health check only
        import sys

        print(f"WARNING: Failed to load routers: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()

    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "ok"}

    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7001)
