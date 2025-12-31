"""Event Metrics - Prometheus-compatible metrics for Event Sourcing.

Metrics tracked:
- events_published_total: Counter of published events by type
- events_persisted_total: Counter of persisted events
- event_publish_latency_seconds: Histogram of publish latency
- projection_events_processed_total: Counter by projection
- projection_lag_seconds: Gauge of projection lag
- consumer_lag_events: Gauge of consumer lag in events

Usage:
    from backend.src.fi_events.observability.metrics import get_metrics

    metrics = get_metrics()
    metrics.record_event_published("TRANSCRIPTION_STARTED", 0.005)
    metrics.set_projection_lag("session_index", 2.5)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MetricValue:
    """A single metric value with labels."""

    name: str
    labels: dict[str, str]
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class HistogramBucket:
    """Histogram bucket for latency tracking."""

    le: float  # Less than or equal
    count: int = 0


class EventMetrics:
    """Prometheus-compatible metrics collector for Event Sourcing.

    Implements a subset of Prometheus metrics:
    - Counter: Monotonically increasing values
    - Gauge: Values that go up and down
    - Histogram: Distribution of values (latency)
    """

    # Default histogram buckets (in seconds)
    DEFAULT_LATENCY_BUCKETS = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]

    def __init__(self) -> None:
        # Counters
        self._events_published: dict[str, int] = {}
        self._events_persisted: dict[str, int] = {}
        self._events_failed: dict[str, int] = {}
        self._projection_events: dict[str, int] = {}

        # Gauges
        self._projection_lag: dict[str, float] = {}
        self._consumer_lag: dict[str, int] = {}
        self._active_sse_connections: int = 0

        # Histograms (buckets)
        self._publish_latency_buckets: dict[str, list[HistogramBucket]] = {}
        self._publish_latency_sum: dict[str, float] = {}
        self._publish_latency_count: dict[str, int] = {}

        # Metadata
        self._started_at = datetime.now(UTC)

        logger.info("EVENT_METRICS_INITIALIZED")

    # =========================================================================
    # COUNTERS
    # =========================================================================

    def record_event_published(
        self,
        event_type: str,
        latency_seconds: float,
        persisted: bool = True,
    ) -> None:
        """Record a published event.

        Args:
            event_type: Type of event
            latency_seconds: Time taken to publish
            persisted: Whether event was persisted
        """
        # Increment counter
        self._events_published[event_type] = self._events_published.get(event_type, 0) + 1

        if persisted:
            self._events_persisted[event_type] = self._events_persisted.get(event_type, 0) + 1

        # Record latency
        self._record_latency(event_type, latency_seconds)

    def record_event_failed(self, event_type: str, error_type: str) -> None:
        """Record a failed event.

        Args:
            event_type: Type of event
            error_type: Type of error
        """
        key = f"{event_type}:{error_type}"
        self._events_failed[key] = self._events_failed.get(key, 0) + 1

    def record_projection_event(self, projection_name: str) -> None:
        """Record an event processed by a projection.

        Args:
            projection_name: Name of the projection
        """
        self._projection_events[projection_name] = (
            self._projection_events.get(projection_name, 0) + 1
        )

    # =========================================================================
    # GAUGES
    # =========================================================================

    def set_projection_lag(self, projection_name: str, lag_seconds: float) -> None:
        """Set projection lag in seconds.

        Args:
            projection_name: Name of the projection
            lag_seconds: Lag in seconds
        """
        self._projection_lag[projection_name] = lag_seconds

    def set_consumer_lag(self, consumer_group: str, lag_events: int) -> None:
        """Set consumer lag in events.

        Args:
            consumer_group: Consumer group name
            lag_events: Number of events behind
        """
        self._consumer_lag[consumer_group] = lag_events

    def increment_sse_connections(self) -> None:
        """Increment active SSE connections."""
        self._active_sse_connections += 1

    def decrement_sse_connections(self) -> None:
        """Decrement active SSE connections."""
        self._active_sse_connections = max(0, self._active_sse_connections - 1)

    # =========================================================================
    # HISTOGRAMS
    # =========================================================================

    def _record_latency(self, event_type: str, latency_seconds: float) -> None:
        """Record latency in histogram buckets.

        Args:
            event_type: Type of event
            latency_seconds: Latency in seconds
        """
        # Initialize buckets if needed
        if event_type not in self._publish_latency_buckets:
            self._publish_latency_buckets[event_type] = [
                HistogramBucket(le=b) for b in self.DEFAULT_LATENCY_BUCKETS
            ]
            self._publish_latency_buckets[event_type].append(HistogramBucket(le=float("inf")))
            self._publish_latency_sum[event_type] = 0.0
            self._publish_latency_count[event_type] = 0

        # Increment appropriate buckets
        for bucket in self._publish_latency_buckets[event_type]:
            if latency_seconds <= bucket.le:
                bucket.count += 1

        # Update sum and count
        self._publish_latency_sum[event_type] += latency_seconds
        self._publish_latency_count[event_type] += 1

    # =========================================================================
    # EXPORT (Prometheus format)
    # =========================================================================

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = []

        # events_published_total
        lines.append("# HELP events_published_total Total events published by type")
        lines.append("# TYPE events_published_total counter")
        for event_type, count in self._events_published.items():
            lines.append(f'events_published_total{{event_type="{event_type}"}} {count}')

        # events_persisted_total
        lines.append("# HELP events_persisted_total Total events persisted by type")
        lines.append("# TYPE events_persisted_total counter")
        for event_type, count in self._events_persisted.items():
            lines.append(f'events_persisted_total{{event_type="{event_type}"}} {count}')

        # events_failed_total
        lines.append("# HELP events_failed_total Total failed events by type and error")
        lines.append("# TYPE events_failed_total counter")
        for key, count in self._events_failed.items():
            event_type, error_type = key.split(":", 1)
            lines.append(
                f'events_failed_total{{event_type="{event_type}",error="{error_type}"}} {count}'
            )

        # projection_events_processed_total
        lines.append("# HELP projection_events_processed_total Events processed by projection")
        lines.append("# TYPE projection_events_processed_total counter")
        for name, count in self._projection_events.items():
            lines.append(f'projection_events_processed_total{{projection="{name}"}} {count}')

        # projection_lag_seconds
        lines.append("# HELP projection_lag_seconds Projection lag in seconds")
        lines.append("# TYPE projection_lag_seconds gauge")
        for name, lag in self._projection_lag.items():
            lines.append(f'projection_lag_seconds{{projection="{name}"}} {lag}')

        # consumer_lag_events
        lines.append("# HELP consumer_lag_events Consumer lag in events")
        lines.append("# TYPE consumer_lag_events gauge")
        for consumer, lag in self._consumer_lag.items():
            lines.append(f'consumer_lag_events{{consumer="{consumer}"}} {lag}')

        # active_sse_connections
        lines.append("# HELP active_sse_connections Number of active SSE connections")
        lines.append("# TYPE active_sse_connections gauge")
        lines.append(f"active_sse_connections {self._active_sse_connections}")

        # event_publish_latency_seconds (histogram)
        lines.append("# HELP event_publish_latency_seconds Event publish latency in seconds")
        lines.append("# TYPE event_publish_latency_seconds histogram")
        for event_type, buckets in self._publish_latency_buckets.items():
            for bucket in buckets:
                le_str = "+Inf" if bucket.le == float("inf") else str(bucket.le)
                lines.append(
                    f'event_publish_latency_seconds_bucket{{event_type="{event_type}",le="{le_str}"}} {bucket.count}'
                )
            lines.append(
                f'event_publish_latency_seconds_sum{{event_type="{event_type}"}} {self._publish_latency_sum[event_type]}'
            )
            lines.append(
                f'event_publish_latency_seconds_count{{event_type="{event_type}"}} {self._publish_latency_count[event_type]}'
            )

        return "\n".join(lines)

    def get_summary(self) -> dict[str, Any]:
        """Get metrics summary as dict.

        Returns:
            Summary dict with key metrics
        """
        total_published = sum(self._events_published.values())
        total_persisted = sum(self._events_persisted.values())
        total_failed = sum(self._events_failed.values())

        uptime_seconds = (datetime.now(UTC) - self._started_at).total_seconds()

        return {
            "total_events_published": total_published,
            "total_events_persisted": total_persisted,
            "total_events_failed": total_failed,
            "events_by_type": dict(self._events_published),
            "projections": {
                "events_processed": dict(self._projection_events),
                "lag_seconds": dict(self._projection_lag),
            },
            "consumers": {
                "lag_events": dict(self._consumer_lag),
            },
            "active_sse_connections": self._active_sse_connections,
            "uptime_seconds": round(uptime_seconds, 2),
        }

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        self._events_published.clear()
        self._events_persisted.clear()
        self._events_failed.clear()
        self._projection_events.clear()
        self._projection_lag.clear()
        self._consumer_lag.clear()
        self._active_sse_connections = 0
        self._publish_latency_buckets.clear()
        self._publish_latency_sum.clear()
        self._publish_latency_count.clear()
        self._started_at = datetime.now(UTC)


# ============================================================================
# SINGLETON
# ============================================================================

_metrics: EventMetrics | None = None


def get_metrics() -> EventMetrics:
    """Get global event metrics singleton.

    Returns:
        EventMetrics instance
    """
    global _metrics
    if _metrics is None:
        _metrics = EventMetrics()
    return _metrics


def reset_metrics() -> None:
    """Reset the global metrics (for testing)."""
    global _metrics
    if _metrics is not None:
        _metrics.reset()
