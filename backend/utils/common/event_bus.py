"""In-memory event bus implementation."""

from collections.abc import Callable
from typing import Any

from backend.infrastructure.interfaces.ievent_bus import IEventBus


class InMemoryEventBus(IEventBus):
    """Simple in-memory event bus for decoupled communication.

    Thread-safe for basic usage, but not designed for high concurrency.
    """

    def __init__(self) -> None:
        """Initialize event bus with empty subscriptions."""
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}

    def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event to all subscribers.

        Args:
            event_type: Type of event
            data: Event payload
        """
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(data)
                except Exception:
                    # In a real implementation, you might want to log this
                    # For now, we'll just continue to other handlers
                    pass

    def subscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """Subscribe to an event type.

        Args:
            event_type: Event type to subscribe to
            handler: Function to call when event is published
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[dict[str, Any]], None]) -> None:
        """Unsubscribe from an event type.

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                # Clean up empty lists
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]
            except ValueError:
                # Handler not found, ignore
                pass
