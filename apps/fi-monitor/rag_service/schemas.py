"""Pydantic request/response models for RAG Service."""

from __future__ import annotations

from pydantic import BaseModel, Field

from config import EMBEDDING_DIM


# ============================================================================
# Core Endpoints
# ============================================================================


class EmbedRequest(BaseModel):
    """Request for batch embedding generation."""

    texts: list[str] = Field(..., min_length=1, max_length=100, description="Texts to embed (max 100)")


class EmbedResponse(BaseModel):
    """Response with embeddings and metadata."""

    embeddings: list[list[float]] = Field(..., description="List of embeddings (384-dim each)")
    device: str = Field(..., description="Device used (cuda/mps/cpu)")
    model: str = Field(..., description="Model name")
    count: int = Field(..., description="Number of embeddings generated")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    device: str = Field(..., description="Device being used")
    gpu_name: str | None = Field(None, description="GPU name if available")
    gpu_memory_mb: float | None = Field(None, description="GPU memory allocated (MB) - CUDA only, MPS returns -1")
    model: str = Field(..., description="Model loaded")


class PDFUploadRequest(BaseModel):
    """Request for PDF upload and processing."""

    filename: str = Field(..., description="PDF filename")
    content: str = Field(..., description="PDF content as base64 string")


class PDFUploadResponse(BaseModel):
    """Response for PDF upload."""

    status: str = Field(..., description="Upload status (success/error)")
    filename: str = Field(..., description="Uploaded filename")
    chunks: int = Field(0, description="Number of chunks extracted")
    message: str = Field(..., description="Status message")


class RAGQueryRequest(BaseModel):
    """Request for RAG query."""

    query: str = Field(..., description="Question to ask")
    filename: str | None = Field(None, description="Specific PDF to query (optional, searches all if not provided)")
    top_k: int = Field(3, description="Number of top results to return")


class RAGQueryResponse(BaseModel):
    """Response for RAG query."""

    query: str = Field(..., description="Original query")
    results: list[dict] = Field(..., description="List of results with chunk text and similarity score")
    device: str = Field(..., description="Device used for search")


# ============================================================================
# RAG Quality Metrics
# ============================================================================


class GenerateAnnotationsRequest(BaseModel):
    """Request to auto-generate ground truth annotations with LLM."""

    filename: str = Field(..., description="PDF filename to generate annotations for")
    questions_per_chunk: int = Field(2, ge=1, le=5, description="Number of questions to generate per chunk")
    model: str = Field("llama3.1:8b", description="Ollama model to use for generation")


class GenerateAnnotationsResponse(BaseModel):
    """Response from annotation generation."""

    filename: str
    annotations_count: int
    chunks_processed: int
    status: str
    estimated_time_ms: int


class AnnotationEntry(BaseModel):
    """Single annotation entry."""

    query: str
    relevant_chunks: list[int]
    relevance_scores: list[int]
    source: str
    validated: bool


class AnnotationsResponse(BaseModel):
    """Response for GET /rag/annotations/{filename}."""

    filename: str
    annotations: list[AnnotationEntry]
    count: int


class UpdateAnnotationRequest(BaseModel):
    """Request to update/validate annotation manually."""

    query: str
    relevant_chunks: list[int]
    relevance_scores: list[int]
    validated: bool = True


class EvaluateRequest(BaseModel):
    """Request to evaluate single query quality."""

    query: str
    filename: str
    top_k: int = Field(3, ge=1, le=10, description="Number of top results to evaluate")


class EvaluateResponse(BaseModel):
    """Response from single query evaluation."""

    query: str
    metrics: dict[str, float]
    retrieved_chunks: list[int]
    relevant_chunks: list[int]
    relevance_scores: list[int]


class BatchEvaluateRequest(BaseModel):
    """Request to evaluate all queries in a document."""

    filename: str
    top_k: int = Field(3, ge=1, le=10)


class BatchEvaluateResponse(BaseModel):
    """Response from batch evaluation."""

    filename: str
    total_queries: int
    avg_metrics: dict[str, float]
    per_query_metrics: list[dict]


class SimilaritySearchRequest(BaseModel):
    """Request for GPU similarity search."""

    query_vector: list[float] = Field(
        ...,
        description="Query embedding vector",
        min_length=EMBEDDING_DIM,
        max_length=EMBEDDING_DIM,
    )
    document_vectors: list[list[float]] = Field(
        ...,
        description="List of document embedding vectors to search",
        min_length=1,
        max_length=50000,  # Limit to prevent OOM
    )


class SimilaritySearchResponse(BaseModel):
    """Response from GPU similarity search."""

    similarities: list[float] = Field(
        ...,
        description="Cosine similarity scores (0-1) for each document vector",
    )
    device_used: str = Field(
        ...,
        description="Device used for computation (cuda/mps/cpu)",
    )
    duration_ms: float = Field(
        ...,
        description="Computation time in milliseconds",
    )
