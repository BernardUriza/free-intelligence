"""EventBus - Publish/Subscribe for domain events.

The EventBus is the central hub for event distribution:
1. Services publish events via bus.publish(event)
2. Bus persists to EventStore (if configured)
3. Bus notifies subscribers (handlers, projectors)
4. Metrics/logging happen here

Usage:
    event_bus = get_event_bus()
    await event_bus.publish(TranscriptionStartedEvent.create(session_id="..."))
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Awaitable, Callable

from backend.src.fi_common.logging.logger import get_logger

if TYPE_CHECKING:
    from backend.src.fi_events.application.event_store import EventStore
    from backend.src.fi_events.domain.events import DomainEvent, EventType

logger = get_logger(__name__)

# Type alias for event handlers
EventHandler = Callable[["DomainEvent"], Awaitable[None]]


class EventBus:
    """In-process event bus with optional persistence.

    Features:
    - Async publish with optional await for handlers
    - Pluggable EventStore for persistence
    - Subscribe handlers by event type
    - Metrics: events_published, publish_latency
    """

    def __init__(self, event_store: "EventStore | None" = None):
        """Initialize event bus.

        Args:
            event_store: Optional store for persistence. If None, events
                        are only delivered to subscribers (fire-and-forget).
        """
        self._store = event_store
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []

        # Metrics
        self._events_published = 0
        self._total_latency_ms = 0.0

        logger.info(
            "EVENT_BUS_INITIALIZED",
            has_store=event_store is not None,
        )

    async def publish(
        self,
        event: "DomainEvent",
        persist: bool = True,
    ) -> None:
        """Publish domain event.

        1. Persist to store (if configured and persist=True)
        2. Notify type-specific handlers
        3. Notify global handlers
        4. Log and update metrics

        Args:
            event: The domain event to publish
            persist: Whether to persist to store (default True)

        Raises:
            EventStoreError: If persistence fails
        """
        start_time = time.perf_counter()

        try:
            # 1. Persist to store
            if persist and self._store is not None:
                await self._store.append(event)

            # 2. Notify handlers (fire-and-forget, don't block)
            handlers = (
                self._handlers.get(event.event_type.value, [])
                + self._global_handlers
            )

            if handlers:
                # Run handlers concurrently
                await asyncio.gather(
                    *[self._safe_call(h, event) for h in handlers],
                    return_exceptions=True,
                )

            # 3. Metrics
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._events_published += 1
            self._total_latency_ms += elapsed_ms

            # 4. Log (structured, no PHI)
            logger.info(
                "EVENT_PUBLISHED",
                event_id=event.event_id,
                event_type=event.event_type.value,
                aggregate_id=event.aggregate_id,
                latency_ms=round(elapsed_ms, 2),
                persisted=persist and self._store is not None,
            )

        except Exception as e:
            logger.error(
                "EVENT_PUBLISH_FAILED",
                event_id=event.event_id,
                event_type=event.event_type.value,
                error=str(e),
            )
            raise

    async def _safe_call(
        self,
        handler: EventHandler,
        event: "DomainEvent",
    ) -> None:
        """Call handler safely, catching exceptions."""
        try:
            await handler(event)
        except Exception as e:
            logger.warning(
                "EVENT_HANDLER_FAILED",
                event_id=event.event_id,
                handler=handler.__name__,
                error=str(e),
            )

    def subscribe(
        self,
        event_type: "EventType",
        handler: EventHandler,
    ) -> None:
        """Subscribe handler to specific event type.

        Args:
            event_type: Type of events to receive
            handler: Async function to call with event
        """
        self._handlers[event_type.value].append(handler)
        logger.debug(
            "EVENT_HANDLER_SUBSCRIBED",
            event_type=event_type.value,
            handler=handler.__name__,
        )

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe handler to ALL event types.

        Use sparingly - mainly for logging/metrics.

        Args:
            handler: Async function to call with every event
        """
        self._global_handlers.append(handler)
        logger.debug(
            "GLOBAL_EVENT_HANDLER_SUBSCRIBED",
            handler=handler.__name__,
        )

    def get_metrics(self) -> dict:
        """Get event bus metrics.

        Returns:
            Dict with events_published, avg_latency_ms, handlers_count
        """
        avg_latency = (
            self._total_latency_ms / self._events_published
            if self._events_published > 0
            else 0.0
        )
        return {
            "events_published": self._events_published,
            "avg_latency_ms": round(avg_latency, 2),
            "handlers_count": sum(len(h) for h in self._handlers.values()),
            "global_handlers_count": len(self._global_handlers),
        }


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global EventBus singleton.

    The bus is lazily initialized without a store.
    To enable persistence, call configure_event_bus() at startup.

    Returns:
        The global EventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def configure_event_bus(event_store: "EventStore") -> EventBus:
    """Configure the global EventBus with a store.

    Call this at application startup to enable persistence.

    Args:
        event_store: The store implementation to use

    Returns:
        The configured EventBus
    """
    global _event_bus
    _event_bus = EventBus(event_store=event_store)
    logger.info("EVENT_BUS_CONFIGURED", store_type=type(event_store).__name__)
    return _event_bus
