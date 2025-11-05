from __future__ import annotations

"""
Free Intelligence - LLM Metrics

Prometheus-style metrics for LLM operations (p95, counters, cache hits).

File: backend/llm_metrics.py
Created: 2025-10-29
Card: FI-CORE-FEAT-001

Metrics:
- llm_requests_total (counter)
- llm_latency_p95 (gauge)
- llm_cache_hits_total (counter)
"""

import time
from collections import defaultdict


class LLMMetrics:
    """
    Simple metrics collector for LLM operations.

    Tracks:
    - Total requests
    - Latency samples (for p95 calculation)
    - Cache hits
    """

    def __init__(self):
        self.requests_total = 0
        self.cache_hits_total = 0
        self.latency_samples: list[int] = []
        self.max_samples = 1000  # Keep last 1000 samples for p95
        self.start_time = time.time()

        # Per-provider metrics
        self.provider_metrics: dict[str, dict[str, int]] = defaultdict(
            lambda: {"requests": 0, "cache_hits": 0}
        )

    def record_request(
        self,
        provider: str,
        latency_ms: int,
        cache_hit: bool = False,
    ):
        """
        Record a request.

        Args:
            provider: Provider name (ollama, claude)
            latency_ms: Latency in milliseconds
            cache_hit: Whether this was a cache hit
        """
        self.requests_total += 1
        self.provider_metrics[provider]["requests"] += 1

        if cache_hit:
            self.cache_hits_total += 1
            self.provider_metrics[provider]["cache_hits"] += 1
        else:
            # Only record latency for non-cached requests
            self.latency_samples.append(latency_ms)

            # Keep only last N samples
            if len(self.latency_samples) > self.max_samples:
                self.latency_samples = self.latency_samples[-self.max_samples :]

    def _percentile(self, p: float) -> int:
        """
        Calculate percentile from samples.

        Args:
            p: Percentile (0.0-1.0), e.g., 0.95 for p95

        Returns:
            Percentile value in milliseconds (0 if no samples)
        """
        if not self.latency_samples:
            return 0

        sorted_samples = sorted(self.latency_samples)
        n = len(sorted_samples)
        # Fix off-by-one: ensure index is valid for all n >= 1
        index = min(int(n * p), n - 1)
        return sorted_samples[index]

    def get_p50_latency(self) -> int:
        """Calculate p50 (median) latency from samples."""
        return self._percentile(0.50)

    def get_p95_latency(self) -> int:
        """Calculate p95 latency from samples."""
        return self._percentile(0.95)

    def get_p99_latency(self) -> int:
        """Calculate p99 latency from samples."""
        return self._percentile(0.99)

    def get_cache_hit_rate(self) -> float:
        """
        Calculate cache hit rate.

        Returns:
            Cache hit rate (0.0-1.0)
        """
        if self.requests_total == 0:
            return 0.0
        return self.cache_hits_total / self.requests_total

    def get_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = [
            "# HELP llm_requests_total Total LLM requests",
            "# TYPE llm_requests_total counter",
            f"llm_requests_total {self.requests_total}",
            "",
            "# HELP llm_cache_hits_total Total cache hits",
            "# TYPE llm_cache_hits_total counter",
            f"llm_cache_hits_total {self.cache_hits_total}",
            "",
            "# HELP llm_latency_p50 50th percentile latency (ms)",
            "# TYPE llm_latency_p50 gauge",
            f"llm_latency_p50 {self.get_p50_latency()}",
            "",
            "# HELP llm_latency_p95 95th percentile latency (ms)",
            "# TYPE llm_latency_p95 gauge",
            f"llm_latency_p95 {self.get_p95_latency()}",
            "",
            "# HELP llm_latency_p99 99th percentile latency (ms)",
            "# TYPE llm_latency_p99 gauge",
            f"llm_latency_p99 {self.get_p99_latency()}",
            "",
            "# HELP llm_cache_hit_rate Cache hit rate (0.0-1.0)",
            "# TYPE llm_cache_hit_rate gauge",
            f"llm_cache_hit_rate {self.get_cache_hit_rate():.3f}",
            "",
        ]

        # Per-provider metrics
        for provider, metrics in self.provider_metrics.items():
            lines.append(f'llm_requests_total{{provider="{provider}"}} {metrics["requests"]}')
            lines.append(f'llm_cache_hits_total{{provider="{provider}"}} {metrics["cache_hits"]}')

        return "\n".join(lines)

    def get_stats(self) -> dict[str, any]:
        """
        Get metrics as dictionary.

        Returns:
            Metrics dictionary
        """
        return {
            "requests_total": self.requests_total,
            "cache_hits_total": self.cache_hits_total,
            "cache_hit_rate": self.get_cache_hit_rate(),
            "p50_latency_ms": self.get_p50_latency(),
            "p95_latency_ms": self.get_p95_latency(),
            "p99_latency_ms": self.get_p99_latency(),
            "uptime_seconds": int(time.time() - self.start_time),
            "provider_metrics": dict(self.provider_metrics),
        }

    def reset(self):
        """Reset all metrics."""
        self.requests_total = 0
        self.cache_hits_total = 0
        self.latency_samples = []
        self.provider_metrics.clear()
        self.start_time = time.time()


# Global metrics instance (singleton)
_metrics_instance = None


def get_metrics() -> LLMMetrics:
    """
    Get global metrics instance (singleton).

    Returns:
        LLMMetrics instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = LLMMetrics()
    return _metrics_instance
