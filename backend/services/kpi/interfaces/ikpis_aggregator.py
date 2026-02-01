"""Interface for KPIsAggregator - enables dependency injection.

This interface defines the contract for KPI metrics aggregation.
Routers and middleware depend on this interface for testability.

Pattern: Dependency Inversion Principle (DIP)
Card: Backend Refactor Phase 2.3 Neptuno - Eliminate Service Locator
Created: 2026-02-01
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IKPIsAggregator(ABC):
    """Abstract interface for KPI metrics aggregation.

    This interface exposes the methods needed by:
    - kpis_middleware.py: record_http_event, record_llm_event
    - kpis.py router: get_summary, get_chips, get_timeseries
    """

    @abstractmethod
    def record_http_event(
        self,
        route: str,
        status: int,
        duration_ms: int,
        cache_hit: bool = False,
    ) -> None:
        """Record HTTP request event.

        Args:
            route: Route template (e.g., /api/sessions)
            status: HTTP status code
            duration_ms: Request duration in ms
            cache_hit: Whether this was a cache hit
        """
        pass

    @abstractmethod
    def record_llm_event(
        self,
        provider: str,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        latency_ms: int = 0,
        cache_hit: bool = False,
    ) -> None:
        """Record LLM request event.

        Args:
            provider: Provider name (anthropic, openai, local)
            tokens_in: Input tokens (None if unknown)
            tokens_out: Output tokens (None if unknown)
            latency_ms: Request latency in ms
            cache_hit: Whether this was a cache hit
        """
        pass

    @abstractmethod
    def get_summary(
        self,
        window: str = "5m",
        route_filter: str | None = None,
        provider_filter: str | None = None,
    ) -> dict[str, Any]:
        """Get summary metrics for time window.

        Args:
            window: Time window (1m, 5m, 15m, 1h, 24h)
            route_filter: Filter by route (None = all)
            provider_filter: Filter by provider (None = all)

        Returns:
            Summary dict with requests, latency, tokens, cache, providers
        """
        pass

    @abstractmethod
    def get_chips(self, window: str = "5m") -> dict[str, Any]:
        """Get metrics formatted as chips for UI.

        Args:
            window: Time window (1m, 5m, 15m, 1h, 24h)

        Returns:
            Chips dict ready for UI consumption
        """
        pass

    @abstractmethod
    def get_timeseries(
        self,
        window: str = "15m",
        bucket_sec: int | None = None,
    ) -> dict[str, Any]:
        """Get timeseries data for sparklines.

        Args:
            window: Time window (1m, 5m, 15m, 1h, 24h)
            bucket_sec: Bucket granularity override (None = use default)

        Returns:
            Timeseries dict with series arrays
        """
        pass
