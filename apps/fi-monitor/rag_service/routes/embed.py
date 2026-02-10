"""Embed texts endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

import state
from auth import verify_api_key
from config import EMBEDDING_MODEL
from gpu import DEVICE
from schemas import EmbedRequest, EmbedResponse

router = APIRouter()


@router.post("/rag/embed", response_model=EmbedResponse)
async def embed_texts(
    request: EmbedRequest,
    _auth: None = Depends(verify_api_key),
) -> EmbedResponse:
    """Generate embeddings for texts with GPU acceleration.

    SECURITY: Requires API key authentication.

    Args:
        request: List of texts to embed

    Returns:
        Embeddings with metadata

    Example:
        curl -X POST http://localhost:11435/rag/embed \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"texts": ["hello world"]}'
    """
    if state._model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded yet",
        )

    # Generate embeddings
    try:
        embeddings = state._model.encode(
            request.texts,
            batch_size=32,
            convert_to_numpy=True,
            show_progress_bar=False,
            device=DEVICE,
        )

        return EmbedResponse(
            embeddings=embeddings.tolist(),
            device=DEVICE,
            model=EMBEDDING_MODEL,
            count=len(embeddings),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {e}",
        )
