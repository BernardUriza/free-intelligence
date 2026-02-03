"""Vector math utilities.

Pure mathematical functions for vector operations.
No business logic, no dependencies on services/repositories.

Author: Claude Code (extracted from embedding_service.py)
Created: 2026-02-02
Phase: Architecture violation fix (Sello 7 - SOBERBIA)
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
