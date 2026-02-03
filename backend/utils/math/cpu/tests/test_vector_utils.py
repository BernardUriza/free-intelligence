"""Tests for CPU vector utilities.

NO GPU required - pure NumPy tests.
Can run in CI/CD without GPU hardware.

Author: Bernard Uriza Orozco + Claude Sonnet 4.5
Created: 2026-02-02
Card: Vector Math CPU/GPU Separation
"""

import numpy as np
import pytest

from backend.utils.math.cpu import cosine_similarity, cosine_similarity_batch


class TestCosineSimilarity:
    """Test single vector similarity."""

    def test_identical_vectors(self):
        """Identical vectors should have similarity 1.0."""
        vec = [1.0, 0.0, 0.0]
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity 0.0."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [0.0, 1.0, 0.0]
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(0.0)

    def test_zero_vector(self):
        """Zero vector should return 0.0 (avoid division by zero)."""
        vec_zero = [0.0, 0.0, 0.0]
        vec_normal = [1.0, 1.0, 1.0]
        assert cosine_similarity(vec_zero, vec_normal) == 0.0
        assert cosine_similarity(vec_normal, vec_zero) == 0.0

    def test_opposite_vectors(self):
        """Opposite vectors should have negative similarity."""
        vec_a = [1.0, 0.0, 0.0]
        vec_b = [-1.0, 0.0, 0.0]
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(-1.0)

    def test_45_degree_vectors(self):
        """45-degree vectors should have similarity ~0.707."""
        vec_a = [1.0, 0.0]
        vec_b = [1.0, 1.0]
        # cos(45°) = √2/2 ≈ 0.707
        assert cosine_similarity(vec_a, vec_b) == pytest.approx(0.707, abs=0.01)


class TestCosineSimilarityBatch:
    """Test batch CPU vector similarity."""

    def test_batch_consistency_with_single(self):
        """Batch should match single computation results."""
        query = [1.0, 0.0, 0.0]
        vectors = [
            [1.0, 0.0, 0.0],  # Same
            [0.0, 1.0, 0.0],  # Orthogonal
            [0.5, 0.5, 0.0],  # 45 degrees
        ]

        batch_scores = cosine_similarity_batch(query, vectors)
        single_scores = [cosine_similarity(query, v) for v in vectors]

        np.testing.assert_array_almost_equal(batch_scores, single_scores)

    def test_empty_batch(self):
        """Empty vector list should return empty scores."""
        query = [1.0, 0.0, 0.0]
        assert cosine_similarity_batch(query, []) == []

    def test_single_vector_batch(self):
        """Batch with single vector should work."""
        query = [1.0, 0.0, 0.0]
        vectors = [[1.0, 0.0, 0.0]]
        scores = cosine_similarity_batch(query, vectors)
        assert len(scores) == 1
        assert scores[0] == pytest.approx(1.0)

    def test_large_batch_performance(self):
        """Batch should handle 1000+ vectors efficiently."""
        query = np.random.rand(384).tolist()  # OpenAI embedding dim
        vectors = np.random.rand(1000, 384).tolist()

        import time

        start = time.perf_counter()
        scores = cosine_similarity_batch(query, vectors)
        elapsed = time.perf_counter() - start

        assert len(scores) == 1000
        assert elapsed < 0.05  # Should be <50ms on modern CPU

    def test_batch_all_zero_vectors(self):
        """Batch with all zero vectors should return all zeros."""
        query = [1.0, 1.0, 1.0]
        vectors = [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        ]
        scores = cosine_similarity_batch(query, vectors)
        assert scores == [0.0, 0.0, 0.0]

    def test_batch_query_zero_vector(self):
        """Batch with zero query should return all zeros."""
        query = [0.0, 0.0, 0.0]
        vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
        scores = cosine_similarity_batch(query, vectors)
        assert scores == [0.0, 0.0, 0.0]
