from __future__ import annotations

"""
Free Intelligence - Metrics & Telemetry

Local metrics collection without PHI:
- Latency (p50, p95, p99)
- Token usage
- Cost tracking (cloud providers)
- Cache hit rates
- Provider distribution

Philosophy: Observability without privacy compromise.

File: backend/metrics.py
Created: 2025-10-28
"""

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import  datetime, timedelta, timezone
from typing import Any, Optional

from backend.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """Single metric measurement"""

    timestamp: datetime
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class LatencyMetrics:
    """Latency percentiles"""

    p50: float  # median
    p95: float  # 95th percentile
    p99: float  # 99th percentile
    mean: float
    min: float
    max: float
    count: int


@dataclass
class CostMetrics:
    """Cost tracking"""

    total_usd: float
    by_provider: dict[str, float]
    token_count: int
    request_count: int


@dataclass
class CacheMetrics:
    """Cache performance"""

    hit_rate: float  # 0.0 to 1.0
    hits: int
    misses: int
    total_requests: int


class MetricsCollector:
    """
    In-memory metrics collector with time-window retention.

    Collects:
    - LLM latencies
    - Token usage
    - Costs
    - Cache performance
    """

    def __init__(self, retention_hours: int = 24):
        """
        Initialize metrics collector.

        Args:
            retention_hours: How long to keep metrics in memory
        """
        self.retention_hours = retention_hours
        self.logger = get_logger(__name__)

        # Metric storage
        self.latencies: list[MetricPoint] = []
        self.tokens: list[MetricPoint] = []
        self.costs: list[MetricPoint] = []
        self.cache_events: list[MetricPoint] = []

        # Counters
        self.request_count_by_provider: dict[str, int] = defaultdict(int)
        self.error_count_by_provider: dict[str, int] = defaultdict(int)

        self.logger.info("METRICS_COLLECTOR_INITIALIZED", retention_hours=retention_hours)

    def record_llm_request(
        self,
        provider: str,
        model: str,
        latency_ms: float,
        tokens: int,
        cost_usd: float,
        status: str = "success",
    ):
        """
        Record LLM request metrics.

        Args:
            provider: Provider name (claude, ollama)
            model: Model name
            latency_ms: Request latency in milliseconds
            tokens: Total tokens used
            cost_usd: Cost in USD
            status: Request status (success, error)
        """
        now = datetime.now(timezone.utc)
        labels = {"provider": provider, "model": model, "status": status}

        # Record latency
        self.latencies.append(MetricPoint(timestamp=now, value=latency_ms, labels=labels))

        # Record tokens
        self.tokens.append(MetricPoint(timestamp=now, value=float(tokens), labels=labels))

        # Record cost
        self.costs.append(MetricPoint(timestamp=now, value=cost_usd, labels=labels))

        # Update counters
        if status == "success":
            self.request_count_by_provider[provider] += 1
        else:
            self.error_count_by_provider[provider] += 1

        # Cleanup old metrics
        self._cleanup_old_metrics()

        self.logger.info(
            "LLM_REQUEST_RECORDED",
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            tokens=tokens,
            cost_usd=cost_usd,
            status=status,
        )

    def record_cache_event(
        self,
        event_type: str,  # "hit" or "miss"
        provider: str,
    ):
        """
        Record cache hit/miss event.

        Args:
            event_type: "hit" or "miss"
            provider: Provider name
        """
        now = datetime.now(timezone.utc)

        self.cache_events.append(
            MetricPoint(
                timestamp=now,
                value=1.0 if event_type == "hit" else 0.0,
                labels={"provider": provider, "event": event_type},
            )
        )

        self._cleanup_old_metrics()

    def get_latency_metrics(
        self, provider: Optional[str] = None, window_hours: Optional[int] = None
    ) -> Optional[LatencyMetrics]:
        """
        Calculate latency percentiles.

        Args:
            provider: Filter by provider (None = all)
            window_hours: Time window (None = all data)

        Returns:
            LatencyMetrics or None if no data
        """
        # Filter data
        data = self._filter_metrics(self.latencies, provider=provider, window_hours=window_hours)

        if not data:
            return None

        values = [m.value for m in data]
        values.sort()

        count = len(values)

        return LatencyMetrics(
            p50=self._percentile(values, 50),
            p95=self._percentile(values, 95),
            p99=self._percentile(values, 99),
            mean=statistics.mean(values),
            min=min(values),
            max=max(values),
            count=count,
        )

    def get_cost_metrics(self, window_hours: Optional[int] = None) -> CostMetrics:
        """
        Calculate cost metrics.

        Args:
            window_hours: Time window (None = all data)

        Returns:
            CostMetrics
        """
        # Filter data
        data = self._filter_metrics(self.costs, window_hours=window_hours)

        total_usd = sum(m.value for m in data)

        # Cost by provider
        by_provider = defaultdict(float)
        for m in data:
            provider = m.labels.get("provider", "unknown")
            by_provider[provider] += m.value

        # Token count
        token_data = self._filter_metrics(self.tokens, window_hours=window_hours)
        token_count = int(sum(m.value for m in token_data))

        return CostMetrics(
            total_usd=total_usd,
            by_provider=dict(by_provider),
            token_count=token_count,
            request_count=len(data),
        )

    def get_cache_metrics(
        self, provider: Optional[str] = None, window_hours: Optional[int] = None
    ) -> CacheMetrics:
        """
        Calculate cache hit rate.

        Args:
            provider: Filter by provider (None = all)
            window_hours: Time window (None = all data)

        Returns:
            CacheMetrics
        """
        # Filter data
        data = self._filter_metrics(self.cache_events, provider=provider, window_hours=window_hours)

        if not data:
            return CacheMetrics(hit_rate=0.0, hits=0, misses=0, total_requests=0)

        hits = sum(1 for m in data if m.labels.get("event") == "hit")
        misses = sum(1 for m in data if m.labels.get("event") == "miss")
        total = hits + misses

        hit_rate = hits / total if total > 0 else 0.0

        return CacheMetrics(hit_rate=hit_rate, hits=hits, misses=misses, total_requests=total)

    def get_provider_distribution(self, window_hours: Optional[int] = None) -> dict[str, int]:
        """
        Get request count by provider.

        Args:
            window_hours: Time window (None = all data)

        Returns:
            Dict of provider -> request count
        """
        data = self._filter_metrics(self.latencies, window_hours=window_hours)

        distribution = defaultdict(int)
        for m in data:
            provider = m.labels.get("provider", "unknown")
            distribution[provider] += 1

        return dict(distribution)

    def _filter_metrics(
        self,
        metrics: list[MetricPoint],
        provider: Optional[str] = None,
        window_hours: Optional[int] = None,
    ) -> list[MetricPoint]:
        """Filter metrics by provider and time window"""
        result = metrics

        # Filter by provider
        if provider:
            result = [m for m in result if m.labels.get("provider") == provider]

        # Filter by time window
        if window_hours:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
            result = [m for m in result if m.timestamp >= cutoff]

        return result

    def _percentile(self, sorted_values: list[float], percentile: int) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * (percentile / 100.0)
        f = int(k)
        c = f + 1

        if c >= len(sorted_values):
            return sorted_values[-1]

        d0 = sorted_values[f]
        d1 = sorted_values[c]

        return d0 + (d1 - d0) * (k - f)

    def _cleanup_old_metrics(self):
        """Remove metrics older than retention window"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)

        self.latencies = [m for m in self.latencies if m.timestamp >= cutoff]
        self.tokens = [m for m in self.tokens if m.timestamp >= cutoff]
        self.costs = [m for m in self.costs if m.timestamp >= cutoff]
        self.cache_events = [m for m in self.cache_events if m.timestamp >= cutoff]

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all metrics"""
        latency = self.get_latency_metrics()
        cost = self.get_cost_metrics()
        cache = self.get_cache_metrics()
        distribution = self.get_provider_distribution()

        return {
            "latency": {
                "p50_ms": latency.p50 if latency else 0,
                "p95_ms": latency.p95 if latency else 0,
                "p99_ms": latency.p99 if latency else 0,
                "mean_ms": latency.mean if latency else 0,
                "count": latency.count if latency else 0,
            },
            "cost": {
                "total_usd": cost.total_usd,
                "by_provider": cost.by_provider,
                "tokens": cost.token_count,
                "requests": cost.request_count,
            },
            "cache": {"hit_rate": cache.hit_rate, "hits": cache.hits, "misses": cache.misses},
            "provider_distribution": distribution,
            "errors_by_provider": dict(self.error_count_by_provider),
        }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_collector

    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()

    return _metrics_collector


