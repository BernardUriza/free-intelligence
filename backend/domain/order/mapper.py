"""Order mapper - DTO to Entity conversions.

Author: Claude Code
Created: 2026-01-28
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

from backend.domain.order.entity import Order, OrderStatus, OrderType

if TYPE_CHECKING:
    from backend.api.routers.order.public.orders import (
        OrderCreateRequest,
        OrderUpdateRequest,
    )


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
    def from_hdf5(order_id: str, metadata: Dict[str, Any]) -> Order:
        """Convert HDF5 metadata to domain entity."""
        return Order(
            order_id=order_id,
            session_id=metadata["session_id"],
            order_type=OrderType(metadata["order_type"]),
            description=metadata["description"],
            status=OrderStatus(metadata.get("status", "pending")),
            created_at=datetime.fromisoformat(
                metadata.get("created_at", datetime.utcnow().isoformat())
            ),
            updated_at=datetime.fromisoformat(
                metadata.get("updated_at", datetime.utcnow().isoformat())
            ),
            completed_at=(
                datetime.fromisoformat(metadata["completed_at"])
                if metadata.get("completed_at")
                else None
            ),
            cancelled_at=(
                datetime.fromisoformat(metadata["cancelled_at"])
                if metadata.get("cancelled_at")
                else None
            ),
            notes=metadata.get("notes"),
        )

    @staticmethod
    def to_hdf5_metadata(entity: Order) -> Dict[str, Any]:
        """Convert domain entity to HDF5 metadata dict."""
        return {
            "session_id": entity.session_id,
            "order_type": entity.order_type.value,
            "description": entity.description,
            "status": entity.status.value,
            "created_at": entity.created_at.isoformat(),
            "updated_at": entity.updated_at.isoformat(),
            "completed_at": entity.completed_at.isoformat() if entity.completed_at else None,
            "cancelled_at": entity.cancelled_at.isoformat() if entity.cancelled_at else None,
            "notes": entity.notes,
        }
