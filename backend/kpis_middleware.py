"""
Free Intelligence - KPIs Middleware

FastAPI middleware for recording HTTP and LLM metrics.

File: backend/kpis_middleware.py
Created: 2025-10-30
Card: FI-API-FEAT-011
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.kpis_aggregator import get_kpis_aggregator
from backend.logger import get_logger

logger = get_logger(__name__)


class KPIsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to record HTTP request metrics.

    Records:
    - Route template (e.g., /api/sessions)
    - HTTP status code
    - Request duration in ms
    - Cache hit status (if applicable)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Intercept request and record metrics.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        start_time = time.time()

        # Get route template (e.g., /api/sessions/{id})
        route = request.url.path
        if hasattr(request, "scope") and "route" in request.scope:
            route_obj = request.scope.get("route")
            if route_obj and hasattr(route_obj, "path"):
                route = route_obj.path

        # Call next handler
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Record metrics
        aggregator = get_kpis_aggregator()
        aggregator.record_http_event(
            route=route,
            status=response.status_code,
            duration_ms=duration_ms,
            cache_hit=False,  # TODO: Detect cache hits from response headers
        )

        # Log slow requests (>1s)
        if duration_ms > 1000:
            logger.warning(
                "HTTP_REQUEST_SLOW",
                route=route,
                status=response.status_code,
                duration_ms=duration_ms,
            )

        return response