# ============================================================================
# CLI INTERFACE
# ============================================================================


def main():
    """CLI interface for metrics"""
    import argparse

    parser = argparse.ArgumentParser(description="Free Intelligence Metrics CLI")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Show metrics summary")
    summary_parser.add_argument("--hours", type=int, help="Time window in hours")

    args = parser.parse_args()

    collector = get_metrics_collector()

    if args.command == "summary":
        summary = collector.get_summary()

        print("\n" + "=" * 70)
        print("📊 Free Intelligence Metrics Summary")
        print("=" * 70)

        print("\n⏱️  Latency:")
        print(f"  p50: {summary['latency']['p50_ms']:.0f}ms")
        print(f"  p95: {summary['latency']['p95_ms']:.0f}ms")
        print(f"  p99: {summary['latency']['p99_ms']:.0f}ms")
        print(f"  Requests: {summary['latency']['count']}")

        print("\n💰 Cost:")
        print(f"  Total: ${summary['cost']['total_usd']:.6f}")
        print(f"  Tokens: {summary['cost']['tokens']:,}")
        print("  By Provider:")
        for provider, cost in summary["cost"]["by_provider"].items():
            print(f"    {provider}: ${cost:.6f}")

        print("\n🔄 Cache:")
        print(f"  Hit Rate: {summary['cache']['hit_rate']*100:.1f}%")
        print(f"  Hits: {summary['cache']['hits']}")
        print(f"  Misses: {summary['cache']['misses']}")

        print("\n📡 Provider Distribution:")
        for provider, count in summary["provider_distribution"].items():
            print(f"  {provider}: {count} requests")

        print("\n" + "=" * 70)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
