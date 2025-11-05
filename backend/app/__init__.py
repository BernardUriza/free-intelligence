"""FastAPI application, middlewares, and entry points."""

from __future__ import annotations

from backend.app.main import app, create_app

__all__ = ["create_app", "app"]
