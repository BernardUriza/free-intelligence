from __future__ import annotations

from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)


async def _get_rag_context(
    query: str,
    persona: str,
    top_k: int = 5,
    min_similarity: float = 0.25,  # Lowered from 0.35 for better recall
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

        relevant_results = [r for r in results if r[2] >= min_similarity]
        if not relevant_results:
            return None

        # Accumulate user query in each document found
        unique_doc_ids = set(doc_id for doc_id, _, _, _ in relevant_results)
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
