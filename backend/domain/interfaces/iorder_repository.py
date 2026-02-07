"""Order repository interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.domain.order import Order


class IOrderRepository(ABC):
    """Order repository interface."""

    @abstractmethod
    def create(self, order: Order) -> str:
        """Create a new order."""
        ...

    @abstractmethod
    def get(self, order_id: str) -> Order | None:
        """Get order by ID."""
        ...

    @abstractmethod
    def list_by_session(self, session_id: str) -> list[Order]:
        """List orders for a session."""
        ...
