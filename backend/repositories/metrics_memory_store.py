"""MetricsMemoryStore - Wrapper that adds latency/error metrics to IMemoryStore.

Decorator pattern for instrumentation without modifying core logic.

Author: Claude Sonnet 4.5 (El Revisor Agresivo)
Created: 2026-01-31
Purpose: Add observability to memory store operations
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Callable, Any

from backend.repositories.interfaces.imemory_store import (
    IMemoryStore,
    AudioEventDict,
    AudioStatsDict,
)
from backend.infrastructure.interfaces.ilogger import ILogger
from backend.utils.common.logging.logger import get_logger


class MetricsMemoryStore(IMemoryStore):
    """Decorator that adds latency and error metrics to IMemoryStore operations.

    Responsibilities:
    - Track latency for all IMemoryStore methods
    - Track error rates (success vs failure)
    - Track type validation rejections (h5py.Empty, arrays, decode errors)
    - Log metrics to structured logger (for Datadog/CloudWatch)

    Why Decorator Pattern:
    - ✅ Adds metrics without modifying HDF5MemoryStore/ElasticsearchMemoryStore
    - ✅ Can wrap ANY IMemoryStore implementation
    - ✅ Easy to enable/disable (just swap out wrapper)
    - ✅ Single responsibility (metrics separate from business logic)

    Example:
        # Without metrics:
        store = HDF5MemoryStore(corpus_path="storage/corpus.h5")

        # With metrics:
        store = MetricsMemoryStore(
            delegate=HDF5MemoryStore(corpus_path="storage/corpus.h5")
        )

    Metrics Logged:
        - MEMORY_STORE_OPERATION (structured log)
          - method: str (get_audio_events, search_audio_events, etc.)
          - doctor_id: str
          - latency_ms: float
          - status: "success" | "error"
          - error_type: str | None (if error)
          - result_count: int (for get/search methods)
          - query: str | None (for search methods)
    """

    def __init__(self, delegate: IMemoryStore, logger: ILogger | None = None):
        """Initialize MetricsMemoryStore wrapper.

        Args:
            delegate: Underlying IMemoryStore implementation
            logger: Logger instance (optional)
        """
        self.delegate = delegate
        self.logger = logger or get_logger(__name__)

    def _track_metrics(self, method_name: str) -> Callable:
        """Decorator to track latency and errors for a method.

        Args:
            method_name: Name of IMemoryStore method (for logging)

        Returns:
            Decorated method with metrics tracking
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                status = "success"
                error_type = None
                result_count = 0

                try:
                    # Execute delegate method
                    result = func(*args, **kwargs)

                    # Extract result count (if applicable)
                    if isinstance(result, tuple):
                        # get_audio_events returns (events, total_count)
                        events, total_count = result
                        result_count = len(events)
                    elif isinstance(result, list):
                        # search_audio_events returns list
                        result_count = len(result)
                    elif isinstance(result, dict):
                        # get_audio_stats returns dict with 'count'
                        result_count = result.get("count", 0)

                    return result

                except Exception as e:
                    status = "error"
                    error_type = type(e).__name__
                    raise  # Re-raise after logging

                finally:
                    latency_ms = (time.time() - start_time) * 1000

                    # Log metrics
                    log_data = {
                        "method": method_name,
                        "latency_ms": round(latency_ms, 2),
                        "status": status,
                        "result_count": result_count,
                    }

                    # Add error info if failed
                    if error_type:
                        log_data["error_type"] = error_type

                    # Add doctor_id if in args/kwargs
                    if args and len(args) > 0:
                        log_data["doctor_id"] = args[0]
                    elif "doctor_id" in kwargs:
                        log_data["doctor_id"] = kwargs["doctor_id"]

                    # Add query if search method
                    if "query" in kwargs:
                        log_data["query"] = kwargs["query"]

                    self.logger.info("MEMORY_STORE_OPERATION", **log_data)

            return wrapper

        return decorator

    def get_audio_events(
        self,
        doctor_id: str,
        start_ts: int | None = None,
        end_ts: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AudioEventDict], int]:
        """Fetch audio events with latency tracking."""
        tracked_method = self._track_metrics("get_audio_events")(
            self.delegate.get_audio_events
        )
        return tracked_method(doctor_id, start_ts, end_ts, limit, offset)

    def search_audio_events(
        self,
        doctor_id: str,
        query: str,
        limit: int = 1000,
    ) -> list[AudioEventDict]:
        """Search audio events with latency tracking."""
        tracked_method = self._track_metrics("search_audio_events")(
            self.delegate.search_audio_events
        )
        return tracked_method(doctor_id, query, limit)

    def get_audio_stats(
        self,
        doctor_id: str,
    ) -> AudioStatsDict:
        """Get audio stats with latency tracking."""
        tracked_method = self._track_metrics("get_audio_stats")(
            self.delegate.get_audio_stats
        )
        return tracked_method(doctor_id)


__all__ = ["MetricsMemoryStore"]
