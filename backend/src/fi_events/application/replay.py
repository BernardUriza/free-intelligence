"""Event Replay - Reconstruct aggregate state from event stream.

Replay allows:
- Rebuilding aggregate state from scratch
- Validating event stream integrity
- Debugging/auditing historical state
- Rebuilding projections after schema changes

Usage:
    from fi_events.application.replay import replay_aggregate, ReplayResult

    result = await replay_aggregate("session-123")
    print(result.event_count, result.final_state)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, TYPE_CHECKING

from backend.src.fi_common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.src.fi_events.domain.events import DomainEvent
    from backend.src.fi_events.application.event_store import EventStore

logger = get_logger(__name__)


@dataclass
class ReplayResult:
    """Result of replaying an aggregate's event stream."""

    aggregate_id: str
    event_count: int
    first_event_id: str | None = None
    last_event_id: str | None = None
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    final_state: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    replay_duration_ms: float = 0.0


# Type alias for state reducer function
StateReducer = Callable[[dict[str, Any], "DomainEvent"], dict[str, Any]]


def default_reducer(state: dict[str, Any], event: "DomainEvent") -> dict[str, Any]:
    """Default reducer that accumulates event counts by type.

    Args:
        state: Current state
        event: Event to apply

    Returns:
        Updated state
    """
    # Track event counts by type
    event_counts = state.get("event_counts", {})
    event_type = event.event_type.value
    event_counts[event_type] = event_counts.get(event_type, 0) + 1
    state["event_counts"] = event_counts

    # Track timeline
    timeline = state.get("timeline", [])
    timeline.append({
        "event_id": event.event_id,
        "event_type": event_type,
        "timestamp": event.timestamp.isoformat(),
    })
    state["timeline"] = timeline

    # Track latest payload per event type
    latest = state.get("latest_by_type", {})
    latest[event_type] = event.payload
    state["latest_by_type"] = latest

    return state


async def replay_aggregate(
    aggregate_id: str,
    event_store: "EventStore",
    reducer: StateReducer | None = None,
    from_snapshot: dict[str, Any] | None = None,
    from_version: int = 0,
) -> ReplayResult:
    """Replay event stream to reconstruct aggregate state.

    Args:
        aggregate_id: The aggregate to replay
        event_store: EventStore instance to load events from
        reducer: Optional custom state reducer function.
                Default accumulates event counts and timeline.
        from_snapshot: Optional snapshot to start from (avoids full replay)
        from_version: Start replaying from this version (0 = all)

    Returns:
        ReplayResult with final state and metadata
    """
    import time

    start_time = time.perf_counter()
    reducer = reducer or default_reducer

    # Initialize state
    state = from_snapshot.copy() if from_snapshot else {}

    result = ReplayResult(aggregate_id=aggregate_id, event_count=0)

    try:
        # Load events
        events = await event_store.load_stream(aggregate_id, from_version)

        if not events:
            logger.info("REPLAY_EMPTY_STREAM", aggregate_id=aggregate_id)
            return result

        result.event_count = len(events)
        result.first_event_id = events[0].event_id
        result.last_event_id = events[-1].event_id
        result.first_timestamp = events[0].timestamp
        result.last_timestamp = events[-1].timestamp

        # Apply events
        for event in events:
            try:
                state = reducer(state, event)
            except Exception as e:
                error_msg = f"Reducer failed on {event.event_id}: {e}"
                result.errors.append(error_msg)
                logger.warning("REPLAY_REDUCER_FAILED", event_id=event.event_id, error=str(e))

        result.final_state = state

    except Exception as e:
        result.errors.append(f"Replay failed: {e}")
        logger.error("REPLAY_FAILED", aggregate_id=aggregate_id, error=str(e))

    result.replay_duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "REPLAY_COMPLETED",
        aggregate_id=aggregate_id,
        event_count=result.event_count,
        error_count=len(result.errors),
        duration_ms=round(result.replay_duration_ms, 2),
    )

    return result


