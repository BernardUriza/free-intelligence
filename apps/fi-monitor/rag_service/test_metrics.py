"""
Unit tests for RAG quality metrics.

Tests all 4 metrics (Recall, Precision, MRR, NDCG) with:
- Normal cases
- Edge cases (empty results, no relevant chunks)
- Perfect ranking scenarios
- Worst-case scenarios
"""

import pytest
from metrics import (
    compute_recall_at_k,
    compute_precision_at_k,
    compute_mrr,
    compute_ndcg_at_k,
    compute_all_metrics,
)


class TestRecallAtK:
    """Test Recall@k metric."""

    def test_perfect_recall(self):
        """All relevant chunks in top-k."""
        retrieved = [2, 5, 8]
        relevant = [2, 5]
        assert compute_recall_at_k(retrieved, relevant, k=3) == 1.0

    def test_partial_recall(self):
        """Some relevant chunks missed."""
        retrieved = [2, 5, 8]
        relevant = [0, 2, 5]
        # Found 2 out of 3 relevant chunks
        assert compute_recall_at_k(retrieved, relevant, k=3) == pytest.approx(2 / 3)

    def test_zero_recall(self):
        """No relevant chunks in top-k."""
        retrieved = [1, 2, 3]
        relevant = [4, 5, 6]
        assert compute_recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_empty_relevant(self):
        """No ground truth relevant chunks."""
        retrieved = [1, 2, 3]
        relevant = []
        assert compute_recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_empty_retrieved(self):
        """No results retrieved."""
        retrieved = []
        relevant = [1, 2, 3]
        assert compute_recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_k_larger_than_retrieved(self):
        """k larger than number of retrieved chunks."""
        retrieved = [1, 2]
        relevant = [1, 2, 3]
        # Found 2 out of 3 relevant chunks
        assert compute_recall_at_k(retrieved, relevant, k=5) == pytest.approx(2 / 3)


class TestPrecisionAtK:
    """Test Precision@k metric."""

    def test_perfect_precision(self):
        """All top-k are relevant."""
        retrieved = [2, 5]
        relevant = [2, 5, 8]
        assert compute_precision_at_k(retrieved, relevant, k=2) == 1.0

    def test_partial_precision(self):
        """Some top-k are noise."""
        retrieved = [2, 5, 8]
        relevant = [2, 5]
        # 2 out of 3 are relevant
        assert compute_precision_at_k(retrieved, relevant, k=3) == pytest.approx(2 / 3)

    def test_zero_precision(self):
        """All top-k are noise."""
        retrieved = [1, 2, 3]
        relevant = [4, 5, 6]
        assert compute_precision_at_k(retrieved, relevant, k=3) == 0.0

    def test_k_zero(self):
        """k=0 (no results considered)."""
        retrieved = [1, 2, 3]
        relevant = [1, 2, 3]
        assert compute_precision_at_k(retrieved, relevant, k=0) == 0.0

    def test_empty_retrieved(self):
        """No results retrieved."""
        retrieved = []
        relevant = [1, 2, 3]
        assert compute_precision_at_k(retrieved, relevant, k=3) == 0.0

    def test_k_larger_than_retrieved(self):
        """k larger than number of retrieved chunks."""
        retrieved = [1, 2]
        relevant = [1, 2, 3]
        # 2 relevant in 5 positions = 2/5 = 0.4
        assert compute_precision_at_k(retrieved, relevant, k=5) == pytest.approx(2 / 5)


class TestMRR:
    """Test Mean Reciprocal Rank (MRR)."""

    def test_first_result_relevant(self):
        """First result is relevant (best case)."""
        retrieved = [2, 5, 8]
        relevant = [2]
        assert compute_mrr(retrieved, relevant) == 1.0

    def test_second_result_relevant(self):
        """First relevant at rank 2."""
        retrieved = [8, 2, 5]
        relevant = [2, 5]
        assert compute_mrr(retrieved, relevant) == 0.5

    def test_third_result_relevant(self):
        """First relevant at rank 3."""
        retrieved = [1, 3, 5, 7]
        relevant = [5]
        assert compute_mrr(retrieved, relevant) == pytest.approx(1 / 3)

    def test_no_relevant_found(self):
        """No relevant chunks in results."""
        retrieved = [1, 2, 3]
        relevant = [4, 5, 6]
        assert compute_mrr(retrieved, relevant) == 0.0

    def test_empty_retrieved(self):
        """No results retrieved."""
        retrieved = []
        relevant = [1, 2, 3]
        assert compute_mrr(retrieved, relevant) == 0.0

    def test_empty_relevant(self):
        """No ground truth relevant chunks."""
        retrieved = [1, 2, 3]
        relevant = []
        assert compute_mrr(retrieved, relevant) == 0.0


