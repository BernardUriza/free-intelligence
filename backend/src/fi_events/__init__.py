"""FI Events - Event Sourcing package for Free Intelligence.

This package provides domain events, event bus, persistent event store,
replay, projections, and observability for tracking system events
in an append-only, auditable manner.

Architecture:
    domain/         - Event models, types, metadata, contracts, identity
    application/    - EventBus (pub/sub), EventStore, Replay
    infrastructure/ - HDF5 store, snapshots, consumer offsets
    projections/    - Materialized views (SessionIndex, Timeline, etc.)
    api/            - FastAPI router for event endpoints

Usage:
    from backend.src.fi_events import EventBus, DomainEvent, EventType

    event_bus = get_event_bus()
    await event_bus.publish(TranscriptionStartedEvent(session_id="..."))

Phase 2 Features:
    - Contracts & versioning (strict payload validation, upcasters)
    - ULID-based idempotency (dedupe_key for exactly-once)
    - Replay & snapshots (aggregate state reconstruction)
    - Projections (SessionIndex, TranscriptionTimeline, etc.)
    - Consumer offsets (position tracking, lag monitoring)
    - SSE streaming with heartbeat
    - Observability (metrics, tracing)

Author: Bernard Uriza Orozco
Created: 2024-12-24
"""

# Core
from backend.src.fi_events.application.event_bus import EventBus, get_event_bus

# Replay
from backend.src.fi_events.application.replay import (
    ReplayResult,
    replay_aggregate,
)

# Contracts
from backend.src.fi_events.domain.contracts import (
    get_contract,
    list_contracts,
    validate_payload,
)
from backend.src.fi_events.domain.events import (
    DomainEvent,
    EventType,
    SOAPGenerationEvent,
    TranscriptionChunkEvent,
    TranscriptionEndedEvent,
    TranscriptionFailedEvent,
    TranscriptionStartedEvent,
)

# Identity
from backend.src.fi_events.domain.identity import (
    generate_dedupe_key,
    generate_event_id,
)

# Consumer offsets
from backend.src.fi_events.infrastructure.consumer_offsets import (
    ConsumerLag,
    ConsumerPosition,
    get_offset_store,
)

# Snapshots
from backend.src.fi_events.infrastructure.snapshots import (
    SnapshotStore,
    get_snapshot_store,
)

# Projections
from backend.src.fi_events.projections import (
    get_registry,
    register_default_projections,
)

__all__ = [
    # Core
    "DomainEvent",
    "EventType",
    "EventBus",
    "get_event_bus",
    # Specific events
    "TranscriptionStartedEvent",
    "TranscriptionChunkEvent",
    "TranscriptionEndedEvent",
    "TranscriptionFailedEvent",
    "SOAPGenerationEvent",
    # Identity
    "generate_event_id",
    "generate_dedupe_key",
    # Contracts
    "validate_payload",
    "get_contract",
    "list_contracts",
    # Replay
    "replay_aggregate",
    "ReplayResult",
    # Snapshots
    "SnapshotStore",
    "get_snapshot_store",
    # Projections
    "get_registry",
    "register_default_projections",
    # Consumer offsets
    "get_offset_store",
    "ConsumerPosition",
    "ConsumerLag",
]