async def validate_stream(
    aggregate_id: str,
    event_store: "EventStore",
) -> dict[str, Any]:
    """Validate event stream integrity.

    Checks:
    - Events are in chronological order
    - No duplicate event_ids
    - All events have required fields

    Args:
        aggregate_id: The aggregate to validate
        event_store: EventStore instance

    Returns:
        Validation result dict with is_valid, errors, warnings
    """
    result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "event_count": 0,
    }

    try:
        events = await event_store.load_stream(aggregate_id)
        result["event_count"] = len(events)

        if not events:
            return result

        seen_ids = set()
        prev_timestamp = None

        for i, event in enumerate(events):
            # Check for duplicate IDs
            if event.event_id in seen_ids:
                result["errors"].append(f"Duplicate event_id at position {i}: {event.event_id}")
                result["is_valid"] = False
            seen_ids.add(event.event_id)

            # Check chronological order
            if prev_timestamp and event.timestamp < prev_timestamp:
                result["warnings"].append(
                    f"Event {event.event_id} is out of order at position {i}"
                )
            prev_timestamp = event.timestamp

            # Check required fields
            if not event.aggregate_id:
                result["errors"].append(f"Missing aggregate_id at position {i}")
                result["is_valid"] = False

    except Exception as e:
        result["errors"].append(f"Validation failed: {e}")
        result["is_valid"] = False

    logger.info(
        "STREAM_VALIDATED",
        aggregate_id=aggregate_id,
        is_valid=result["is_valid"],
        error_count=len(result["errors"]),
    )

    return result


# ============================================================================
# DOMAIN-SPECIFIC REDUCERS
# ============================================================================


def transcription_reducer(state: dict[str, Any], event: "DomainEvent") -> dict[str, Any]:
    """Reducer for transcription aggregates.

    Builds state with:
    - status: pending/in_progress/completed/failed
    - total_chunks: count of chunks
    - total_duration_ms: sum of durations
    """
    from backend.src.fi_events.domain.events import EventType

    event_type = event.event_type

    if event_type == EventType.TRANSCRIPTION_STARTED:
        state["status"] = "in_progress"
        state["mode"] = event.payload.get("mode", "medical")
        state["started_at"] = event.timestamp.isoformat()
        state["chunks"] = []

    elif event_type == EventType.TRANSCRIPTION_CHUNK_RECEIVED:
        chunks = state.get("chunks", [])
        chunks.append({
            "chunk_number": event.payload.get("chunk_number"),
            "duration_ms": event.payload.get("duration_ms", 0),
            "audio_size_bytes": event.payload.get("audio_size_bytes", 0),
            "timestamp": event.timestamp.isoformat(),
        })
        state["chunks"] = chunks
        state["total_chunks"] = len(chunks)

    elif event_type == EventType.TRANSCRIPTION_ENDED:
        state["status"] = "completed"
        state["ended_at"] = event.timestamp.isoformat()
        state["final_stats"] = {
            "total_chunks": event.payload.get("total_chunks"),
            "total_duration_ms": event.payload.get("total_duration_ms"),
        }

    elif event_type == EventType.TRANSCRIPTION_FAILED:
        state["status"] = "failed"
        state["error"] = {
            "code": event.payload.get("error_code"),
            "message": event.payload.get("error_message"),
        }

    return state


def session_reducer(state: dict[str, Any], event: "DomainEvent") -> dict[str, Any]:
    """Reducer for session aggregates.

    Builds complete session state including transcription, SOAP, etc.
    """
    from backend.src.fi_events.domain.events import EventType

    event_type = event.event_type

    # Initialize
    if "created_at" not in state:
        state["created_at"] = event.timestamp.isoformat()

    state["updated_at"] = event.timestamp.isoformat()

    # Transcription
    if event_type.value.startswith("TRANSCRIPTION_"):
        transcription = state.get("transcription", {})
        transcription = transcription_reducer(transcription, event)
        state["transcription"] = transcription

    # SOAP
    elif event_type == EventType.SOAP_GENERATION_STARTED:
        state["soap"] = {"status": "in_progress"}
    elif event_type == EventType.SOAP_GENERATION_COMPLETED:
        state["soap"] = {
            "status": "completed",
            "quality_score": event.payload.get("quality_score"),
            "completeness": event.payload.get("completeness"),
        }
    elif event_type == EventType.SOAP_GENERATION_FAILED:
        state["soap"] = {
            "status": "failed",
            "error_code": event.payload.get("error_code"),
        }

    # Diarization
    elif event_type == EventType.DIARIZATION_COMPLETED:
        state["diarization"] = {
            "status": "completed",
            "speaker_count": event.payload.get("speaker_count"),
            "total_segments": event.payload.get("total_segments"),
        }

    # Session lifecycle
    elif event_type == EventType.SESSION_FINALIZED:
        state["status"] = "finalized"
        state["finalized_at"] = event.timestamp.isoformat()

    return state