class TestNDCGAtK:
    """Test Normalized Discounted Cumulative Gain (NDCG@k)."""

    def test_perfect_ranking(self):
        """Perfect ranking (most relevant first)."""
        retrieved = [2, 5, 0]
        relevance_scores = {2: 3, 5: 2, 0: 1}  # Already sorted by relevance
        assert compute_ndcg_at_k(retrieved, relevance_scores, k=3) == 1.0

    def test_worst_ranking(self):
        """Worst ranking (least relevant first)."""
        retrieved = [0, 5, 2]
        relevance_scores = {2: 3, 5: 2, 0: 1}  # Reverse order
        # DCG = 1/log2(2) + 2/log2(3) + 3/log2(4) ≈ 1.0 + 1.26 + 1.5 = 3.76
        # IDCG = 3/log2(2) + 2/log2(3) + 1/log2(4) ≈ 3.0 + 1.26 + 0.5 = 4.76
        # NDCG = 3.76/4.76 ≈ 0.79
        ndcg = compute_ndcg_at_k(retrieved, relevance_scores, k=3)
        assert 0.7 < ndcg < 0.85  # Approximate range

    def test_partial_ranking(self):
        """Some chunks ranked correctly."""
        retrieved = [2, 0, 5]
        relevance_scores = {2: 3, 5: 2, 0: 1}
        # First chunk correct, last two swapped
        ndcg = compute_ndcg_at_k(retrieved, relevance_scores, k=3)
        assert 0.9 < ndcg < 1.0  # Near-perfect

    def test_all_zeros(self):
        """All chunks have zero relevance."""
        retrieved = [1, 2, 3]
        relevance_scores = {1: 0, 2: 0, 3: 0}
        assert compute_ndcg_at_k(retrieved, relevance_scores, k=3) == 0.0

    def test_empty_scores(self):
        """No relevance scores provided."""
        retrieved = [1, 2, 3]
        relevance_scores = {}
        assert compute_ndcg_at_k(retrieved, relevance_scores, k=3) == 0.0

    def test_k_zero(self):
        """k=0 (no results considered)."""
        retrieved = [2, 5, 0]
        relevance_scores = {2: 3, 5: 2, 0: 1}
        assert compute_ndcg_at_k(retrieved, relevance_scores, k=0) == 0.0

    def test_k_larger_than_retrieved(self):
        """k larger than retrieved chunks."""
        retrieved = [2, 5]
        relevance_scores = {2: 3, 5: 2, 0: 1}
        # Should still work (only use available chunks)
        ndcg = compute_ndcg_at_k(retrieved, relevance_scores, k=5)
        assert 0.0 <= ndcg <= 1.0


class TestComputeAllMetrics:
    """Test compute_all_metrics convenience function."""

    def test_all_metrics_perfect(self):
        """Perfect case: all metrics should be 1.0."""
        retrieved = [2, 5, 0]
        relevant = [2, 5, 0]
        relevance_scores = {2: 3, 5: 2, 0: 1}

        metrics = compute_all_metrics(retrieved, relevant, relevance_scores, k=3)

        assert metrics["recall@3"] == 1.0
        assert metrics["precision@3"] == 1.0
        assert metrics["mrr"] == 1.0
        assert metrics["ndcg@3"] == 1.0

    def test_all_metrics_partial(self):
        """Realistic case with mixed results."""
        retrieved = [2, 5, 8]
        relevant = [0, 2, 5]
        relevance_scores = {2: 3, 5: 2, 0: 1, 8: 0}

        metrics = compute_all_metrics(retrieved, relevant, relevance_scores, k=3)

        # Recall@3 = 2/3 (found 2 out of 3 relevant)
        assert metrics["recall@3"] == pytest.approx(2 / 3)

        # Precision@3 = 2/3 (2 out of top-3 are relevant)
        assert metrics["precision@3"] == pytest.approx(2 / 3)

        # MRR = 1.0 (first result is relevant)
        assert metrics["mrr"] == 1.0

        # NDCG@3 > 0 (some ranking quality)
        assert metrics["ndcg@3"] > 0.0

    def test_all_metrics_zero(self):
        """Worst case: all metrics should be 0.0."""
        retrieved = [1, 2, 3]
        relevant = [4, 5, 6]
        relevance_scores = {1: 0, 2: 0, 3: 0, 4: 3, 5: 2, 6: 1}

        metrics = compute_all_metrics(retrieved, relevant, relevance_scores, k=3)

        assert metrics["recall@3"] == 0.0
        assert metrics["precision@3"] == 0.0
        assert metrics["mrr"] == 0.0
        assert metrics["ndcg@3"] == 0.0

    def test_all_metrics_range(self):
        """All metrics must be in [0.0, 1.0] range."""
        retrieved = [2, 5, 8, 1, 3]
        relevant = [0, 2, 5]
        relevance_scores = {2: 3, 5: 2, 0: 1, 8: 0, 1: 0, 3: 0}

        metrics = compute_all_metrics(retrieved, relevant, relevance_scores, k=3)

        for metric_name, value in metrics.items():
            assert 0.0 <= value <= 1.0, f"{metric_name} out of range: {value}"

    def test_all_metrics_keys(self):
        """Verify all expected keys are present."""
        retrieved = [2, 5, 8]
        relevant = [2, 5]
        relevance_scores = {2: 3, 5: 2, 8: 0}

        metrics = compute_all_metrics(retrieved, relevant, relevance_scores, k=3)

        expected_keys = {"recall@3", "precision@3", "mrr", "ndcg@3"}
        assert set(metrics.keys()) == expected_keys


if __name__ == "__main__":
    # Run tests with: pytest test_metrics.py -v
    pytest.main([__file__, "-v"])
