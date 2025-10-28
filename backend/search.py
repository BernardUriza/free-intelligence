"""
Free Intelligence - Semantic Search

Semantic search over interactions using cosine similarity on embeddings.

FI-SEARCH-FEAT-001
"""

import h5py
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from backend.logger import get_logger
from backend.llm_router import llm_embed

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
    corpus_path: str,
    query: str,
    top_k: int = 5,
    min_score: float = 0.0
) -> List[Dict]:
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

        # Pad to 768 dimensions if needed (sentence-transformers gives 384)
        if query_embedding.shape[0] == 384:
            padded_query = np.zeros(768, dtype=np.float32)
            padded_query[:384] = query_embedding
            query_embedding = padded_query

        logger.info("QUERY_EMBEDDING_GENERATED", embedding_dim=query_embedding.shape[0])

        # Read corpus embeddings and interactions
        with h5py.File(corpus_path, 'r') as f:
            embeddings_group = f["embeddings"]
            interactions_group = f["interactions"]

            total_embeddings = embeddings_group["interaction_id"].shape[0]

            if total_embeddings == 0:
                logger.warning("CORPUS_EMPTY", message="No embeddings in corpus")
                return []

            logger.info("CORPUS_LOADED", total_embeddings=total_embeddings)

            # Compute similarities
            results = []
            for i in range(total_embeddings):
                # Get embedding vector
                embedding_vec = embeddings_group["vector"][i]

                # Compute similarity
                similarity = cosine_similarity(query_embedding, embedding_vec)

                # Skip if below threshold
                if similarity < min_score:
                    continue

                # Get interaction data
                interaction_id = embeddings_group["interaction_id"][i].decode('utf-8')

                # Find matching interaction
                # Linear search through interactions (could be optimized with index)
                for j in range(interactions_group["interaction_id"].shape[0]):
                    if interactions_group["interaction_id"][j].decode('utf-8') == interaction_id:
                        results.append({
                            'score': similarity,
                            'interaction_id': interaction_id,
                            'session_id': interactions_group["session_id"][j].decode('utf-8'),
                            'timestamp': interactions_group["timestamp"][j].decode('utf-8'),
                            'prompt': interactions_group["prompt"][j].decode('utf-8'),
                            'response': interactions_group["response"][j].decode('utf-8'),
                            'model': interactions_group["model"][j].decode('utf-8'),
                            'tokens': int(interactions_group["tokens"][j])
                        })
                        break

            # Sort by similarity (descending) and take top_k
            results.sort(key=lambda x: x['score'], reverse=True)
            results = results[:top_k]

            logger.info("SEMANTIC_SEARCH_COMPLETED",
                       total_results=len(results),
                       top_score=results[0]['score'] if results else 0.0)

            return results

    except Exception as e:
        logger.error("SEMANTIC_SEARCH_FAILED", error=str(e), query=query[:100])
        raise


def search_by_session(
    corpus_path: str,
    session_id: str
) -> List[Dict]:
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
        with h5py.File(corpus_path, 'r') as f:
            interactions_group = f["interactions"]
            total = interactions_group["session_id"].shape[0]

            results = []
            for i in range(total):
                if interactions_group["session_id"][i].decode('utf-8') == session_id:
                    results.append({
                        'interaction_id': interactions_group["interaction_id"][i].decode('utf-8'),
                        'session_id': session_id,
                        'timestamp': interactions_group["timestamp"][i].decode('utf-8'),
                        'prompt': interactions_group["prompt"][i].decode('utf-8'),
                        'response': interactions_group["response"][i].decode('utf-8'),
                        'model': interactions_group["model"][i].decode('utf-8'),
                        'tokens': int(interactions_group["tokens"][i])
                    })

            logger.info("SESSION_SEARCH_COMPLETED",
                       session_id=session_id,
                       interactions_found=len(results))

            return results

    except Exception as e:
        logger.error("SESSION_SEARCH_FAILED", error=str(e), session_id=session_id)
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

    with h5py.File(corpus_path, 'r') as f:
        embeddings_count = f["embeddings"]["interaction_id"].shape[0]

    if embeddings_count == 0:
        print("\n⚠️  Corpus is empty. Add some interactions first using 'fi chat'")
        sys.exit(1)

    print(f"\n📊 Corpus has {embeddings_count} embeddings")

    # Demo queries
    queries = [
        "What is Free Intelligence?",
        "How does the system work?",
        "database and storage"
    ]

    for query in queries:
        print(f"\n🔍 Query: \"{query}\"")
        print("─" * 60)

        results = semantic_search(corpus_path, query, top_k=3)

        if not results:
            print("   No results found")
            continue

        for i, result in enumerate(results, 1):
            print(f"\n   [{i}] Score: {result['score']:.3f}")
            print(f"       Prompt: {result['prompt'][:70]}...")
            print(f"       Response: {result['response'][:70]}...")
            print(f"       Model: {result['model']}, Tokens: {result['tokens']}")

    print("\n" + "=" * 60)
    print("Demo complete!")
