"""HDF5 Order Repository Implementation.

Author: Claude Code
Created: 2026-01-28
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import h5py

from backend.domain.order import Order
from backend.domain.interfaces.iorder_repository import IOrderRepository
from backend.mappers.order_mapper import OrderMapper, OrderHDF5Metadata


class HDF5OrderRepository(IOrderRepository):
    """Implements IOrderRepository using HDF5 task-based storage (Fix #1).

    Storage-agnostic interface - internal HDF5 structure is an implementation detail.
    Orders are stored with metadata and associated with sessions.
    Structure may change without affecting domain layer.
    """

    def __init__(self, hdf5_path: str | Path):
        """Initialize repository with HDF5 file path.

        Args:
            hdf5_path: Path to HDF5 corpus file
        """
        self.hdf5_path = Path(hdf5_path)
        if not self.hdf5_path.exists():
            raise FileNotFoundError(f"HDF5 file not found: {hdf5_path}")

    def save(self, order: Order) -> str:
        """Persist order entity.

        Args:
            order: Order entity to save

        Returns:
            order_id of persisted order

        Raises:
            ValueError: If order_id already exists
        """
        with h5py.File(self.hdf5_path, "a") as f:
            # Ensure session exists
            session_group_path = f"/sessions/{order.session_id}"
            if session_group_path not in f:
                raise ValueError(f"Session {order.session_id} not found")

            # Ensure orders group exists
            orders_group_path = f"{session_group_path}/orders"
            if orders_group_path not in f:
                f.create_group(orders_group_path)

            # Check if order already exists
            order_group_path = f"{orders_group_path}/{order.order_id}"
            if order_group_path in f:
                raise ValueError(f"Order {order.order_id} already exists")

            # Create order group
            order_group = f.create_group(order_group_path)

            # Store metadata (Fix #3 - Type Safety)
            metadata = OrderMapper.to_hdf5_metadata(order)
            order_group.attrs["metadata"] = json.dumps(asdict(metadata))

        return order.order_id

    def find_by_id(self, order_id: str) -> Order | None:
        """Find order by ID.

        Args:
            order_id: Order identifier

        Returns:
            Order entity if found, None otherwise
        """
        with h5py.File(self.hdf5_path, "r") as f:
            # Search across all sessions
            if "sessions" not in f:
                return None

            for session_id in f["sessions"].keys():
                orders_group_path = f"/sessions/{session_id}/orders"
                if orders_group_path not in f:
                    continue

                order_group_path = f"{orders_group_path}/{order_id}"
                if order_group_path in f:
                    order_group = f[order_group_path]
                    metadata_json = order_group.attrs.get("metadata")

                    if metadata_json:
                        # Fix #3: Convert dict to typed OrderHDF5Metadata
                        metadata_dict = json.loads(metadata_json)
                        metadata = OrderHDF5Metadata(**metadata_dict)
                        return OrderMapper.from_hdf5(order_id, metadata)

            return None

    def find_by_session(self, session_id: str) -> list[Order]:
        """Find all orders for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of orders for the session
        """
        orders = []

        with h5py.File(self.hdf5_path, "r") as f:
            orders_group_path = f"/sessions/{session_id}/orders"

            if orders_group_path not in f:
                return []

            orders_group = f[orders_group_path]

            for order_id in orders_group.keys():
                order_group = orders_group[order_id]
                metadata_json = order_group.attrs.get("metadata")

                if metadata_json:
                    # Fix #3: Convert dict to typed OrderHDF5Metadata
                    metadata_dict = json.loads(metadata_json)
                    metadata = OrderHDF5Metadata(**metadata_dict)
                    order = OrderMapper.from_hdf5(order_id, metadata)
                    orders.append(order)

        return orders

    def find_by_status(self, status: str) -> list[Order]:
        """Find orders by status.

        Args:
            status: Order status to filter by

        Returns:
            List of orders with matching status
        """
        matching_orders = []

        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return []

            # Search across all sessions
            for session_id in f["sessions"].keys():
                orders_group_path = f"/sessions/{session_id}/orders"
                if orders_group_path not in f:
                    continue

                orders_group = f[orders_group_path]

                for order_id in orders_group.keys():
                    order_group = orders_group[order_id]
                    metadata_json = order_group.attrs.get("metadata")

                    if metadata_json:
                        # Fix #3: Convert dict to typed OrderHDF5Metadata
                        metadata_dict = json.loads(metadata_json)
                        if metadata_dict.get("status") == status:
                            metadata = OrderHDF5Metadata(**metadata_dict)
                            order = OrderMapper.from_hdf5(order_id, metadata)
                            matching_orders.append(order)

        return matching_orders

    def update(self, order: Order) -> None:
        """Update existing order.

        Args:
            order: Order entity with updated fields

        Raises:
            ValueError: If order does not exist
        """
        with h5py.File(self.hdf5_path, "a") as f:
            # Search for order across all sessions
            order_group_path = None

            if "sessions" in f:
                for session_id in f["sessions"].keys():
                    candidate_path = f"/sessions/{session_id}/orders/{order.order_id}"
                    if candidate_path in f:
                        order_group_path = candidate_path
                        break

            if not order_group_path:
                raise ValueError(f"Order {order.order_id} not found")

            order_group = f[order_group_path]

            # Update metadata
            metadata = OrderMapper.to_hdf5_metadata(order)
            order_group.attrs["metadata"] = json.dumps(metadata)

    def delete(self, order_id: str) -> bool:
        """Delete order by ID.

        Args:
            order_id: Order identifier

        Returns:
            True if order was deleted, False if not found
        """
        with h5py.File(self.hdf5_path, "a") as f:
            # Search for order across all sessions
            if "sessions" not in f:
                return False

            for session_id in f["sessions"].keys():
                order_group_path = f"/sessions/{session_id}/orders/{order_id}"
                if order_group_path in f:
                    del f[order_group_path]
                    return True

            return False

    def exists(self, order_id: str) -> bool:
        """Check if order exists.

        Args:
            order_id: Order identifier

        Returns:
            True if order exists, False otherwise
        """
        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return False

            # Search across all sessions
            for session_id in f["sessions"].keys():
                order_group_path = f"/sessions/{session_id}/orders/{order_id}"
                if order_group_path in f:
                    return True

            return False

    def count(self, session_id: str | None = None) -> int:
        """Count total number of orders.

        Args:
            session_id: Optional session ID to count orders for

        Returns:
            Total order count (for session if specified, else all)
        """
        with h5py.File(self.hdf5_path, "r") as f:
            if "sessions" not in f:
                return 0

            if session_id:
                # Count orders for specific session
                orders_group_path = f"/sessions/{session_id}/orders"
                if orders_group_path not in f:
                    return 0
                return len(f[orders_group_path].keys())
            else:
                # Count all orders across all sessions
                total = 0
                for sess_id in f["sessions"].keys():
                    orders_group_path = f"/sessions/{sess_id}/orders"
                    if orders_group_path in f:
                        total += len(f[orders_group_path].keys())
                return total
