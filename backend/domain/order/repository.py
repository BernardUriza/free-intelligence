"""Order repository interface - domain contract.

Author: Claude Code
Created: 2026-01-28
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from backend.domain.order.entity import Order, OrderStatus, OrderType


class IOrderRepository(ABC):
    """Interface for order persistence operations."""

    @abstractmethod
    def save(self, order: Order) -> str:
        """Persist order entity."""
        pass

    @abstractmethod
    def find_by_id(self, order_id: str) -> Order | None:
        """Find order by ID."""
        pass

    @abstractmethod
    def find_by_session(self, session_id: str) -> List[Order]:
        """Find all orders for a session."""
        pass

    @abstractmethod
    def find_by_status(self, status: OrderStatus) -> List[Order]:
        """Find orders by status."""
        pass

    @abstractmethod
    def find_by_type(self, order_type: OrderType) -> List[Order]:
        """Find orders by type."""
        pass

    @abstractmethod
    def update(self, order: Order) -> bool:
        """Update existing order."""
        pass

    @abstractmethod
    def delete(self, order_id: str) -> bool:
        """Delete order by ID."""
        pass

    @abstractmethod
    def exists(self, order_id: str) -> bool:
        """Check if order exists."""
        pass
