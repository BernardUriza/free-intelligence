"""Event Tracing - Distributed tracing for Event Sourcing.

Provides lightweight tracing spans for:
- Event publishing
- Event persistence
- Projection processing
- Replay operations

Designed to be compatible with OpenTelemetry but standalone.

Usage:
    from backend.src.fi_events.observability.tracing import trace_event, get_tracer

    tracer = get_tracer()
    with tracer.span("publish_event", {"event_type": "TRANSCRIPTION_STARTED"}):
        await event_bus.publish(event)

    # Or use decorator
    @trace_event("process_chunk")
    async def process_chunk(chunk):
        ...
"""

from __future__ import annotations

import asyncio
import functools
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Generator
from uuid import uuid4

from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)

# Maximum spans to keep in memory
MAX_SPANS_IN_MEMORY = 1000


@dataclass
class Span:
    """A tracing span representing a unit of work."""

    span_id: str
    trace_id: str
    parent_id: str | None
    operation_name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float | None = None
    status: str = "ok"  # ok, error
    tags: dict[str, str] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def finish(self, status: str = "ok") -> None:
        """Finish the span.

        Args:
            status: Final status (ok or error)
        """
        self.end_time = datetime.now(UTC)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the span.

        Args:
            name: Event name
            attributes: Event attributes
        """
        self.events.append(
            {
                "name": name,
                "timestamp": datetime.now(UTC).isoformat(),
                "attributes": attributes or {},
            }
        )

    def set_tag(self, key: str, value: str) -> None:
        """Set a tag on the span.

        Args:
            key: Tag key
            value: Tag value
        """
        self.tags[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Convert span to dict.

        Returns:
            Span as dict
        """
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "events": self.events,
        }


class EventTracer:
    """Lightweight distributed tracer for Event Sourcing.

    Stores spans in memory with a circular buffer.
    Can export spans for analysis.
    """

    def __init__(self, service_name: str = "fi_events") -> None:
        """Initialize tracer.

        Args:
            service_name: Name of the service
        """
        self._service_name = service_name
        self._spans: list[Span] = []
        self._current_trace_id: str | None = None
        self._current_span_id: str | None = None

        logger.info("EVENT_TRACER_INITIALIZED", service_name=service_name)

    def _generate_id(self) -> str:
        """Generate a trace/span ID."""
        return uuid4().hex[:16]

    @contextmanager
    def span(
        self,
        operation_name: str,
        tags: dict[str, str] | None = None,
        parent_id: str | None = None,
    ) -> Generator[Span]:
        """Create a tracing span context.

        Args:
            operation_name: Name of the operation
            tags: Optional tags
            parent_id: Optional parent span ID

        Yields:
            The active span
        """
        # Generate IDs
        trace_id = self._current_trace_id or self._generate_id()
        span_id = self._generate_id()
        parent = parent_id or self._current_span_id

        # Create span
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_id=parent,
            operation_name=operation_name,
            start_time=datetime.now(UTC),
            tags={"service": self._service_name, **(tags or {})},
        )

        # Set as current
        previous_trace_id = self._current_trace_id
        previous_span_id = self._current_span_id
        self._current_trace_id = trace_id
        self._current_span_id = span_id

        try:
            yield span
            span.finish("ok")
        except Exception as e:
            span.finish("error")
            span.set_tag("error.message", str(e))
            span.set_tag("error.type", type(e).__name__)
            raise
        finally:
            # Restore previous context
            self._current_trace_id = previous_trace_id
            self._current_span_id = previous_span_id

            # Store span
            self._store_span(span)

            # Log span
            logger.debug(
                "SPAN_FINISHED",
                operation=operation_name,
                trace_id=trace_id,
                span_id=span_id,
                duration_ms=span.duration_ms,
                status=span.status,
            )

    def _store_span(self, span: Span) -> None:
        """Store span in buffer.

        Args:
            span: Span to store
        """
        self._spans.append(span)

        # Trim if over limit (circular buffer)
        if len(self._spans) > MAX_SPANS_IN_MEMORY:
            self._spans = self._spans[-MAX_SPANS_IN_MEMORY:]

    def get_trace(self, trace_id: str) -> list[Span]:
        """Get all spans for a trace.

        Args:
            trace_id: Trace ID

        Returns:
            List of spans in the trace
        """
        return [s for s in self._spans if s.trace_id == trace_id]

    def get_recent_spans(self, limit: int = 100) -> list[Span]:
        """Get recent spans.

        Args:
            limit: Maximum spans to return

        Returns:
            List of recent spans
        """
        return self._spans[-limit:]

    def get_slow_spans(
        self,
        threshold_ms: float = 100.0,
        limit: int = 50,
    ) -> list[Span]:
        """Get spans slower than threshold.

        Args:
            threshold_ms: Threshold in milliseconds
            limit: Maximum spans to return

        Returns:
            List of slow spans
        """
        slow = [
            s for s in self._spans if s.duration_ms is not None and s.duration_ms > threshold_ms
        ]
        return sorted(slow, key=lambda s: s.duration_ms or 0, reverse=True)[:limit]

    def get_error_spans(self, limit: int = 50) -> list[Span]:
        """Get spans with errors.

        Args:
            limit: Maximum spans to return

        Returns:
            List of error spans
        """
        errors = [s for s in self._spans if s.status == "error"]
        return errors[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get tracer statistics.

        Returns:
            Stats dict
        """
        if not self._spans:
            return {
                "total_spans": 0,
                "avg_duration_ms": 0,
                "error_rate": 0,
            }

        durations = [s.duration_ms for s in self._spans if s.duration_ms is not None]
        errors = sum(1 for s in self._spans if s.status == "error")

        return {
            "total_spans": len(self._spans),
            "avg_duration_ms": round(sum(durations) / len(durations), 2) if durations else 0,
            "max_duration_ms": round(max(durations), 2) if durations else 0,
            "min_duration_ms": round(min(durations), 2) if durations else 0,
            "error_count": errors,
            "error_rate": round(errors / len(self._spans) * 100, 2) if self._spans else 0,
            "operations": self._get_operation_stats(),
        }

    def _get_operation_stats(self) -> dict[str, dict[str, Any]]:
        """Get stats per operation.

        Returns:
            Dict of operation -> stats
        """
        ops: dict[str, list[float]] = {}
        for span in self._spans:
            if span.duration_ms is not None:
                if span.operation_name not in ops:
                    ops[span.operation_name] = []
                ops[span.operation_name].append(span.duration_ms)

        return {
            op: {
                "count": len(durations),
                "avg_ms": round(sum(durations) / len(durations), 2),
                "max_ms": round(max(durations), 2),
            }
            for op, durations in ops.items()
        }

    def clear(self) -> None:
        """Clear all stored spans."""
        self._spans.clear()
        self._current_trace_id = None
        self._current_span_id = None


# ============================================================================
# SINGLETON
# ============================================================================

_tracer: EventTracer | None = None


def get_tracer() -> EventTracer:
    """Get global event tracer singleton.

    Returns:
        EventTracer instance
    """
    global _tracer
    if _tracer is None:
        _tracer = EventTracer()
    return _tracer


# ============================================================================
# DECORATOR
# ============================================================================


def trace_event(
    operation_name: str,
    tags: dict[str, str] | None = None,
) -> Callable:
    """Decorator to trace a function.

    Args:
        operation_name: Name of the operation
        tags: Optional tags

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.span(operation_name, tags):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.span(operation_name, tags):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
