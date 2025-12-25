"""Events API - Public endpoints for event streaming and metrics.

Endpoints:
    GET  /events/stream/{aggregate_id}  - Load event stream
    GET  /events/stats                  - Get event store statistics
    GET  /events/metrics                - Get event bus metrics

Note: Events are published internally via EventBus, not via API.
      These endpoints are for debugging/monitoring only.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_events.application.event_bus import get_event_bus
from backend.src.fi_events.domain.events import EventType

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["Events"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class EventResponse(BaseModel):
    """Single event in response."""

    event_id: str
    event_type: str
    aggregate_id: str
    timestamp: str
    payload: dict


class EventStreamResponse(BaseModel):
    """Response for event stream query."""

    aggregate_id: str
    events: list[EventResponse]
    event_count: int


class EventStoreStatsResponse(BaseModel):
    """Response for store statistics."""

    path: str | None = None
    aggregate_count: int = 0
    total_events: int = 0
    file_size_mb: float = 0.0
    created_at: str | None = None
    error: str | None = None


class EventBusMetricsResponse(BaseModel):
    """Response for event bus metrics."""

    events_published: int
    avg_latency_ms: float
    handlers_count: int
    global_handlers_count: int


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get(
    "/stream/{aggregate_id}",
    response_model=EventStreamResponse,
    summary="Load event stream for aggregate",
    description="Returns all events for a given aggregate (e.g., session_id) in chronological order.",
)
async def get_event_stream(
    aggregate_id: str,
    from_version: int = Query(0, ge=0, description="Start from this version"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
) -> EventStreamResponse:
    """Load event stream for an aggregate.

    Args:
        aggregate_id: The aggregate ID (e.g., session_id)
        from_version: Start from this version (0 = all)
        limit: Maximum number of events to return

    Returns:
        EventStreamResponse with events in chronological order
    """
    try:
        event_bus = get_event_bus()

        # Check if store is configured
        if event_bus._store is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Event store not configured",
            )

        events = await event_bus._store.load_stream(aggregate_id, from_version)

        # Apply limit
        events = events[:limit]

        return EventStreamResponse(
            aggregate_id=aggregate_id,
            events=[
                EventResponse(
                    event_id=e.event_id,
                    event_type=e.event_type.value,
                    aggregate_id=e.aggregate_id,
                    timestamp=e.timestamp.isoformat(),
                    payload=e.payload,
                )
                for e in events
            ],
            event_count=len(events),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("EVENT_STREAM_ENDPOINT_FAILED", aggregate_id=aggregate_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load event stream: {e}",
        )


@router.get(
    "/stats",
    response_model=EventStoreStatsResponse,
    summary="Get event store statistics",
    description="Returns statistics about the event store (file size, event count, etc.)",
)
async def get_event_stats() -> EventStoreStatsResponse:
    """Get event store statistics.

    Returns:
        EventStoreStatsResponse with store metrics
    """
    try:
        event_bus = get_event_bus()

        if event_bus._store is None:
            return EventStoreStatsResponse(error="Event store not configured")

        # Check if store has get_stats method
        if hasattr(event_bus._store, "get_stats"):
            stats = event_bus._store.get_stats()
            return EventStoreStatsResponse(**stats)

        # Fallback for stores without get_stats
        count = await event_bus._store.count_events()
        return EventStoreStatsResponse(total_events=count)

    except Exception as e:
        logger.error("EVENT_STATS_ENDPOINT_FAILED", error=str(e))
        return EventStoreStatsResponse(error=str(e))


@router.get(
    "/metrics",
    response_model=EventBusMetricsResponse,
    summary="Get event bus metrics",
    description="Returns runtime metrics for the event bus (events published, latency, handlers)",
)
async def get_event_metrics() -> EventBusMetricsResponse:
    """Get event bus runtime metrics.

    Returns:
        EventBusMetricsResponse with bus metrics
    """
    event_bus = get_event_bus()
    metrics = event_bus.get_metrics()
    return EventBusMetricsResponse(**metrics)


@router.get(
    "/types",
    response_model=list[str],
    summary="List available event types",
    description="Returns all available event types in the system",
)
async def list_event_types() -> list[str]:
    """List all available event types.

    Returns:
        List of event type names
    """
    return [e.value for e in EventType]
