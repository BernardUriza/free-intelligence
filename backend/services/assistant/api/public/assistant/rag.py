from __future__ import annotations

from backend.services.document.services.document_service import DocumentService
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


async def _get_rag_context(
    query: str,
    persona: str,
    clinic_id: str,
    top_k: int = 5,
    min_similarity: float = 0.50,  # Medical safety requirement - only high-confidence matches
) -> str | None:
    """Search documents and build RAG context for the LLM.

    Uses FI Monitor GPU service for embeddings (Ollama via tunnel).
    SECURITY: Only searches documents within clinic_id boundary (multi-tenancy).

    Args:
        query: User query for RAG search
        persona: Persona filter (future: filter by document_type)
        clinic_id: Clinic ID for multi-tenancy isolation
        top_k: Number of top results
        min_similarity: Minimum similarity threshold (0-1, cosine similarity)

    Returns:
        Formatted RAG context or None if no results

    Example:
        context = await _get_rag_context(
            query="diabetes treatment guidelines",
            persona="doctor",
            clinic_id="clinic-123",
            top_k=5,
            min_similarity=0.50
        )
    """
    if not clinic_id:
        logger.warning("RAG_MISSING_CLINIC_ID", query=query[:50])
        return None

    try:
        # Initialize DocumentService (uses HDF5 + in-memory vector index)
        doc_service = DocumentService()

        # Search documents using FI Monitor GPU embeddings
        # DocumentService.search() internally:
        # 1. Calls generate_embedding(query) → monitor_client → fi-monitor/rag/embed
        # 2. Searches in-memory vector index with clinic_id filter
        # 3. Returns list[SearchResult] sorted by similarity (highest first)
        results = doc_service.search(
            query=query,
            clinic_id=clinic_id,
            limit=top_k,
            min_score=min_similarity
        )

        logger.info(
            "RAG_SEARCH_EXECUTED",
            clinic_id=clinic_id,
            query_length=len(query),
            results_count=len(results),
            min_similarity=min_similarity
        )

        if not results:
            logger.info(
                "RAG_NO_RESULTS",
                query=query[:50],
                clinic_id=clinic_id,
                min_similarity=min_similarity
            )
            return None

        # Format results into LLM-friendly context
        context_parts: list[str] = []
        for idx, result in enumerate(results, 1):
            context_parts.append(
                f"### Fragmento {idx} (Relevancia: {result.similarity_score:.0%})\n"
                f"**Fuente:** {result.document_title}\n"
                f"**Contenido:**\n{result.chunk_text}"
            )

        logger.info(
            "RAG_CONTEXT_BUILT",
            clinic_id=clinic_id,
            fragments=len(context_parts),
            avg_similarity=sum(r.similarity_score for r in results) / len(results)
        )

        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        logger.error(
            "RAG_CONTEXT_FAILED",
            clinic_id=clinic_id,
            query=query[:50],
            error=str(e),
            error_type=type(e).__name__
        )
        return None
