"""Events API - Public endpoints for event streaming, replay, and projections.

Endpoints:
    GET  /events/stream/{aggregate_id}    - Load event stream
    GET  /events/stats                    - Get event store statistics
    GET  /events/metrics                  - Get event bus metrics
    GET  /events/types                    - List event types
    GET  /events/replay/{aggregate_id}    - Replay aggregate state
    GET  /events/projections              - List projections
    GET  /events/projections/{name}       - Get projection state
    GET  /events/sse/{aggregate_id}       - SSE stream with heartbeat
    GET  /events/consumer-lag/{consumer}  - Get consumer lag

Note: Events are published internally via EventBus, not via API.
      These endpoints are for debugging/monitoring and DevTools.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_events.application.event_bus import get_event_bus
from backend.src.fi_events.application.replay import replay_aggregate
from backend.src.fi_events.domain.events import EventType
from backend.src.fi_events.infrastructure.consumer_offsets import get_offset_store
from backend.src.fi_events.projections.registry import get_registry
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

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


# ============================================================================
# REPLAY ENDPOINT
# ============================================================================


class ReplayResponse(BaseModel):
    """Response for replay endpoint."""

    aggregate_id: str
    event_count: int
    first_event_id: str | None = None
    last_event_id: str | None = None
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    final_state: dict = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    replay_duration_ms: float = 0.0


@router.get(
    "/replay/{aggregate_id}",
    response_model=ReplayResponse,
    summary="Replay aggregate state",
    description="Reconstructs aggregate state by replaying all events from the stream.",
)
async def replay_aggregate_endpoint(
    aggregate_id: str,
    from_version: int = Query(0, ge=0, description="Start from this version"),
    reducer: str = Query("default", description="Reducer to use: default, transcription, session"),
) -> ReplayResponse:
    """Replay aggregate to reconstruct state.

    Args:
        aggregate_id: The aggregate ID (e.g., session_id)
        from_version: Start from this version (0 = all)
        reducer: Which reducer to use

    Returns:
        ReplayResponse with final state and metadata
    """
    try:
        event_bus = get_event_bus()

        if event_bus._store is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Event store not configured",
            )

        # Select reducer
        from backend.src.fi_events.application.replay import (
            default_reducer,
            session_reducer,
            transcription_reducer,
        )

        reducer_fn = {
            "default": default_reducer,
            "transcription": transcription_reducer,
            "session": session_reducer,
        }.get(reducer, default_reducer)

        result = await replay_aggregate(
            aggregate_id=aggregate_id,
            event_store=event_bus._store,
            reducer=reducer_fn,
            from_version=from_version,
        )

        return ReplayResponse(
            aggregate_id=result.aggregate_id,
            event_count=result.event_count,
            first_event_id=result.first_event_id,
            last_event_id=result.last_event_id,
            first_timestamp=result.first_timestamp.isoformat() if result.first_timestamp else None,
            last_timestamp=result.last_timestamp.isoformat() if result.last_timestamp else None,
            final_state=result.final_state,
            errors=result.errors,
            replay_duration_ms=result.replay_duration_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("REPLAY_ENDPOINT_FAILED", aggregate_id=aggregate_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Replay failed: {e}",
        )


# ============================================================================
# PROJECTIONS ENDPOINTS
# ============================================================================


class ProjectionInfoResponse(BaseModel):
    """Info about a projection."""

    name: str
    subscribed_events: list[str]
    status: str
    events_processed: int
    last_processed_at: str | None = None
    error_count: int = 0


class ProjectionStateResponse(BaseModel):
    """Projection state response."""

    name: str
    status: str
    events_processed: int
    state: dict = Field(default_factory=dict)


@router.get(
    "/projections",
    response_model=list[ProjectionInfoResponse],
    summary="List all projections",
    description="Returns info about all registered projections.",
)
async def list_projections() -> list[ProjectionInfoResponse]:
    """List all registered projections.

    Returns:
        List of projection info
    """
    registry = get_registry()
    projections = registry.list_projections()

    return [
        ProjectionInfoResponse(
            name=p["name"],
            subscribed_events=p["subscribed_events"],
            status=p["status"],
            events_processed=p["events_processed"],
            last_processed_at=p.get("last_processed_at"),
            error_count=p.get("error_count", 0),
        )
        for p in projections
    ]


@router.get(
    "/projections/{name}",
    response_model=ProjectionStateResponse,
    summary="Get projection state",
    description="Returns current state of a specific projection.",
)
async def get_projection_state(name: str) -> ProjectionStateResponse:
    """Get projection state by name.

    Args:
        name: Projection name

    Returns:
        ProjectionStateResponse with current state
    """
    registry = get_registry()
    projection = registry.get(name)

    if projection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projection '{name}' not found",
        )

    state = await projection.get_state()
    runtime = projection.get_runtime_state()

    return ProjectionStateResponse(
        name=projection.name,
        status=runtime.status.value,
        events_processed=runtime.events_processed,
        state=state,
    )


@router.post(
    "/projections/{name}/rebuild",
    summary="Rebuild projection",
    description="Rebuilds a projection from scratch by replaying all events.",
)
async def rebuild_projection(name: str) -> dict[str, Any]:
    """Rebuild a projection from scratch.

    Args:
        name: Projection name

    Returns:
        Rebuild result with stats
    """
    event_bus = get_event_bus()

    if event_bus._store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event store not configured",
        )

    registry = get_registry()
    result = await registry.rebuild(name, event_bus._store)

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"],
        )

    return result


# ============================================================================
# SSE STREAM WITH HEARTBEAT
# ============================================================================

SSE_HEARTBEAT_INTERVAL = 15  # seconds


async def event_stream_generator(
    aggregate_id: str,
    request: Request,
    from_version: int = 0,
):
    """Generate SSE stream for an aggregate.

    Yields events in SSE format with heartbeat every 15 seconds.
    """
    event_bus = get_event_bus()
    last_event_id: str | None = None
    heartbeat_counter = 0

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info("SSE_CLIENT_DISCONNECTED", aggregate_id=aggregate_id)
                break

            # Load new events
            if event_bus._store is not None:
                events = await event_bus._store.load_stream(aggregate_id, from_version)

                # Filter to only new events
                if last_event_id:
                    new_events = []
                    found = False
                    for e in events:
                        if found:
                            new_events.append(e)
                        elif e.event_id == last_event_id:
                            found = True
                    events = new_events

                # Send new events
                for event in events:
                    event_data = {
                        "event_id": event.event_id,
                        "event_type": event.event_type.value,
                        "aggregate_id": event.aggregate_id,
                        "timestamp": event.timestamp.isoformat(),
                        "payload": event.payload,
                    }
                    yield f"event: event\ndata: {json.dumps(event_data)}\n\n"
                    last_event_id = event.event_id

            # Wait for heartbeat interval
            await asyncio.sleep(SSE_HEARTBEAT_INTERVAL)

            # Send heartbeat
            heartbeat_counter += 1
            heartbeat_data = {
                "type": "heartbeat",
                "count": heartbeat_counter,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            yield f"event: heartbeat\ndata: {json.dumps(heartbeat_data)}\n\n"

    except asyncio.CancelledError:
        logger.info("SSE_STREAM_CANCELLED", aggregate_id=aggregate_id)
    except Exception as e:
        logger.error("SSE_STREAM_ERROR", aggregate_id=aggregate_id, error=str(e))
        error_data = {"error": str(e)}
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"


@router.get(
    "/sse/{aggregate_id}",
    summary="SSE stream for aggregate",
    description="Server-Sent Events stream with events and heartbeat every 15 seconds.",
)
async def sse_stream(
    aggregate_id: str,
    request: Request,
    from_version: int = Query(0, ge=0, description="Start from this version"),
) -> StreamingResponse:
    """SSE stream for real-time event updates.

    Args:
        aggregate_id: The aggregate to stream
        request: FastAPI request
        from_version: Start from this version

    Returns:
        StreamingResponse with SSE content
    """
    return StreamingResponse(
        event_stream_generator(aggregate_id, request, from_version),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# CONSUMER LAG ENDPOINT
# ============================================================================


class ConsumerLagResponse(BaseModel):
    """Consumer lag response."""

    consumer_group: str
    aggregate_id: str
    current_position: str | None = None
    head_position: str | None = None
    lag_events: int = 0
    lag_ms: float = 0.0


@router.get(
    "/consumer-lag/{consumer_group}",
    response_model=ConsumerLagResponse,
    summary="Get consumer lag",
    description="Returns lag information for a consumer group.",
)
async def get_consumer_lag(
    consumer_group: str,
    aggregate_id: str = Query("__global__", description="Stream to check"),
) -> ConsumerLagResponse:
    """Get consumer lag for a consumer group.

    Args:
        consumer_group: Consumer group name
        aggregate_id: Stream to check (default: global)

    Returns:
        ConsumerLagResponse with lag metrics
    """
    event_bus = get_event_bus()
    offset_store = get_offset_store()

    # Get head position
    head_event_id = None
    head_timestamp = None
    total_events = 0

    if event_bus._store is not None:
        events = await event_bus._store.load_stream(aggregate_id)
        if events:
            head_event_id = events[-1].event_id
            head_timestamp = events[-1].timestamp
            total_events = len(events)

    lag = await offset_store.get_lag(
        consumer_group=consumer_group,
        aggregate_id=aggregate_id,
        head_event_id=head_event_id,
        head_event_timestamp=head_timestamp,
        total_events=total_events,
    )

    return ConsumerLagResponse(
        consumer_group=lag.consumer_group,
        aggregate_id=lag.aggregate_id,
        current_position=lag.current_position,
        head_position=lag.head_position,
        lag_events=lag.lag_events,
        lag_ms=lag.lag_ms,
    )


# ============================================================================
# OBSERVABILITY ENDPOINTS
# ============================================================================


@router.get(
    "/metrics/prometheus",
    summary="Prometheus metrics",
    description="Returns metrics in Prometheus text format.",
    response_class=StreamingResponse,
)
async def prometheus_metrics() -> StreamingResponse:
    """Export metrics in Prometheus format.

    Returns:
        Prometheus-formatted metrics
    """
    from backend.src.fi_events.observability.metrics import get_metrics

    metrics = get_metrics()
    content = metrics.export_prometheus()

    return StreamingResponse(
        iter([content]),
        media_type="text/plain; charset=utf-8",
    )


@router.get(
    "/metrics/summary",
    summary="Metrics summary",
    description="Returns a summary of event metrics.",
)
async def metrics_summary() -> dict[str, Any]:
    """Get metrics summary.

    Returns:
        Summary dict with key metrics
    """
    from backend.src.fi_events.observability.metrics import get_metrics

    metrics = get_metrics()
    return metrics.get_summary()


@router.get(
    "/tracing/stats",
    summary="Tracing statistics",
    description="Returns tracing statistics and operation breakdown.",
)
async def tracing_stats() -> dict[str, Any]:
    """Get tracing statistics.

    Returns:
        Stats dict
    """
    from backend.src.fi_events.observability.tracing import get_tracer

    tracer = get_tracer()
    return tracer.get_stats()


@router.get(
    "/tracing/spans",
    summary="Recent spans",
    description="Returns recent tracing spans.",
)
async def recent_spans(
    limit: int = Query(50, ge=1, le=500, description="Maximum spans to return"),
) -> list[dict[str, Any]]:
    """Get recent tracing spans.

    Args:
        limit: Maximum spans to return

    Returns:
        List of span dicts
    """
    from backend.src.fi_events.observability.tracing import get_tracer

    tracer = get_tracer()
    spans = tracer.get_recent_spans(limit)
    return [s.to_dict() for s in spans]


@router.get(
    "/tracing/slow",
    summary="Slow spans",
    description="Returns spans slower than threshold.",
)
async def slow_spans(
    threshold_ms: float = Query(100.0, ge=1.0, description="Threshold in ms"),
    limit: int = Query(50, ge=1, le=500, description="Maximum spans to return"),
) -> list[dict[str, Any]]:
    """Get slow tracing spans.

    Args:
        threshold_ms: Threshold in milliseconds
        limit: Maximum spans to return

    Returns:
        List of slow span dicts
    """
    from backend.src.fi_events.observability.tracing import get_tracer

    tracer = get_tracer()
    spans = tracer.get_slow_spans(threshold_ms, limit)
    return [s.to_dict() for s in spans]
