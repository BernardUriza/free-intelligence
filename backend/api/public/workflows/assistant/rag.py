from __future__ import annotations

from backend.logger import get_logger

logger = get_logger(__name__)


async def _get_rag_context(
    query: str,
    persona: str,
    top_k: int = 5,
    min_similarity: float = 0.35,
) -> str | None:
    """Search documents and build RAG context for the LLM."""
    try:
        from backend.api.public.workflows.documents import _get_embedding
        from backend.packages.fi_storage.infrastructure.hdf5.document_repository import (
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
