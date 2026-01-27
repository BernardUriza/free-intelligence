"""FiCoder service for qwen-code CLI integration."""

from __future__ import annotations


class FiCoderService:
    """Simple service providing qwen-code API router."""

    def get_api_router(self):
        """Get the FastAPI router for qwen-code endpoints."""
        from .api.router import router

        return router
