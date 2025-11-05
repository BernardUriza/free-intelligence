from __future__ import annotations

"""
Free Intelligence - KPIs Aggregator

In-memory KPIs aggregator with time-window bucketing for /api/kpis endpoint.

Philosophy (AURITY):
- Medir antes de opinar: métricas como contrato, no como adorno
- Observabilidad mínima suficiente: bajo costo, alta señal
- Determinismo y trazabilidad: sin "estimaciones mágicas"

File: backend/kpis_aggregator.py
Created: 2025-10-30
Card: FI-API-FEAT-011
"""

import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional

from backend.logger import get_logger

logger = get_logger(__name__)


# Environment variables
METRICS_ENABLED = os.getenv("METRICS_ENABLED", "1") == "1"
METRICS_RETENTION_MIN = int(os.getenv("METRICS_RETENTION_MIN", "1440"))  # 24h
METRICS_BUCKET_SEC = int(os.getenv("METRICS_BUCKET_SEC", "10"))  # 10s granularity
METRICS_DEFAULT_WINDOW = os.getenv("METRICS_DEFAULT_WINDOW", "5m")


@dataclass
class HTTPMetricEvent:
    """Single HTTP request metric event"""

    timestamp: float  # Unix timestamp
    route: str  # Route template (e.g., /api/sessions)
    status: int  # HTTP status code
    duration_ms: int  # Request duration
    cache_hit: bool = False


@dataclass
class LLMMetricEvent:
    """Single LLM request metric event"""

    timestamp: float  # Unix timestamp
    provider: str  # anthropic, openai, local
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latency_ms: int = 0
    cache_hit: bool = False


@dataclass
class MetricsBucket:
    """Aggregated metrics for a time bucket"""

    start_ts: float
    end_ts: float

    # HTTP metrics
    http_requests_total: int = 0
    http_2xx: int = 0
    http_4xx: int = 0
    http_5xx: int = 0
    http_latencies: list[int] = field(default_factory=list)

    # LLM metrics
    llm_tokens_in: int = 0
    llm_tokens_out: int = 0
    llm_tokens_unknown: int = 0  # Count of requests with unknown tokens
    llm_latencies: list[int] = field(default_factory=list)
    llm_cache_hits: int = 0
    llm_cache_misses: int = 0

    # Provider distribution
    provider_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))


