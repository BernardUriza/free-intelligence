"""
Test suite for LLM metrics calculation.

File: tests/test_llm_metrics.py
Created: 2025-10-29
Card: FI-CORE-REF-001

Tests:
- Percentile edge cases (empty, n=1, small, large datasets)
- p50 < p95 < p99 invariant
- Cache hit rate calculation
- Prometheus export format
"""

import pytest

from backend.llm_metrics import LLMMetrics


class TestLLMMetrics:
    """Test LLM metrics calculation."""

    def test_empty_samples(self):
        """Test percentiles with no samples."""
        metrics = LLMMetrics()
        assert metrics.get_p50_latency() == 0
        assert metrics.get_p95_latency() == 0
        assert metrics.get_p99_latency() == 0

    def test_single_sample(self):
        """Test percentiles with n=1 (edge case for off-by-one)."""
        metrics = LLMMetrics()
        metrics.record_request("ollama", latency_ms=100, cache_hit=False)

        # All percentiles should return the single value
        assert metrics.get_p50_latency() == 100
        assert metrics.get_p95_latency() == 100
        assert metrics.get_p99_latency() == 100

    def test_two_samples(self):
        """Test percentiles with n=2."""
        metrics = LLMMetrics()
        metrics.record_request("ollama", latency_ms=100, cache_hit=False)
        metrics.record_request("ollama", latency_ms=200, cache_hit=False)

        # Sorted: [100, 200]
        # p50: index = min(int(2 * 0.5), 1) = min(1, 1) = 1 → value 200
        # p95: index = min(int(2 * 0.95), 1) = min(1, 1) = 1 → value 200
        # p99: index = min(int(2 * 0.99), 1) = min(1, 1) = 1 → value 200
        assert metrics.get_p50_latency() == 200
        assert metrics.get_p95_latency() == 200
        assert metrics.get_p99_latency() == 200

    def test_ten_samples(self):
        """Test percentiles with n=10."""
        metrics = LLMMetrics()
        for i in range(1, 11):  # 10, 20, 30, ..., 100
            metrics.record_request("ollama", latency_ms=i * 10, cache_hit=False)

        # Sorted: [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        # p50: index min(int(10*0.5), 9) = min(5, 9) = 5 → value 60
        # p95: index min(int(10*0.95), 9) = min(9, 9) = 9 → value 100
        # p99: index min(int(10*0.99), 9) = min(9, 9) = 9 → value 100
        assert metrics.get_p50_latency() == 60
        assert metrics.get_p95_latency() == 100
        assert metrics.get_p99_latency() == 100

    def test_hundred_samples(self):
        """Test percentiles with n=100."""
        metrics = LLMMetrics()
        for i in range(1, 101):  # 1, 2, 3, ..., 100
            metrics.record_request("ollama", latency_ms=i, cache_hit=False)

        # Sorted: [1, 2, ..., 100]
        # p50: index min(int(100*0.5), 99) = min(50, 99) = 50 → value 51
        # p95: index min(int(100*0.95), 99) = min(95, 99) = 95 → value 96
        # p99: index min(int(100*0.99), 99) = min(99, 99) = 99 → value 100
        assert metrics.get_p50_latency() == 51
        assert metrics.get_p95_latency() == 96
        assert metrics.get_p99_latency() == 100

    def test_thousand_samples(self):
        """Test percentiles with n=1000 (max samples)."""
        metrics = LLMMetrics()
        for i in range(1, 1001):  # 1, 2, 3, ..., 1000
            metrics.record_request("ollama", latency_ms=i, cache_hit=False)

        # Verify we kept exactly 1000 samples (max_samples limit)
        assert len(metrics.latency_samples) == 1000

        # p50: index min(int(1000*0.5), 999) = min(500, 999) = 500 → value 501
        # p95: index min(int(1000*0.95), 999) = min(950, 999) = 950 → value 951
        # p99: index min(int(1000*0.99), 999) = min(990, 999) = 990 → value 991
        assert metrics.get_p50_latency() == 501
        assert metrics.get_p95_latency() == 951
        assert metrics.get_p99_latency() == 991

    def test_percentile_invariant(self):
        """Test p50 <= p95 <= p99 invariant."""
        metrics = LLMMetrics()

        # Add random-ish samples
        for i in [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]:
            metrics.record_request("ollama", latency_ms=i, cache_hit=False)

        p50 = metrics.get_p50_latency()
        p95 = metrics.get_p95_latency()
        p99 = metrics.get_p99_latency()

        # Invariant: p50 <= p95 <= p99
        assert p50 <= p95, f"p50 ({p50}) should be <= p95 ({p95})"
        assert p95 <= p99, f"p95 ({p95}) should be <= p99 ({p99})"

    def test_cache_hit_not_included_in_latency(self):
        """Test that cache hits don't affect latency samples."""
        metrics = LLMMetrics()

        # Add non-cached requests
        metrics.record_request("ollama", latency_ms=100, cache_hit=False)
        metrics.record_request("ollama", latency_ms=200, cache_hit=False)

        # Add cached request (should not affect latency)
        metrics.record_request("ollama", latency_ms=999, cache_hit=True)

        # Latency samples should only contain non-cached requests
        assert len(metrics.latency_samples) == 2
        assert metrics.get_p95_latency() == 200  # Not 999

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        metrics = LLMMetrics()

        # 7 requests, 3 cache hits
        metrics.record_request("ollama", latency_ms=100, cache_hit=False)
        metrics.record_request("ollama", latency_ms=100, cache_hit=True)
        metrics.record_request("ollama", latency_ms=100, cache_hit=False)
        metrics.record_request("ollama", latency_ms=100, cache_hit=True)
        metrics.record_request("ollama", latency_ms=100, cache_hit=False)
        metrics.record_request("ollama", latency_ms=100, cache_hit=True)
        metrics.record_request("ollama", latency_ms=100, cache_hit=False)

        assert metrics.requests_total == 7
        assert metrics.cache_hits_total == 3
        assert metrics.get_cache_hit_rate() == pytest.approx(3 / 7, rel=1e-3)

    def test_prometheus_export_format(self):
        """Test Prometheus metrics export."""
        metrics = LLMMetrics()
        metrics.record_request("ollama", latency_ms=100, cache_hit=False)
        metrics.record_request("claude", latency_ms=200, cache_hit=True)

        prom = metrics.get_prometheus_metrics()

        # Verify format
        assert "llm_requests_total 2" in prom
        assert "llm_cache_hits_total 1" in prom
        assert "llm_latency_p50 100" in prom
        assert "llm_latency_p95 100" in prom
        assert "llm_latency_p99 100" in prom
        assert 'llm_requests_total{provider="ollama"} 1' in prom
        assert 'llm_requests_total{provider="claude"} 1' in prom

    def test_get_stats(self):
        """Test stats dictionary output."""
        metrics = LLMMetrics()
        metrics.record_request("ollama", latency_ms=100, cache_hit=False)
        metrics.record_request("ollama", latency_ms=200, cache_hit=False)

        stats = metrics.get_stats()

        assert stats["requests_total"] == 2
        assert stats["cache_hits_total"] == 0
        assert stats["cache_hit_rate"] == 0.0
        # For n=2: p50 index = min(int(2*0.5), 1) = 1 → value 200
        assert stats["p50_latency_ms"] == 200
        assert stats["p95_latency_ms"] == 200
        assert stats["p99_latency_ms"] == 200
        assert "uptime_seconds" in stats
        assert "provider_metrics" in stats

    def test_reset(self):
        """Test metrics reset."""
        metrics = LLMMetrics()
        metrics.record_request("ollama", latency_ms=100, cache_hit=False)
        metrics.record_request("claude", latency_ms=200, cache_hit=True)

        # Reset
        metrics.reset()

        # Verify all metrics are cleared
        assert metrics.requests_total == 0
        assert metrics.cache_hits_total == 0
        assert len(metrics.latency_samples) == 0
        assert len(metrics.provider_metrics) == 0
        assert metrics.get_p95_latency() == 0
