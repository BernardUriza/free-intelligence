"""FI Consult Service - FastAPI application.

Re-exports the main app for backward compatibility.
"""

from __future__ import annotations

from backend.app.main import app, create_app

__all__ = ["app", "create_app"]
