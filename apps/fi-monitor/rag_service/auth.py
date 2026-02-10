"""FastAPI dependency for API key authentication."""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from config import RAG_API_KEY


async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")):
    """Verify the X-API-Key header matches the configured key."""
    if x_api_key != RAG_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
