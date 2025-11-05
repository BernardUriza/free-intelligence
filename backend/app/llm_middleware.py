"""FastAPI application with LLM middleware.

Re-exports the main app from main.py.
"""

from __future__ import annotations

from backend.app.main import app, create_app

__all__ = ["app", "create_app"]
