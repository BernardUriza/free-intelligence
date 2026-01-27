"""Observability module - Metrics, tracing, and monitoring for Event Sourcing.

Provides:
- Prometheus-compatible metrics
- Distributed tracing spans
- Event bus instrumentation
- Projection lag monitoring

Usage:
    from infrastructure.events.observability import get_metrics, EventMetrics

    metrics = get_metrics()
    metrics.record_event_published("TRANSCRIPTION_STARTED", 0.5)
"""

from infrastructure.events.observability.metrics import (
    EventMetrics,
    get_metrics,
    reset_metrics,
)
from infrastructure.events.observability.tracing import (
    EventTracer,
    get_tracer,
    trace_event,
)

__all__ = [
    "EventMetrics",
    "get_metrics",
    "reset_metrics",
    "EventTracer",
    "get_tracer",
    "trace_event",
]
