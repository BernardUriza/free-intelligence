"""Distributed Tracing - Request correlation across services.

Philosophy:
  - Distributed systems = hard to debug without tracing
  - Trace ID = unique identifier for entire request flow
  - Span ID = unique identifier for each operation
  - Context propagation = pass trace info through all calls

Architecture:
  - PUBLIC endpoint receives request → generates trace_id
  - INTERNAL calls inherit trace_id + create new span_id
  - WORKER operations create child spans
  - LLM provider calls propagate trace_id
  - Logs include trace_id for correlation

Headers:
  - X-Trace-Id: Unique trace identifier (UUID)
  - X-Span-Id: Current operation span (UUID)
  - X-Parent-Span-Id: Parent operation span (UUID)
  - X-Session-Id: Business session identifier

Created: 2025-12-03
Pattern: Distributed Tracing (OpenTelemetry-style)
"""

from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from backend.logger import get_logger

logger = get_logger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONTEXT VARIABLES (thread-safe request context)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Context variables for tracing (thread-safe, async-safe)
_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id", default=None
)
_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("span_id", default=None)
_parent_span_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "parent_span_id", default=None
)
_session_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "session_id", default=None
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRACE CONTEXT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class TraceContext:
    """Current trace context"""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    session_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        """Convert to dict for logging"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id or "",
            "session_id": self.session_id or "",
        }

    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers for propagation"""
        headers = {
            "X-Trace-Id": self.trace_id,
            "X-Span-Id": self.span_id,
        }
        if self.parent_span_id:
            headers["X-Parent-Span-Id"] = self.parent_span_id
        if self.session_id:
            headers["X-Session-Id"] = self.session_id
        return headers


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONTEXT MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_trace_id() -> str | None:
    """Get current trace ID from context"""
    return _trace_id.get()


def get_span_id() -> str | None:
    """Get current span ID from context"""
    return _span_id.get()


def get_parent_span_id() -> str | None:
    """Get current parent span ID from context"""
    return _parent_span_id.get()


def get_session_id() -> str | None:
    """Get current session ID from context"""
    return _session_id.get()


def set_trace_context(
    trace_id: str,
    span_id: str,
    parent_span_id: str | None = None,
    session_id: str | None = None,
) -> TraceContext:
    """
    Set trace context for current request.

    Args:
        trace_id: Trace identifier
        span_id: Span identifier
        parent_span_id: Parent span identifier
        session_id: Session identifier

    Returns:
        TraceContext
    """
    _trace_id.set(trace_id)
    _span_id.set(span_id)
    _parent_span_id.set(parent_span_id)
    _session_id.set(session_id)

    return TraceContext(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        session_id=session_id,
    )


def get_trace_context() -> TraceContext | None:
    """Get current trace context"""
    trace_id = get_trace_id()
    span_id = get_span_id()

    if not trace_id or not span_id:
        return None

    return TraceContext(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=get_parent_span_id(),
        session_id=get_session_id(),
    )


def clear_trace_context() -> None:
    """Clear trace context (for cleanup)"""
    _trace_id.set(None)
    _span_id.set(None)
    _parent_span_id.set(None)
    _session_id.set(None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SPAN CREATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def create_child_span(operation_name: str) -> TraceContext:
    """
    Create child span for nested operation.

    Preserves trace_id, sets current span_id as parent, generates new span_id.

    Usage:
        # In worker function
        context = create_child_span("diarization_worker")
        logger.info("DIARIZATION_START", **context.to_dict())

    Args:
        operation_name: Name of operation (for logging)

    Returns:
        TraceContext with new span
    """
    current_trace_id = get_trace_id()
    current_span_id = get_span_id()
    current_session_id = get_session_id()

    if not current_trace_id:
        # No parent trace - create new root trace
        logger.warning(
            "CREATE_CHILD_SPAN_NO_PARENT",
            operation=operation_name,
            hint="Creating root trace instead",
        )
        return create_root_span(operation_name)

    # Create child span
    new_span_id = generate_span_id()

    context = set_trace_context(
        trace_id=current_trace_id,
        span_id=new_span_id,
        parent_span_id=current_span_id,
        session_id=current_session_id,
    )

    logger.debug(
        "CHILD_SPAN_CREATED",
        operation=operation_name,
        trace_id=current_trace_id,
        span_id=new_span_id,
        parent_span_id=current_span_id,
    )

    return context


def create_root_span(operation_name: str, session_id: str | None = None) -> TraceContext:
    """
    Create root span (new trace).

    Usage:
        # When starting new workflow
        context = create_root_span("workflow_start", session_id="session-123")

    Args:
        operation_name: Name of operation
        session_id: Optional session identifier

    Returns:
        TraceContext with new trace
    """
    trace_id = generate_trace_id()
    span_id = generate_span_id()

    context = set_trace_context(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=None,
        session_id=session_id,
    )

    logger.debug(
        "ROOT_SPAN_CREATED",
        operation=operation_name,
        trace_id=trace_id,
        span_id=span_id,
        session_id=session_id,
    )

    return context


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ID GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def generate_trace_id() -> str:
    """Generate unique trace ID"""
    return str(uuid.uuid4())


def generate_span_id() -> str:
    """Generate unique span ID"""
    return str(uuid.uuid4())


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRACING MIDDLEWARE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TracingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for distributed tracing.

    Extracts trace context from headers or creates new trace.
    Injects trace context into response headers.
    Adds trace_id to all logs during request.

    Usage:
        app.add_middleware(TracingMiddleware)

    Headers (request):
        X-Trace-Id: Incoming trace ID (optional)
        X-Span-Id: Incoming span ID (optional)
        X-Parent-Span-Id: Parent span ID (optional)

    Headers (response):
        X-Trace-Id: Trace ID for this request
        X-Span-Id: Span ID for this request
    """

    async def dispatch(self, request: Request, call_next):
        """Process request with tracing"""

        # Extract or create trace context
        trace_id = request.headers.get("X-Trace-Id") or generate_trace_id()
        span_id = generate_span_id()  # Always new span for this request
        parent_span_id = request.headers.get("X-Span-Id")  # Incoming span becomes parent
        session_id = request.headers.get("X-Session-Id")

        # Set context
        context = set_trace_context(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            session_id=session_id,
        )

        # Log request start
        logger.info(
            "REQUEST_START",
            method=request.method,
            path=request.url.path,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            session_id=session_id,
        )

        # Process request
        try:
            response = await call_next(request)

            # Inject trace headers into response
            response.headers["X-Trace-Id"] = trace_id
            response.headers["X-Span-Id"] = span_id
            if session_id:
                response.headers["X-Session-Id"] = session_id

            # Log request completion
            logger.info(
                "REQUEST_COMPLETE",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                trace_id=trace_id,
                span_id=span_id,
            )

            return response

        except Exception as e:
            logger.error(
                "REQUEST_FAILED",
                method=request.method,
                path=request.url.path,
                error=str(e),
                trace_id=trace_id,
                span_id=span_id,
                exc_info=True,
            )
            raise

        finally:
            # Clean up context
            clear_trace_context()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOGGING INTEGRATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_trace_context_for_logging() -> dict[str, Any]:
    """
    Get trace context as dict for structured logging.

    Usage:
        logger.info("OPERATION_START", **get_trace_context_for_logging())

    Returns:
        Dict with trace_id, span_id, parent_span_id, session_id
    """
    context = get_trace_context()
    if not context:
        return {}

    return context.to_dict()
