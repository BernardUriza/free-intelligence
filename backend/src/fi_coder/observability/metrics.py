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


@dataclass
class HealthStatus:
    """System health status."""
    component: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str = ""
    last_check: float = field(default_factory=time.time)
    metrics: dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Advanced metrics collection system."""

    def __init__(self, retention_period: int = 3600, max_points_per_metric: int = 1000):  # Reduced from 10000
        self.retention_period = retention_period
        self.max_points_per_metric = max_points_per_metric
        self._metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_points_per_metric))
        self._gauges: dict[str, float] = {}
        self._counters: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, deque] = defaultdict(lambda: deque(maxlen=self.max_points_per_metric // 10))  # Smaller for histograms
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


class HealthMonitor:
    """System health monitoring."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._health_checks: dict[str, callable] = {}
        self._health_status: dict[str, HealthStatus] = {}
        self._lock = threading.RLock()

    def register_health_check(self, name: str, check_func: callable):
        """Register a health check function."""
        with self._lock:
            self._health_checks[name] = check_func

    def run_health_checks(self) -> dict[str, HealthStatus]:
        """Run all registered health checks."""
        results = {}

        with self._lock:
            for name, check_func in self._health_checks.items():
                try:
                    status = check_func()
                    if isinstance(status, dict):
                        health_status = HealthStatus(
                            component=name,
                            status=status.get("status", "unknown"),
                            message=status.get("message", ""),
                            metrics=status.get("metrics", {}),
                        )
                    else:
                        health_status = HealthStatus(
                            component=name,
                            status="healthy" if status else "unhealthy",
                        )
                    results[name] = health_status
                    self._health_status[name] = health_status

                except Exception as e:
                    logger.error("health_check_error", component=name, error=str(e))
                    results[name] = HealthStatus(
                        component=name,
                        status="error",
                        message=str(e),
                    )

        return results

    def get_overall_health(self) -> str:
        """Get overall system health status."""
        statuses = list(self._health_status.values())
        if not statuses:
            return "unknown"

        if any(s.status == "unhealthy" for s in statuses):
            return "unhealthy"
        elif any(s.status == "degraded" for s in statuses):
            return "degraded"
        elif all(s.status == "healthy" for s in statuses):
            return "healthy"
        else:
            return "unknown"

    def get_health_report(self) -> dict[str, Any]:
        """Get comprehensive health report."""
        health_checks = self.run_health_checks()
        return {
            "overall_status": self.get_overall_health(),
            "components": {name: {
                "status": status.status,
                "message": status.message,
                "last_check": status.last_check,
                "metrics": status.metrics,
            } for name, status in health_checks.items()},
            "timestamp": time.time(),
        }


class PerformanceMonitor:
    """Performance monitoring and alerting."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._alerts: list[dict[str, Any]] = []
        self._alert_lock = threading.RLock()

    def check_performance_thresholds(self) -> list[dict[str, Any]]:
        """Check performance against thresholds and generate alerts."""
        alerts = []

        # Check task execution times
        exec_stats = self.metrics.get_metric_stats("task_execution_time")
        if exec_stats.get("count", 0) > 0:
            avg_time = exec_stats["avg"]
            if avg_time > 300:  # 5 minutes
                alerts.append({
                    "level": "warning",
                    "message": f"Average task execution time is high: {avg_time:.2f}s",
                    "metric": "task_execution_time",
                    "threshold": 300,
                    "current": avg_time,
                })

        # Check queue depth
        queue_stats = self.metrics.get_metric_stats("queue_depth")
        if queue_stats.get("count", 0) > 0:
            max_depth = queue_stats["max"]
            if max_depth > 50:  # Queue too deep
                alerts.append({
                    "level": "warning",
                    "message": f"Task queue is too deep: {max_depth} tasks",
                    "metric": "queue_depth",
                    "threshold": 50,
                    "current": max_depth,
                })

        # Check error rates
        error_stats = self.metrics.get_metric_stats("task_errors")
        success_stats = self.metrics.get_metric_stats("task_success")
        total_errors = error_stats.get("count", 0)
        total_success = success_stats.get("count", 0)
        total_tasks = total_errors + total_success

        if total_tasks > 10:  # Need minimum sample size
            error_rate = total_errors / total_tasks
            if error_rate > 0.1:  # 10% error rate
                alerts.append({
                    "level": "error",
                    "message": f"Task error rate is high: {error_rate:.2%}",
                    "metric": "error_rate",
                    "threshold": 0.1,
                    "current": error_rate,
                })

        with self._alert_lock:
            self._alerts.extend(alerts)

        return alerts

    def get_active_alerts(self) -> list[dict[str, Any]]:
        """Get currently active alerts."""
        with self._alert_lock:
            return self._alerts.copy()

    def clear_alerts(self, alert_ids: list[str] | None = None):
        """Clear alerts."""
        with self._alert_lock:
            if alert_ids:
                self._alerts = [a for a in self._alerts if a.get("id") not in alert_ids]
            else:
                self._alerts.clear()


# Global instances
metrics_collector = MetricsCollector()
health_monitor = HealthMonitor(metrics_collector)
performance_monitor = PerformanceMonitor(metrics_collector)

__all__ = [
    "HealthMonitor",
    "HealthStatus",
    "MetricPoint",
    "MetricsCollector",
    "PerformanceMonitor",
    "health_monitor",
    "metrics_collector",
    "performance_monitor",
]
