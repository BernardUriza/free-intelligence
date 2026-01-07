"""FastAPI application, middlewares, and entry points."""

from __future__ import annotations

from backend.app.main import app, create_app
from backend.app.version import __version__

__all__ = ["__version__", "app", "create_app"]
