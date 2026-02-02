"""Metrics and monitoring for FI Coder.

Provides comprehensive metrics collection, health monitoring, and performance tracking.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """Individual metric measurement."""

    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Advanced metrics collection system."""

    def __init__(
        self, retention_period: int = 3600, max_points_per_metric: int = 1000
    ):  # Reduced from 10000
        self.retention_period = retention_period
        self.max_points_per_metric = max_points_per_metric
        self._metrics: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.max_points_per_metric)
        )
        self._gauges: dict[str, float] = {}
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.max_points_per_metric // 10)
        )  # Smaller for histograms
        self._lock = threading.RLock()

        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    def record_metric(self, name: str, value: float, tags: dict[str, str] | None = None):
        """Record a metric point."""
        point = MetricPoint(name=name, value=value, tags=tags or {})
        with self._lock:
            self._metrics[name].append(point)

    def set_gauge(self, name: str, value: float, tags: dict[str, str] | None = None):
        """Set a gauge metric."""
        with self._lock:
            self._gauges[name] = value
            self.record_metric(f"gauge_{name}", value, tags)

    def increment_counter(self, name: str, value: float = 1.0, tags: dict[str, str] | None = None):
        """Increment a counter."""
        with self._lock:
            self._counters[name] += value
            self.record_metric(f"counter_{name}", self._counters[name], tags)

    def record_histogram(self, name: str, value: float, tags: dict[str, str] | None = None):
        """Record a histogram value."""
        with self._lock:
            self._histograms[name].append(value)
            self.record_metric(f"histogram_{name}", value, tags)

    def get_metric_stats(self, name: str, time_window: int | None = None) -> dict[str, Any]:
        """Get statistics for a metric."""
        cutoff = time.time() - (time_window or self.retention_period)

        with self._lock:
            points = self._metrics[name]
            if not points:
                return {"count": 0}

            # Find first valid index using binary search for efficiency
            left, right = 0, len(points) - 1
            first_valid = len(points)
            while left <= right:
                mid = (left + right) // 2
                if points[mid].timestamp >= cutoff:
                    first_valid = mid
                    right = mid - 1
                else:
                    left = mid + 1

            if first_valid >= len(points):
                return {"count": 0}

            # Use slice for efficient access - convert deque slice to list
            valid_points = list(points)[first_valid:]
            if not valid_points:
                return {"count": 0}

            values = [p.value for p in valid_points]
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "latest": values[-1],
                "time_window_seconds": time_window or self.retention_period,
            }

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all current metrics."""
        with self._lock:
            return {
                "gauges": dict(self._gauges),
                "counters": dict(self._counters),
                "histograms": {name: list(values) for name, values in self._histograms.items()},
                "series_count": {name: len(points) for name, points in self._metrics.items()},
            }

    def _cleanup_loop(self):
        """Background cleanup of old metrics."""
        while True:
            try:
                cutoff = time.time() - self.retention_period
                with self._lock:
                    # Only cleanup metrics that have data
                    metrics_to_cleanup = [name for name, points in self._metrics.items() if points]
                    for name in metrics_to_cleanup:
                        points = self._metrics[name]
                        # Remove old points from the left (deque is efficient for this)
                        while points and points[0].timestamp < cutoff:
                            points.popleft()
                        # If deque is empty after cleanup, remove it entirely
                        if not points:
                            del self._metrics[name]
            except Exception as e:
                logger.error("metrics_cleanup_error", error=str(e))

            time.sleep(300)  # Clean every 5 minutes


# Global instance
metrics_collector = MetricsCollector()

__all__ = [
    "MetricPoint",
    "MetricsCollector",
    "metrics_collector",
]
