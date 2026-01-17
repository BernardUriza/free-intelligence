from __future__ import annotations

from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)


async def _get_rag_context(
    query: str,
    persona: str,
    top_k: int = 5,
    min_similarity: float = 0.50,  # Medical safety requirement - only high-confidence matches
) -> str | None:
    """Search documents and build RAG context for the LLM.

    Also accumulates the user query in the found documents for analytics.
    """
    try:
        from datetime import UTC, datetime

        from backend.src.fi_document.api.public.documents import _get_embedding
        from backend.src.fi_storage.infrastructure.hdf5.document_repository import (
            DocumentQuestion,
            add_document_question,
            get_document,
            search_documents_by_embedding,
        )

        query_embedding = await _get_embedding(query)

        results = search_documents_by_embedding(
            query_embedding=query_embedding,
            top_k=top_k,
            persona_filter=persona,
        )

        # Observability: Track near-miss results (0.25-0.50 range)
        # These would have been included with old threshold but are now rejected
        near_miss_threshold = 0.25
        near_misses = [r for r in results if near_miss_threshold <= r[2] < min_similarity]
        if near_misses:
            logger.info(
                "RAG_NEAR_MISS_RESULTS",
                query=query[:50],
                persona=persona,
                near_miss_count=len(near_misses),
                similarities=[f"{r[2]:.2f}" for r in near_misses[:3]],  # Log top 3
                doc_ids=[r[0] for r in near_misses[:3]],
            )

        relevant_results = [r for r in results if r[2] >= min_similarity]
        if not relevant_results:
            logger.info(
                "RAG_NO_RESULTS",
                query=query[:50],
                persona=persona,
                min_similarity=min_similarity,
                total_results=len(results),
                near_misses=len(near_misses),
            )
            return None

        # Accumulate user query in each document found
        unique_doc_ids = {doc_id for doc_id, _, _, _ in relevant_results}
        for doc_id in unique_doc_ids:
            try:
                user_question = DocumentQuestion(
                    question_id=0,  # Auto-assigned by add_document_question
                    question=query,
                    source="user_query",
                    timestamp=datetime.now(UTC).isoformat(),
                    answer=None,
                )
                add_document_question(doc_id, user_question)
                logger.debug("USER_QUERY_ACCUMULATED", doc_id=doc_id, query=query[:50])
            except Exception as qe:
                logger.warning("FAILED_TO_ACCUMULATE_QUERY", doc_id=doc_id, error=str(qe))

        context_parts: list[str] = []
        for idx, (doc_id, _chunk_id, similarity, chunk_text) in enumerate(relevant_results, 1):
            doc = get_document(doc_id)
            if doc:
                context_parts.append(
                    f"### Fragmento {idx} (Relevancia: {similarity:.0%})\n"
                    f"**Fuente:** {doc.metadata.title}\n"
                    f"**Contenido:**\n{chunk_text}"
                )

        if not context_parts:
            return None

        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        logger.warning("RAG_CONTEXT_FAILED", error=str(e))
        return None
