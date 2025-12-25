"""FI Events - Event Sourcing package for Free Intelligence.

This package provides domain events, event bus, and persistent event store
for tracking system events in an append-only, auditable manner.

Architecture:
    domain/      - Event models, types, metadata
    application/ - EventBus (pub/sub), abstract EventStore
    infrastructure/ - HDF5 persistent store implementation
    api/         - FastAPI router for event endpoints

Usage:
    from backend.src.fi_events import EventBus, DomainEvent, EventType

    event_bus = get_event_bus()
    await event_bus.publish(TranscriptionStartedEvent(session_id="..."))

Author: Bernard Uriza Orozco
Created: 2024-12-24
"""

from backend.src.fi_events.application.event_bus import EventBus, get_event_bus
from backend.src.fi_events.domain.events import DomainEvent, EventType

__all__ = ["DomainEvent", "EventType", "EventBus", "get_event_bus"]
