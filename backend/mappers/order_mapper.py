"""Order Mapper - DB ↔ Domain mapping for Order entities.

Handles bidirectional conversion between Order domain entities and HDF5 persistence.

Pattern:
    Repository calls: OrderMapper.to_hdf5_metadata(order) → OrderHDF5Metadata
    Repository calls: OrderMapper.from_hdf5(order_id, metadata) → Order

Author: Claude Code (P1-5 Repository Mappers)
Created: 2026-02-02
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.domain.order import Order, OrderStatus, OrderType


# ============================================================================
# HDF5 Persistence Structure
# ============================================================================


@dataclass
class OrderHDF5Metadata:
    """Metadata for Order persistence in HDF5.

    Includes all Order fields stored as JSON in HDF5 group attributes.
    """

    order_id: str
    session_id: str
    type: str  # OrderType.value (prescription|lab|imaging|referral)
    status: str  # OrderStatus.value (draft|active|completed|cancelled)
    content: dict[str, Any]


# ============================================================================
# OrderMapper - Bidirectional Mapping
# ============================================================================


class OrderMapper:
    """Maps Order domain entity ↔ HDF5 persistence structures.

    Responsibilities:
    - Convert Order → OrderHDF5Metadata for persistence
    - Convert OrderHDF5Metadata → Order for domain use
    - Handle enum serialization (OrderType, OrderStatus)
    """

    @staticmethod
    def to_hdf5_metadata(order: Order) -> OrderHDF5Metadata:
        """Convert Order domain entity to HDF5 metadata structure.

        Args:
            order: Order entity from domain layer

        Returns:
            OrderHDF5Metadata dataclass for HDF5 storage

        Example:
            >>> order = Order(id="123", session_id="456", type=OrderType.PRESCRIPTION, ...)
            >>> metadata = OrderMapper.to_hdf5_metadata(order)
            >>> # Store in HDF5: group.attrs["metadata"] = json.dumps(asdict(metadata))
        """
        # Extract order_id (handle both 'id' and 'order_id' for compatibility)
        order_id = getattr(order, "order_id", None) or getattr(order, "id", None)
        if not order_id:
            raise ValueError("Order must have 'id' or 'order_id' field")

        # Serialize enums to strings
        order_type = order.type.value if isinstance(order.type, OrderType) else str(order.type)
        order_status = (
            order.status.value if isinstance(order.status, OrderStatus) else str(order.status)
        )

        return OrderHDF5Metadata(
            order_id=order_id,
            session_id=order.session_id,
            type=order_type,
            status=order_status,
            content=order.content,
        )

    @staticmethod
    def from_hdf5(order_id: str, metadata: OrderHDF5Metadata | dict[str, Any]) -> Order:
        """Convert HDF5 metadata to Order domain entity.

        Args:
            order_id: Order identifier (for validation)
            metadata: OrderHDF5Metadata dataclass or dict from HDF5 attributes

        Returns:
            Order domain entity with all fields populated

        Example:
            >>> metadata_dict = json.loads(group.attrs["metadata"])
            >>> metadata = OrderHDF5Metadata(**metadata_dict)
            >>> order = OrderMapper.from_hdf5("123", metadata)
        """
        # Handle both dataclass and dict inputs (for backwards compatibility)
        if isinstance(metadata, OrderHDF5Metadata):
            metadata_dict = {
                "order_id": metadata.order_id,
                "session_id": metadata.session_id,
                "type": metadata.type,
                "status": metadata.status,
                "content": metadata.content,
            }
        else:
            metadata_dict = metadata

        # Validate order_id consistency
        if order_id != metadata_dict.get("order_id"):
            raise ValueError(
                f"order_id mismatch: path={order_id}, metadata={metadata_dict.get('order_id')}"
            )

        # Convert string enums to enum instances
        order_type = OrderType(metadata_dict["type"])
        order_status = OrderStatus(metadata_dict["status"])

        # Create Order (using 'id' field as per dataclass definition)
        return Order(
            id=metadata_dict["order_id"],
            session_id=metadata_dict["session_id"],
            type=order_type,
            status=order_status,
            content=metadata_dict["content"],
        )
