"""Event bus interface for decoupled inter-layer communication."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Dict


class IEventBus(ABC):
    """Abstract interface for event bus operations."""

    @abstractmethod
    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """Publish an event to all subscribers.

        Args:
            event_type: Type of event (e.g., 'session.created', 'task.completed')
            data: Event payload data
        """
        pass

    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Subscribe to an event type.

        Args:
            event_type: Event type to subscribe to
            handler: Function to call when event is published
        """
        pass

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Unsubscribe from an event type.

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler function to remove
        """
        pass
