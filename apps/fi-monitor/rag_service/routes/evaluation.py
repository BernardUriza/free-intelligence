"""Annotation and evaluation endpoints."""

from __future__ import annotations

import time

import numpy as np
from fastapi import APIRouter, Depends, HTTPException

import state
from annotations import generate_annotations_for_document
from auth import verify_api_key
from gpu import DEVICE
from metrics import compute_all_metrics
from schemas import (
    AnnotationEntry,
    AnnotationsResponse,
    BatchEvaluateRequest,
    BatchEvaluateResponse,
    EvaluateRequest,
    EvaluateResponse,
    GenerateAnnotationsRequest,
    GenerateAnnotationsResponse,
    UpdateAnnotationRequest,
)

router = APIRouter()


@router.post("/rag/generate_annotations", response_model=GenerateAnnotationsResponse)
async def generate_annotations(
    request: GenerateAnnotationsRequest,
    _auth: None = Depends(verify_api_key),
) -> GenerateAnnotationsResponse:
    """Auto-generate ground truth annotations using Ollama LLM.

    SECURITY: Requires API key authentication.

    Args:
        request: Annotation generation parameters

    Returns:
        Count of generated annotations

    Example:
        curl -X POST http://localhost:11435/rag/generate_annotations \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"filename":"diabetes.pdf","questions_per_chunk":2}'
    """
    if request.filename not in state._document_store:
        raise HTTPException(status_code=404, detail=f"Document '{request.filename}' not found")

    try:
        start_time = time.time()

        chunks = state._document_store[request.filename]["chunks"]

        # Generate annotations with LLM
        annotations = await generate_annotations_for_document(
            filename=request.filename,
            chunks=chunks,
            questions_per_chunk=request.questions_per_chunk,
            model=request.model,
        )

        # Store in ground truth store
        state._ground_truth_store[request.filename] = annotations

        elapsed_ms = int((time.time() - start_time) * 1000)

        print(
            f"[RAG Service] Generated {len(annotations)} annotations for {request.filename} "
            f"in {elapsed_ms}ms"
        )

        return GenerateAnnotationsResponse(
            filename=request.filename,
            annotations_count=len(annotations),
            chunks_processed=len(chunks),
            status="success",
            estimated_time_ms=elapsed_ms,
        )

    except Exception as e:
        print(f"[RAG Service] Annotation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Annotation generation failed: {e}")


@router.get("/rag/annotations/{filename}", response_model=AnnotationsResponse)
async def get_annotations(
    filename: str,
    _auth: None = Depends(verify_api_key),
) -> AnnotationsResponse:
    """Get existing ground truth annotations for a document.

    SECURITY: Requires API key authentication.

    Example:
        curl -X GET http://localhost:11435/rag/annotations/diabetes.pdf \\
             -H "X-API-Key: your-key"
    """
    if filename not in state._ground_truth_store:
        raise HTTPException(
            status_code=404, detail=f"No annotations found for '{filename}'"
        )

    annotations = state._ground_truth_store[filename]

    return AnnotationsResponse(
        filename=filename,
        annotations=[AnnotationEntry(**ann) for ann in annotations],
        count=len(annotations),
    )


@router.put("/rag/annotations/{filename}")
async def update_annotation(
    filename: str,
    request: UpdateAnnotationRequest,
    _auth: None = Depends(verify_api_key),
) -> dict:
    """Update/validate annotation manually.

    Use this to correct LLM-generated annotations.

    Example:
        curl -X PUT http://localhost:11435/rag/annotations/diabetes.pdf \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"query":"What is blood sugar?","relevant_chunks":[5],"relevance_scores":[3],"validated":true}'
    """
    if filename not in state._ground_truth_store:
        raise HTTPException(
            status_code=404, detail=f"No annotations found for '{filename}'"
        )

    # Find and update annotation with matching query
    annotations = state._ground_truth_store[filename]
    found = False

    for ann in annotations:
        if ann["query"] == request.query:
            ann["relevant_chunks"] = request.relevant_chunks
            ann["relevance_scores"] = request.relevance_scores
            ann["validated"] = request.validated
            ann["source"] = "manual"  # Mark as manually edited
            found = True
            break

    if not found:
        # Add new annotation
        annotations.append(
            {
                "query": request.query,
                "relevant_chunks": request.relevant_chunks,
                "relevance_scores": request.relevance_scores,
                "source": "manual",
                "validated": request.validated,
            }
        )

    print(f"[RAG Service] Updated annotation for '{filename}': {request.query}")

    return {"status": "updated", "query": request.query, "validated": request.validated}


