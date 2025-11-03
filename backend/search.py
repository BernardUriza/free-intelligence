from __future__ import annotations

"""
Free Intelligence - Semantic Search

Semantic search over interactions using cosine similarity on embeddings.

FI-SEARCH-FEAT-001
"""

from pathlib import Path

import h5py
import numpy as np

from backend.llm_router import llm_embed, pad_embedding_to_768
from backend.logger import get_logger

logger = get_logger(__name__)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Similarity score between 0 and 1

    Examples:
        >>> v1 = np.array([1, 0, 0])
        >>> v2 = np.array([1, 0, 0])
        >>> cosine_similarity(v1, v2)
        1.0
    """
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot_product / (norm1 * norm2))


def semantic_search(
    corpus_path: str, query: str, top_k: int = 5, min_score: float = 0.0
) -> list[dict]:
    """
    Perform semantic search over corpus interactions.

    Args:
        corpus_path: Path to HDF5 corpus
        query: Search query text
        top_k: Number of top results to return
        min_score: Minimum similarity score threshold (0-1)

    Returns:
        List of dicts with interaction data and similarity scores

    Examples:
        >>> results = semantic_search(
        ...     "storage/corpus.h5",
        ...     "What is Free Intelligence?",
        ...     top_k=5
        ... )
        >>> for result in results:
        ...     print(f"{result['score']:.3f}: {result['prompt'][:60]}")
    """
    logger.info("SEMANTIC_SEARCH_STARTED", query=query[:100], top_k=top_k)

    try:
        # Generate query embedding
        query_embedding = llm_embed(query)

        # Pad to 768 dimensions if needed (shared utility)
        query_embedding = pad_embedding_to_768(query_embedding)

        embedding_dim = query_embedding.shape[0]
        logger.info("QUERY_EMBEDDING_GENERATED", embedding_dim=embedding_dim)

        # Read corpus embeddings and interactions
        with h5py.File(corpus_path, "r") as f:
            embeddings_group = f["embeddings"]
            interactions_group = f["interactions"]

            total_embeddings = embeddings_group["interaction_id"].shape[0]  # type: ignore[index,attr-defined]

            if total_embeddings == 0:
                logger.warning("CORPUS_EMPTY", message="No embeddings in corpus")
                return []

            logger.info("CORPUS_LOADED", total_embeddings=total_embeddings)

            # Build interaction dictionary once (O(n) instead of O(n²))
            # This eliminates the N+1 query problem
            interaction_map = {}
            total_interactions = interactions_group["interaction_id"].shape[0]  # type: ignore[index,attr-defined]
            for j in range(total_interactions):
                iid = interactions_group["interaction_id"][j].decode("utf-8")  # type: ignore[index,attr-defined]
                interaction_map[iid] = {
                    "session_id": interactions_group["session_id"][j].decode("utf-8"),  # type: ignore[index,attr-defined]
                    "timestamp": interactions_group["timestamp"][j].decode("utf-8"),  # type: ignore[index,attr-defined]
                    "prompt": interactions_group["prompt"][j].decode("utf-8"),  # type: ignore[index,attr-defined]
                    "response": interactions_group["response"][j].decode("utf-8"),  # type: ignore[index,attr-defined]
                    "model": interactions_group["model"][j].decode("utf-8"),  # type: ignore[index,attr-defined]
                    "tokens": int(interactions_group["tokens"][j]),  # type: ignore[index]
                }

            logger.info("INTERACTION_MAP_BUILT", total_interactions=total_interactions)

            # Compute similarities
            results = []
            for i in range(total_embeddings):
                # Get embedding vector
                embedding_vec = embeddings_group["vector"]  # type: ignore[index][i]

                # Compute similarity
                similarity = cosine_similarity(query_embedding, embedding_vec)

                # Skip if below threshold
                if similarity < min_score:
                    continue

                # Get interaction data via O(1) dictionary lookup
                interaction_id = embeddings_group["interaction_id"][i].decode("utf-8")  # type: ignore[index,attr-defined]

                if interaction_id in interaction_map:
                    interaction_data = interaction_map[interaction_id]
                    results.append(
                        {
                            "score": similarity,
                            "interaction_id": interaction_id,
                            **interaction_data,  # Unpack all fields
                        }
                    )
                else:
                    logger.warning(
                        "INTERACTION_NOT_FOUND",
                        interaction_id=interaction_id,
                        message="Embedding without matching interaction",
                    )

            # Sort by similarity (descending) and take top_k
            results.sort(key=lambda x: x["score"], reverse=True)
            results = results[:top_k]

            logger.info(
                "SEMANTIC_SEARCH_COMPLETED",
                total_results=len(results),
                top_score=results[0]["score"] if results else 0.0,
            )

            return results

    except Exception as e:
        logger.error("SEMANTIC_SEARCH_FAILED", error=str(e)
        raise


def search_by_session(corpus_path: str, session_id: str) -> list[dict]:
    """
    Get all interactions from a specific session.

    Args:
        corpus_path: Path to HDF5 corpus
        session_id: Session ID to filter by

    Returns:
        List of interaction dicts

    Examples:
        >>> results = search_by_session(
        ...     "storage/corpus.h5",
        ...     "session_20251028_010000"
        ... )
    """
    logger.info("SESSION_SEARCH_STARTED", session_id=session_id)

    try:
        with h5py.File(corpus_path, "r") as f:
            interactions_group = f["interactions"]
            total = interactions_group["session_id"].shape[0]  # type: ignore[index,attr-defined]

            results = []
            for i in range(total):
                curr_session_id = interactions_group["session_id"][i].decode("utf-8")  # type: ignore[index,attr-defined]
                if curr_session_id == session_id:
                    results.append(
                        {
                            "interaction_id": interactions_group["interaction_id"][i].decode(  # type: ignore[attr-defined]
                                "utf-8"
                            ),  # type: ignore[index,attr-defined]
                            "session_id": session_id,
                            "timestamp": interactions_group["timestamp"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                            "prompt": interactions_group["prompt"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                            "response": interactions_group["response"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                            "model": interactions_group["model"][i].decode("utf-8"),  # type: ignore[index,attr-defined]
                            "tokens": int(interactions_group["tokens"][i]),  # type: ignore[index]
                        }
                    )

            logger.info(
                "SESSION_SEARCH_COMPLETED", session_id=session_id, interactions_found=len(results)
            )

            return results

    except Exception as e:
        logger.error("SESSION_SEARCH_FAILED", error=str(e)
        raise


if __name__ == "__main__":
    """Demo script"""
    import sys

    from backend.config_loader import load_config

    config = load_config()
    corpus_path = config["storage"]["corpus_path"]

    print("🔍 Free Intelligence - Semantic Search Demo")
    print("=" * 60)

    # Check if corpus exists and has data
    if not Path(corpus_path).exists():
        print(f"\n❌ Corpus not found: {corpus_path}")
        sys.exit(1)

    with h5py.File(corpus_path, "r") as f:
        embeddings_count = f["embeddings"]["interaction_id"].shape[0]  # type: ignore[index,attr-defined]

    if embeddings_count == 0:
        print("\n⚠️  Corpus is empty. Add some interactions first using 'fi chat'")
        sys.exit(1)

    print(f"\n📊 Corpus has {embeddings_count} embeddings")

    # Demo queries
    queries = ["What is Free Intelligence?", "How does the system work?", "database and storage"]

    for query in queries:
        print(f'\n🔍 Query: "{query}"')
        print("─" * 60)

        results = semantic_search(corpus_path, query, top_k=3)

        if not results:
            print("   No results found")
            continue

        for i, result in enumerate(results, 1):
            score = result["score"]
            prompt = result["prompt"]
            response = result["response"]
            model = result["model"]
            tokens = result["tokens"]
            print(f"\n   [{i}] Score: {score:.3f}")
            print(f"       Prompt: {prompt[:70]}...")
            print(f"       Response: {response[:70]}...")
            print(f"       Model: {model}, Tokens: {tokens}")

    print("\n" + "=" * 60)
    print("Demo complete!")