class KPIsAggregator:
    """
    In-memory KPIs aggregator with time-window bucketing.

    Collects HTTP and LLM metrics into time-based buckets for efficient querying.
    Supports sliding time windows: 1m, 5m, 15m, 1h, 24h.
    """

    def __init__(
        self,
        bucket_sec: int = METRICS_BUCKET_SEC,
        retention_min: int = METRICS_RETENTION_MIN,
    ):
        """
        Initialize KPIs aggregator.

        Args:
            bucket_sec: Bucket granularity in seconds (default: 10)
            retention_min: Data retention in minutes (default: 1440 = 24h)
        """
        self.bucket_sec = bucket_sec
        self.retention_min = retention_min
        self.retention_sec = retention_min * 60

        # Buckets: {bucket_start_ts -> MetricsBucket}
        self.buckets: dict[float, MetricsBucket] = {}

        # Last cleanup timestamp
        self.last_cleanup_ts = time.time()

        logger.info(
            "KPIS_AGGREGATOR_INITIALIZED",
            bucket_sec=bucket_sec,
            retention_min=retention_min,
        )

    def record_http_event(
        self,
        route: str,
        status: int,
        duration_ms: int,
        cache_hit: bool = False,
    ):
        """
        Record HTTP request event.

        Args:
            route: Route template (e.g., /api/sessions)
            status: HTTP status code
            duration_ms: Request duration in ms
            cache_hit: Whether this was a cache hit
        """
        if not METRICS_ENABLED:
            return

        event = HTTPMetricEvent(
            timestamp=time.time(),
            route=route,
            status=status,
            duration_ms=duration_ms,
            cache_hit=cache_hit,
        )

        bucket = self._get_or_create_bucket(event.timestamp)

        # Update HTTP counters
        bucket.http_requests_total += 1
        if 200 <= status < 300:
            bucket.http_2xx += 1
        elif 400 <= status < 500:
            bucket.http_4xx += 1
        elif 500 <= status < 600:
            bucket.http_5xx += 1

        # Record latency
        bucket.http_latencies.append(duration_ms)

        # Cleanup old buckets periodically
        self._cleanup_if_needed()

    def record_llm_event(
        self,
        provider: str,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        latency_ms: int = 0,
        cache_hit: bool = False,
    ):
        """
        Record LLM request event.

        Args:
            provider: Provider name (anthropic, openai, local)
            tokens_in: Input tokens (None if unknown)
            tokens_out: Output tokens (None if unknown)
            latency_ms: Request latency in ms
            cache_hit: Whether this was a cache hit
        """
        if not METRICS_ENABLED:
            return

        event = LLMMetricEvent(
            timestamp=time.time(),
            provider=provider,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
        )

        bucket = self._get_or_create_bucket(event.timestamp)

        # Update token counters
        if tokens_in is not None:
            bucket.llm_tokens_in += tokens_in
        else:
            bucket.llm_tokens_unknown += 1

        if tokens_out is not None:
            bucket.llm_tokens_out += tokens_out
        else:
            bucket.llm_tokens_unknown += 1

        # Update cache counters
        if cache_hit:
            bucket.llm_cache_hits += 1
        else:
            bucket.llm_cache_misses += 1

        # Record latency (only for non-cached requests)
        if not cache_hit:
            bucket.llm_latencies.append(latency_ms)

        # Update provider distribution
        bucket.provider_counts[provider] += 1

        # Cleanup old buckets periodically
        self._cleanup_if_needed()

    def get_summary(
        self,
        window: str = "5m",
        route_filter: Optional[str] = None,
        provider_filter: Optional[str] = None,
    ) -> dict:
        """
        Get summary metrics for time window.

        Args:
            window: Time window (1m, 5m, 15m, 1h, 24h)
            route_filter: Filter by route (None = all)
            provider_filter: Filter by provider (None = all)

        Returns:
            Summary dict with requests, latency, tokens, cache, providers
        """
        buckets = self._get_buckets_in_window(window)

        if not buckets:
            return self._empty_summary(window)

        # Aggregate metrics across buckets
        total_requests = sum(b.http_requests_total for b in buckets)
        total_2xx = sum(b.http_2xx for b in buckets)
        total_4xx = sum(b.http_4xx for b in buckets)
        total_5xx = sum(b.http_5xx for b in buckets)

        # Aggregate latencies
        all_http_latencies = []
        for b in buckets:
            all_http_latencies.extend(b.http_latencies)

        all_llm_latencies = []
        for b in buckets:
            all_llm_latencies.extend(b.llm_latencies)

        # Aggregate tokens
        total_tokens_in = sum(b.llm_tokens_in for b in buckets)
        total_tokens_out = sum(b.llm_tokens_out for b in buckets)
        total_tokens_unknown = sum(b.llm_tokens_unknown for b in buckets)

        # Aggregate cache
        total_cache_hits = sum(b.llm_cache_hits for b in buckets)
        total_cache_misses = sum(b.llm_cache_misses for b in buckets)
        total_cache_requests = total_cache_hits + total_cache_misses
        cache_hit_ratio = (
            total_cache_hits / total_cache_requests if total_cache_requests > 0 else 0.0
        )

        # Aggregate provider distribution
        provider_totals = defaultdict(int)
        for b in buckets:
            for provider, count in b.provider_counts.items():
                provider_totals[provider] += count

        total_provider_requests = sum(provider_totals.values())
        providers = [
            {
                "id": provider,
                "count": count,
                "pct": count / total_provider_requests if total_provider_requests > 0 else 0.0,
            }
            for provider, count in sorted(provider_totals.items(), key=lambda x: x[1], reverse=True)
        ]

        # Calculate latency percentiles (use combined latencies for now)
        combined_latencies = all_http_latencies + all_llm_latencies
        latency_metrics = self._calculate_percentiles(combined_latencies)

        return {
            "window": window,
            "asOf": datetime.now(UTC).isoformat() + "Z",
            "requests": {
                "total": total_requests,
                "2xx": total_2xx,
                "4xx": total_4xx,
                "5xx": total_5xx,
            },
            "latency": latency_metrics,
            "tokens": {
                "in": total_tokens_in,
                "out": total_tokens_out,
                "unknown": total_tokens_unknown,
            },
            "cache": {
                "hit": total_cache_hits,
                "miss": total_cache_misses,
                "hit_ratio": round(cache_hit_ratio, 3),
            },
            "providers": providers,
        }

    def get_chips(self, window: str = "5m") -> dict:
        """
        Get metrics formatted as chips for UI-204/205.

        Args:
            window: Time window (1m, 5m, 15m, 1h, 24h)

        Returns:
            Chips dict ready for UI consumption
        """
        summary = self.get_summary(window)

        # Calculate trends (simplified: compare to previous window)
        # TODO: Implement trend calculation

        chips = [
            {
                "id": "tokens_in",
                "label": "Tokens In",
                "value": summary["tokens"]["in"],
                "unit": "tok",
                "trend": "→",  # TODO: Calculate trend
            },
            {
                "id": "tokens_out",
                "label": "Tokens Out",
                "value": summary["tokens"]["out"],
                "unit": "tok",
                "trend": "→",
            },
            {
                "id": "p95_ms",
                "label": "p95",
                "value": summary["latency"]["p95_ms"],
                "unit": "ms",
                "trend": "→",
            },
            {
                "id": "cache_hit",
                "label": "Cache Hit",
                "value": summary["cache"]["hit_ratio"],
                "unit": "ratio",
                "trend": "→",
            },
            {
                "id": "provider_mix",
                "label": "Providers",
                "value": [{"id": p["id"], "pct": p["pct"]} for p in summary["providers"]],
            },
        ]

        return {
            "window": window,
            "asOf": summary["asOf"],
            "chips": chips,
        }

    def get_timeseries(
        self,
        window: str = "15m",
        bucket_sec: Optional[int] = None,
    ) -> dict:
        """
        Get timeseries data for sparklines (UI-204/205).

        Args:
            window: Time window (1m, 5m, 15m, 1h, 24h)
            bucket_sec: Bucket granularity override (None = use default)

        Returns:
            Timeseries dict with series arrays
        """
        buckets = self._get_buckets_in_window(window)

        if not buckets:
            return {
                "window": window,
                "asOf": datetime.now(UTC).isoformat() + "Z",
                "bucketSec": bucket_sec or self.bucket_sec,
                "series": {
                    "p95_ms": [],
                    "tokens_in": [],
                    "tokens_out": [],
                    "cache_hit_ratio": [],
                },
            }

        # Build timeseries arrays
        p95_series = []
        tokens_in_series = []
        tokens_out_series = []
        cache_hit_ratio_series = []

        for bucket in sorted(buckets, key=lambda b: b.start_ts):
            ts = int(bucket.start_ts * 1000)  # Convert to milliseconds

            # Calculate p95 for this bucket
            combined_latencies = bucket.http_latencies + bucket.llm_latencies
            p95 = self._percentile(sorted(combined_latencies), 95) if combined_latencies else 0
            p95_series.append([ts, p95])

            # Tokens
            tokens_in_series.append([ts, bucket.llm_tokens_in])
            tokens_out_series.append([ts, bucket.llm_tokens_out])

            # Cache hit ratio
            total_cache = bucket.llm_cache_hits + bucket.llm_cache_misses
            ratio = bucket.llm_cache_hits / total_cache if total_cache > 0 else 0.0
            cache_hit_ratio_series.append([ts, round(ratio, 3)])

        return {
            "window": window,
            "asOf": datetime.now(UTC).isoformat() + "Z",
            "bucketSec": bucket_sec or self.bucket_sec,
            "series": {
                "p95_ms": p95_series,
                "tokens_in": tokens_in_series,
                "tokens_out": tokens_out_series,
                "cache_hit_ratio": cache_hit_ratio_series,
            },
        }

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _get_or_create_bucket(self, timestamp: float) -> MetricsBucket:
        """Get or create bucket for timestamp."""
        bucket_start = (int(timestamp) // self.bucket_sec) * self.bucket_sec

        if bucket_start not in self.buckets:
            self.buckets[bucket_start] = MetricsBucket(
                start_ts=bucket_start,
                end_ts=bucket_start + self.bucket_sec,
            )

        return self.buckets[bucket_start]

    def _get_buckets_in_window(self, window: str) -> list[MetricsBucket]:
        """Get all buckets within time window."""
        now = time.time()
        window_sec = self._parse_window(window)
        cutoff = now - window_sec

        return [bucket for bucket in self.buckets.values() if bucket.start_ts >= cutoff]

    def _parse_window(self, window: str) -> int:
        """Parse window string to seconds."""
        if window == "1m":
            return 60
        elif window == "5m":
            return 300
        elif window == "15m":
            return 900
        elif window == "1h":
            return 3600
        elif window == "24h":
            return 86400
        else:
            logger.warning("INVALID_WINDOW", window=window, fallback="5m")
            return 300  # Default to 5m

    def _cleanup_if_needed(self):
        """Cleanup old buckets if retention window expired."""
        now = time.time()

        # Cleanup every 60 seconds
        if now - self.last_cleanup_ts < 60:
            return

        self.last_cleanup_ts = now
        cutoff = now - self.retention_sec

        # Remove old buckets
        old_count = len(self.buckets)
        self.buckets = {
            ts: bucket for ts, bucket in self.buckets.items() if bucket.start_ts >= cutoff
        }
        new_count = len(self.buckets)

        if old_count > new_count:
            logger.info(
                "KPIS_BUCKETS_CLEANED",
                old_count=old_count,
                new_count=new_count,
                removed=old_count - new_count,
            )

    def _calculate_percentiles(self, latencies: list[int]) -> dict:
        """Calculate latency percentiles."""
        if not latencies:
            return {
                "p50_ms": 0,
                "p95_ms": 0,
                "max_ms": 0,
            }

        sorted_latencies = sorted(latencies)

        return {
            "p50_ms": self._percentile(sorted_latencies, 50),
            "p95_ms": self._percentile(sorted_latencies, 95),
            "max_ms": sorted_latencies[-1] if sorted_latencies else 0,
        }

    def _percentile(self, sorted_values: list[int], percentile: int) -> int:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0

        n = len(sorted_values)
        index = min(int(n * (percentile / 100.0)), n - 1)
        return sorted_values[index]

    def _empty_summary(self, window: str) -> dict:
        """Return empty summary for when no data available."""
        return {
            "window": window,
            "asOf": datetime.now(UTC).isoformat() + "Z",
            "requests": {"total": 0, "2xx": 0, "4xx": 0, "5xx": 0},
            "latency": {"p50_ms": 0, "p95_ms": 0, "max_ms": 0},
            "tokens": {"in": 0, "out": 0, "unknown": 0},
            "cache": {"hit": 0, "miss": 0, "hit_ratio": 0.0},
            "providers": [],
        }


# Global singleton instance
_kpis_aggregator: Optional[KPIsAggregator] = None


def get_kpis_aggregator() -> KPIsAggregator:
    """Get or create global KPIs aggregator instance."""
    global _kpis_aggregator

    if _kpis_aggregator is None:
        _kpis_aggregator = KPIsAggregator()

    return _kpis_aggregator
