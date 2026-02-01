"""Order repository interface."""

from abc import ABC, abstractmethod
from typing import Optional

# Forward reference to avoid circular imports
if False:
    from backend.domain.order import Order


class IOrderRepository(ABC):
    """Order repository interface."""

    @abstractmethod
    def create(self, order: "Order") -> str:
        """Create a new order."""
        ...

    @abstractmethod
    def get(self, order_id: str) -> Optional["Order"]:
        """Get order by ID."""
        ...

    @abstractmethod
    def list_by_session(self, session_id: str) -> list["Order"]:
        """List orders for a session."""
        ...
