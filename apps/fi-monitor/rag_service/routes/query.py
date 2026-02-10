"""RAG query endpoint."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status

import state
from auth import verify_api_key
from gpu import DEVICE
from schemas import RAGQueryRequest, RAGQueryResponse
from text_processing import preprocess_query

router = APIRouter()


@router.post("/rag/query", response_model=RAGQueryResponse)
async def query_documents(
    request: RAGQueryRequest,
    _auth: None = Depends(verify_api_key),
) -> RAGQueryResponse:
    """Query stored documents using semantic search (with query preprocessing).

    SECURITY: Requires API key authentication.

    Args:
        request: Query request with question and optional filename filter

    Returns:
        Top-K most relevant chunks with similarity scores

    Example:
        curl -X POST http://localhost:11435/rag/query \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"query":"What was the diagnosis?","top_k":3}'
    """
    if state._model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded yet",
        )

    if not state._document_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents uploaded yet. Upload a PDF first.",
        )

    try:
        # 1. Preprocess query (remove filler words for better matching)
        processed_query = preprocess_query(request.query)

        # 2. Generate query embedding (use processed query)
        query_embedding = state._model.encode(
            [processed_query],
            convert_to_numpy=True,
            show_progress_bar=False,
            device=DEVICE,
        )[0]  # Get first (and only) embedding

        # 3. Search all documents (or only the specified one)
        all_results = []

        docs_to_search = [request.filename] if request.filename else list(state._document_store.keys())

        for filename in docs_to_search:
            if filename not in state._document_store:
                continue

            doc_data = state._document_store[filename]
            chunks = doc_data["chunks"]
            embeddings = doc_data["embeddings"]

            # 4. Compute cosine similarity
            # Normalize vectors
            query_norm = query_embedding / np.linalg.norm(query_embedding)
            embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

            # Compute similarities
            similarities = embeddings_norm @ query_norm

            # 5. Get top-K results for this document
            top_indices = np.argsort(similarities)[::-1][:request.top_k]

            for idx in top_indices:
                all_results.append({
                    "filename": filename,
                    "chunk": chunks[idx],
                    "similarity": float(similarities[idx]),
                })

        # 6. Sort all results by similarity and get top-K
        all_results.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = all_results[:request.top_k]

        print(f"[RAG Service] Query: '{request.query}' -> {len(top_results)} results")

        return RAGQueryResponse(
            query=request.query,
            results=top_results,
            device=DEVICE,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {e}",
        )
