"""Math utilities for vector operations.

CPU-only implementation for production backend.
GPU acceleration handled by Fi Monitor service independently.
"""

from backend.utils.math.cpu import (
    cosine_similarity,
    cosine_similarity_batch,
)

__all__ = [
    "cosine_similarity",
    "cosine_similarity_batch",
]
