from __future__ import annotations

"""
Free Intelligence - KPIs Middleware

FastAPI middleware for recording HTTP and LLM metrics.

File: backend/kpis_middleware.py
Created: 2025-10-30
Updated: 2026-02-01 (Phase 2.3 Neptuno - DI migration)
Card: FI-API-FEAT-011
"""

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.kpi.interfaces.ikpis_aggregator import IKPIsAggregator

from backend.utils.common.logging.logger import get_logger
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = get_logger(__name__)


def _get_kpis_aggregator() -> "IKPIsAggregator":
    """Lazy factory for KPIs aggregator (Phase 2.3 Neptuno).

    Middleware cannot use FastAPI Depends(), so uses lazy import.
    Returns singleton from dependencies module for metric continuity.
    """
    from backend.api.routers.kpi.dependencies import get_kpis_aggregator_dep

    return get_kpis_aggregator_dep()


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

        # Detect cache hits from response headers
        cache_hit = response.headers.get("X-Cache-Status") == "HIT" or \
                    response.headers.get("X-FastAPI-Cache") == "Hit" or \
                    response.headers.get("Cache-Control", "").startswith("max-age") and duration_ms < 10

        # Record metrics (Phase 2.3 Neptuno - uses lazy factory)
        aggregator = _get_kpis_aggregator()
        aggregator.record_http_event(
            route=route,
            status=response.status_code,
            duration_ms=duration_ms,
            cache_hit=cache_hit,
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
