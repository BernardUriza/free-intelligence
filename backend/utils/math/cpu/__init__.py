"""CPU-based vector operations using NumPy.

Production-ready implementation for backend deployment.
NO GPU dependencies - optimized for CPU execution.
"""

from backend.utils.math.cpu.vector_utils import (
    cosine_similarity,
    cosine_similarity_batch,
)

__all__ = [
    "cosine_similarity",
    "cosine_similarity_batch",
]
