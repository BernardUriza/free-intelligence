"""EventStore - Abstract interface for event persistence.

The EventStore is responsible for:
1. Appending events (append-only, no updates/deletes)
2. Loading event streams by aggregate_id
3. Maintaining event ordering
4. Providing durability guarantees

Implementations:
- HDF5EventStore (infrastructure/) - Production, append-only HDF5
- InMemoryEventStore - Testing only
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infrastructure.events.domain.events import DomainEvent, EventType


class EventStore(ABC):
    """Abstract event store interface.

    All implementations must guarantee:
    - Append-only semantics (no updates, no deletes)
    - Ordered event streams per aggregate
    - Durability (events survive restarts)
    - Idempotency (same event_id = no duplicate)
    """

    @abstractmethod
    async def append(self, event: "DomainEvent") -> None:
        """Append event to the store.

        Args:
            event: Domain event to persist

        Raises:
            EventStoreError: If append fails
            DuplicateEventError: If event_id already exists
        """
        pass

    @abstractmethod
    async def load_stream(
        self,
        aggregate_id: str,
        from_version: int = 0,
    ) -> list["DomainEvent"]:
        """Load all events for an aggregate.

        Args:
            aggregate_id: The aggregate to load events for
            from_version: Start from this version (0 = all)

        Returns:
            List of events in chronological order

        Raises:
            EventStoreError: If load fails
        """
        pass

    @abstractmethod
    async def load_by_type(
        self,
        event_type: "EventType",
        limit: int = 100,
    ) -> list["DomainEvent"]:
        """Load events by type (for projections/analytics).

        Args:
            event_type: Type of events to load
            limit: Maximum number to return

        Returns:
            List of events, newest first
        """
        pass

    @abstractmethod
    async def count_events(self, aggregate_id: str | None = None) -> int:
        """Count events in store.

        Args:
            aggregate_id: If provided, count only for this aggregate

        Returns:
            Number of events
        """
        pass


class EventStoreError(Exception):
    """Base exception for event store errors."""

    pass


class DuplicateEventError(EventStoreError):
    """Raised when trying to append duplicate event_id."""

    pass