@router.post("/rag/evaluate", response_model=EvaluateResponse)
async def evaluate_query(
    request: EvaluateRequest,
    _auth: None = Depends(verify_api_key),
) -> EvaluateResponse:
    """Evaluate quality of a single query using RAG metrics.

    SECURITY: Requires API key authentication.

    Returns: Recall@k, Precision@k, MRR, NDCG@k

    Example:
        curl -X POST http://localhost:11435/rag/evaluate \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"query":"What is blood sugar?","filename":"diabetes.pdf","top_k":3}'
    """
    if request.filename not in state._document_store:
        raise HTTPException(status_code=404, detail=f"Document '{request.filename}' not found")

    if request.filename not in state._ground_truth_store:
        raise HTTPException(
            status_code=404,
            detail=f"No ground truth annotations for '{request.filename}'. Generate annotations first.",
        )

    # 1. Execute RAG query internally
    if state._model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    try:
        # Get query embedding
        query_embedding = state._model.encode(
            [request.query], convert_to_numpy=True, show_progress_bar=False, device=DEVICE
        )[0]

        # Search in document
        doc_data = state._document_store[request.filename]
        chunks = doc_data["chunks"]
        embeddings = doc_data["embeddings"]

        # Compute similarities
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        embeddings_norm = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        similarities = embeddings_norm @ query_norm

        # Get top-k chunk indices
        top_indices = np.argsort(similarities)[::-1][: request.top_k]
        retrieved_chunks = top_indices.tolist()

        # 2. Find ground truth for this query
        ground_truth_annotations = state._ground_truth_store[request.filename]
        ground_truth = None

        for ann in ground_truth_annotations:
            if ann["query"].strip().lower() == request.query.strip().lower():
                ground_truth = ann
                break

        if not ground_truth:
            raise HTTPException(
                status_code=404,
                detail=f"No ground truth found for query: '{request.query}'",
            )

        relevant_chunks = ground_truth["relevant_chunks"]
        relevance_scores_list = ground_truth["relevance_scores"]

        # Build relevance scores dict
        relevance_scores = {
            chunk_id: score
            for chunk_id, score in zip(relevant_chunks, relevance_scores_list)
        }

        # 3. Compute all metrics
        metrics = compute_all_metrics(
            retrieved=retrieved_chunks,
            relevant=relevant_chunks,
            relevance_scores=relevance_scores,
            k=request.top_k,
        )

        print(
            f"[RAG Service] Evaluated query '{request.query}': "
            f"Recall@{request.top_k}={metrics[f'recall@{request.top_k}']:.2f}"
        )

        return EvaluateResponse(
            query=request.query,
            metrics=metrics,
            retrieved_chunks=retrieved_chunks,
            relevant_chunks=relevant_chunks,
            relevance_scores=relevance_scores_list,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e}")


@router.post("/rag/batch_evaluate", response_model=BatchEvaluateResponse)
async def batch_evaluate(
    request: BatchEvaluateRequest,
    _auth: None = Depends(verify_api_key),
) -> BatchEvaluateResponse:
    """Evaluate all queries for a document (average metrics).

    SECURITY: Requires API key authentication.

    Example:
        curl -X POST http://localhost:11435/rag/batch_evaluate \\
             -H "X-API-Key: your-key" \\
             -H "Content-Type: application/json" \\
             -d '{"filename":"diabetes.pdf","top_k":3}'
    """
    if request.filename not in state._ground_truth_store:
        raise HTTPException(
            status_code=404,
            detail=f"No annotations for '{request.filename}'. Generate annotations first.",
        )

    annotations = state._ground_truth_store[request.filename]

    if not annotations:
        raise HTTPException(status_code=404, detail=f"No queries found for '{request.filename}'")

    # Evaluate each query
    per_query_metrics = []
    metric_sums: dict[str, float] = {}

    for ann in annotations:
        query = ann["query"]

        # Call evaluate_query for each annotation
        try:
            eval_request = EvaluateRequest(
                query=query, filename=request.filename, top_k=request.top_k
            )

            # Reuse evaluation logic
            result = await evaluate_query(eval_request)

            per_query_metrics.append(
                {
                    "query": query,
                    "metrics": result.metrics,
                    "retrieved_chunks": result.retrieved_chunks,
                    "relevant_chunks": result.relevant_chunks,
                }
            )

            # Accumulate sums for averaging
            for metric_name, value in result.metrics.items():
                metric_sums[metric_name] = metric_sums.get(metric_name, 0.0) + value

        except HTTPException as e:
            # Skip queries without ground truth
            if e.status_code == 404:
                continue
            raise

    # Compute averages
    total_queries = len(per_query_metrics)
    avg_metrics = {
        metric_name: total / total_queries for metric_name, total in metric_sums.items()
    }

    print(
        f"[RAG Service] Batch evaluated {request.filename}: "
        f"{total_queries} queries, avg Recall@{request.top_k}={avg_metrics.get(f'recall@{request.top_k}', 0.0):.2f}"
    )

    return BatchEvaluateResponse(
        filename=request.filename,
        total_queries=total_queries,
        avg_metrics=avg_metrics,
        per_query_metrics=per_query_metrics,
    )
