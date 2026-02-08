"""CPU-based vector math utilities.

Production-ready NumPy implementation for backend deployment.
NO GPU dependencies - optimized for Azure Container Apps CPU execution.

Performance Profile:
    100 vectors:   ~1ms
    1000 vectors:  ~10ms
    10000 vectors: ~100ms (consider offloading to Fi Monitor GPU)

Deployment Target:
    Backend (Azure Container Apps) - NO GPU available
    Use Fi Monitor for GPU-accelerated workloads (10000+ vectors)

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-02-02
Refactored from: backend/utils/math/vector_utils.py
Card: Vector Math CPU/GPU Separation
"""

import numpy as np


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Pure mathematical function: cos(θ) = (A · B) / (||A|| × ||B||)

    Args:
        vec1: First vector (embedding)
        vec2: Second vector (embedding)

    Returns:
        Cosine similarity score (0-1, higher is more similar)

    Example:
        >>> vec_a = [1.0, 0.0, 0.0]
        >>> vec_b = [1.0, 0.0, 0.0]
        >>> cosine_similarity(vec_a, vec_b)
        1.0  # Identical vectors

        >>> vec_c = [1.0, 0.0, 0.0]
        >>> vec_d = [0.0, 1.0, 0.0]
        >>> cosine_similarity(vec_c, vec_d)
        0.0  # Orthogonal vectors
    """
    a = np.array(vec1)
    b = np.array(vec2)

    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


def cosine_similarity_batch(
    query_vec: list[float],
    vectors: list[list[float]],
) -> list[float]:
    """Compute cosine similarity between query and multiple vectors (CPU batch).

    Optimized batch version using NumPy broadcasting.
    Faster than calling cosine_similarity() in a loop.

    Args:
        query_vec: Query vector (embedding)
        vectors: List of vectors to compare against

    Returns:
        List of similarity scores (0-1) for each vector

    Performance:
        100 vectors: ~1ms (CPU)
        1000 vectors: ~10ms (CPU)

    Example:
        >>> query = [1.0, 0.0, 0.0]
        >>> docs = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.5, 0.5, 0.0]]
        >>> cosine_similarity_batch(query, docs)
        [1.0, 0.0, 0.707...]
    """
    query = np.array(query_vec)
    matrix = np.array(vectors)  # Shape: (n_vectors, embedding_dim)

    # Normalize query
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return [0.0] * len(vectors)

    # Normalize all vectors at once (broadcasting)
    matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix_norms[matrix_norms == 0] = 1.0  # Avoid division by zero

    # Compute all dot products at once (matrix-vector multiplication)
    dot_products = np.dot(matrix, query)

    # Compute similarities
    similarities = dot_products / (matrix_norms.squeeze() * query_norm)

    return similarities.tolist()
