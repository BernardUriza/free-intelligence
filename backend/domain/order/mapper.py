"""Order mapper - DTO to Entity conversions.

Author: Claude Code
Created: 2026-01-28
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from backend.domain.order.entity import Order, OrderStatus, OrderType

if TYPE_CHECKING:
    from backend.api.routers.order.public.orders import (
        OrderCreateRequest,
        OrderUpdateRequest,
    )


@dataclass
class OrderHDF5Metadata:
    """Typed HDF5 metadata for Order (Fix #3 - Type Safety).

    All fields REQUIRED (no .get() calls with defaults).
    """

    session_id: str
    order_type: str  # OrderType.value
    description: str
    status: str  # OrderStatus.value
    created_at: str  # ISO format
    updated_at: str  # ISO format
    completed_at: str | None
    cancelled_at: str | None
    notes: str | None


class OrderMapper:
    """Maps between Order representations."""

    @staticmethod
    def from_create_dto(dto: OrderCreateRequest, order_id: str, session_id: str) -> Order:
        """Convert OrderCreateRequest to domain entity."""
        return Order(
            order_id=order_id,
            session_id=session_id,
            order_type=OrderType(dto.order_type),
            description=dto.description,
            notes=dto.notes if hasattr(dto, "notes") else None,
        )

    @staticmethod
    def from_hdf5(order_id: str, metadata: OrderHDF5Metadata) -> Order:
        """Convert HDF5 metadata to domain entity (Fix #3 - Type Safety).

        Args:
            order_id: Order UUID
            metadata: TYPED HDF5 metadata

        Returns:
            Order domain entity

        Raises:
            AttributeError: If metadata missing required fields
            ValueError: If datetime strings invalid
        """
        return Order(
            order_id=order_id,
            session_id=metadata.session_id,
            order_type=OrderType(metadata.order_type),
            description=metadata.description,
            status=OrderStatus(metadata.status),
            created_at=datetime.fromisoformat(metadata.created_at),
            updated_at=datetime.fromisoformat(metadata.updated_at),
            completed_at=(
                datetime.fromisoformat(metadata.completed_at)
                if metadata.completed_at
                else None
            ),
            cancelled_at=(
                datetime.fromisoformat(metadata.cancelled_at)
                if metadata.cancelled_at
                else None
            ),
            notes=metadata.notes,
        )

    @staticmethod
    def to_hdf5_metadata(entity: Order) -> OrderHDF5Metadata:
        """Convert domain entity to HDF5 metadata (Fix #3 - Type Safety).

        Returns:
            TYPED OrderHDF5Metadata (use dataclasses.asdict() in repository)
        """
        return OrderHDF5Metadata(
            session_id=entity.session_id,
            order_type=entity.order_type.value,
            description=entity.description,
            status=entity.status.value,
            created_at=entity.created_at.isoformat(),
            updated_at=entity.updated_at.isoformat(),
            completed_at=entity.completed_at.isoformat() if entity.completed_at else None,
            cancelled_at=entity.cancelled_at.isoformat() if entity.cancelled_at else None,
            notes=entity.notes,
        )
