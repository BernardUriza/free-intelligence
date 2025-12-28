"""Projection Registry - Central registration and management of projections.

Projections are materialized views built from the event stream.
They optimize read queries by pre-computing aggregate state.

The registry:
- Tracks all registered projections
- Routes events to relevant projections
- Manages projection lifecycle (start, stop, rebuild)
- Monitors projection health and lag

Usage:
    from fi_events.projections.registry import ProjectionRegistry, get_registry

    registry = get_registry()
    registry.register(SessionIndexProjection())
    await registry.start_all()
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from backend.src.fi_common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.src.fi_events.domain.events import DomainEvent, EventType

logger = get_logger(__name__)


class ProjectionStatus(str, Enum):
    """Projection lifecycle status."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    REBUILDING = "rebuilding"
    ERROR = "error"


@dataclass
class ProjectionState:
    """Runtime state of a projection."""

    status: ProjectionStatus = ProjectionStatus.STOPPED
    last_processed_event_id: str | None = None
    last_processed_at: datetime | None = None
    events_processed: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: datetime | None = None


class Projection(ABC):
    """Base class for all projections.

    A projection:
    - Subscribes to specific event types
    - Maintains its own read model (state)
    - Can be rebuilt from scratch

    Subclasses must implement:
    - name: Unique projection identifier
    - subscribed_events: List of EventTypes to process
    - handle(event): Process a single event
    - get_state(): Return current projection state
    """

    def __init__(self) -> None:
        self._state = ProjectionState()
        self._lock = asyncio.Lock()

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique projection name."""
        ...

    @property
    @abstractmethod
    def subscribed_events(self) -> list["EventType"]:
        """Event types this projection handles."""
        ...

    @abstractmethod
    async def handle(self, event: "DomainEvent") -> None:
        """Process a single event.

        Args:
            event: The domain event to process
        """
        ...

    @abstractmethod
    async def get_state(self) -> dict[str, Any]:
        """Get current projection state.

        Returns:
            Projection-specific state dict
        """
        ...

    @abstractmethod
    async def reset(self) -> None:
        """Reset projection to initial state.

        Called before rebuild.
        """
        ...

    async def process_event(self, event: "DomainEvent") -> bool:
        """Process event with error handling and state tracking.

        Args:
            event: Event to process

        Returns:
            True if processed successfully
        """
        async with self._lock:
            try:
                await self.handle(event)

                self._state.last_processed_event_id = event.event_id
                self._state.last_processed_at = datetime.now(UTC)
                self._state.events_processed += 1

                return True

            except Exception as e:
                error_msg = f"Failed to process {event.event_id}: {e}"
                self._state.errors.append(error_msg)
                if len(self._state.errors) > 100:
                    self._state.errors = self._state.errors[-100:]

                logger.error(
                    "PROJECTION_HANDLE_FAILED",
                    projection=self.name,
                    event_id=event.event_id,
                    error=str(e),
                )
                return False

    def get_runtime_state(self) -> ProjectionState:
        """Get runtime state."""
        return self._state


class ProjectionRegistry:
    """Central registry for all projections.

    Manages projection lifecycle and event routing.
    """

    def __init__(self) -> None:
        self._projections: dict[str, Projection] = {}
        self._event_subscriptions: dict["EventType", list[Projection]] = {}
        self._started = False

    def register(self, projection: Projection) -> None:
        """Register a projection.

        Args:
            projection: Projection instance to register

        Raises:
            ValueError: If projection with same name already registered
        """
        if projection.name in self._projections:
            raise ValueError(f"Projection '{projection.name}' already registered")

        self._projections[projection.name] = projection

        # Build subscription index
        for event_type in projection.subscribed_events:
            if event_type not in self._event_subscriptions:
                self._event_subscriptions[event_type] = []
            self._event_subscriptions[event_type].append(projection)

        logger.info(
            "PROJECTION_REGISTERED",
            name=projection.name,
            subscribed_events=[e.value for e in projection.subscribed_events],
        )

    def unregister(self, name: str) -> bool:
        """Unregister a projection.

        Args:
            name: Projection name

        Returns:
            True if found and removed
        """
        projection = self._projections.pop(name, None)
        if projection is None:
            return False

        # Remove from subscriptions
        for event_type in projection.subscribed_events:
            if event_type in self._event_subscriptions:
                self._event_subscriptions[event_type] = [
                    p for p in self._event_subscriptions[event_type] if p.name != name
                ]

        logger.info("PROJECTION_UNREGISTERED", name=name)
        return True

    def get(self, name: str) -> Projection | None:
        """Get projection by name."""
        return self._projections.get(name)

    def list_projections(self) -> list[dict[str, Any]]:
        """List all registered projections with state.

        Returns:
            List of projection info dicts
        """
        return [
            {
                "name": p.name,
                "subscribed_events": [e.value for e in p.subscribed_events],
                "status": p.get_runtime_state().status.value,
                "events_processed": p.get_runtime_state().events_processed,
                "last_processed_at": (
                    p.get_runtime_state().last_processed_at.isoformat()
                    if p.get_runtime_state().last_processed_at
                    else None
                ),
                "error_count": len(p.get_runtime_state().errors),
            }
            for p in self._projections.values()
        ]

    async def dispatch_event(self, event: "DomainEvent") -> int:
        """Dispatch event to all subscribed projections.

        Args:
            event: Event to dispatch

        Returns:
            Number of projections that processed the event
        """
        subscribers = self._event_subscriptions.get(event.event_type, [])
        if not subscribers:
            return 0

        # Process in parallel
        results = await asyncio.gather(
            *[p.process_event(event) for p in subscribers],
            return_exceptions=True,
        )

        processed = sum(1 for r in results if r is True)

        logger.debug(
            "EVENT_DISPATCHED",
            event_id=event.event_id,
            event_type=event.event_type.value,
            subscribers=len(subscribers),
            processed=processed,
        )

        return processed

    async def start_all(self) -> None:
        """Start all projections."""
        if self._started:
            return

        for projection in self._projections.values():
            projection._state.status = ProjectionStatus.RUNNING
            projection._state.started_at = datetime.now(UTC)

        self._started = True
        logger.info("PROJECTIONS_STARTED", count=len(self._projections))

    async def stop_all(self) -> None:
        """Stop all projections."""
        for projection in self._projections.values():
            projection._state.status = ProjectionStatus.STOPPED

        self._started = False
        logger.info("PROJECTIONS_STOPPED", count=len(self._projections))

    async def rebuild(self, name: str, event_store: Any) -> dict[str, Any]:
        """Rebuild a projection from scratch.

        Args:
            name: Projection name
            event_store: EventStore to load events from

        Returns:
            Rebuild result with stats
        """
        projection = self._projections.get(name)
        if projection is None:
            return {"error": f"Projection '{name}' not found"}

        projection._state.status = ProjectionStatus.REBUILDING
        start_time = datetime.now(UTC)

        try:
            # Reset state
            await projection.reset()
            projection._state.events_processed = 0
            projection._state.errors = []

            # Load all events (could be optimized with batching)
            events = await event_store.load_all()

            processed = 0
            for event in events:
                if event.event_type in projection.subscribed_events:
                    await projection.process_event(event)
                    processed += 1

            projection._state.status = ProjectionStatus.RUNNING

            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            logger.info(
                "PROJECTION_REBUILT",
                name=name,
                events_processed=processed,
                duration_ms=round(duration_ms, 2),
            )

            return {
                "name": name,
                "events_processed": processed,
                "duration_ms": round(duration_ms, 2),
                "status": "completed",
            }

        except Exception as e:
            projection._state.status = ProjectionStatus.ERROR
            logger.error("PROJECTION_REBUILD_FAILED", name=name, error=str(e))
            return {
                "name": name,
                "status": "failed",
                "error": str(e),
            }


# ============================================================================
# SINGLETON
# ============================================================================

_registry: ProjectionRegistry | None = None


def get_registry() -> ProjectionRegistry:
    """Get global projection registry singleton.

    Returns:
        ProjectionRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ProjectionRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    _registry = None
