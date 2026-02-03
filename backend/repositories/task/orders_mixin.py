"""Orders Mixin - Clinical orders storage.

Handles clinical orders:
- Create orders
- Get orders
- Update orders
- Delete orders

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Refactor from monolithic task_repository.py)
"""

from __future__ import annotations

import json
from typing import Any

import h5py

from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


class OrdersMixin:
    """Mixin for clinical orders operations.

    Requires _HDF5Base as base class (provides h5_file_path, TASKS_GROUP).
    """

    def create_order(self, session_id: str, order_data: dict[str, Any]) -> None:
        """Create order for session.

        Args:
            session_id: Session identifier
            order_data: Order dict (type, description, details, source)
        """
        try:
            orders_path = f"{self.TASKS_GROUP}/{session_id}/orders"

            with h5py.File(self.h5_file_path, "a") as f:
                # Ensure session group exists
                tasks_group = f.require_group(self.TASKS_GROUP)
                session_group = tasks_group.require_group(session_id)

                # Get or create orders list
                if "orders" in session_group:
                    orders_data = session_group["orders"][()]
                    orders_json = bytes(orders_data).decode("utf-8")
                    orders = json.loads(orders_json)
                else:
                    orders = []

                # Append new order
                orders.append(order_data)

                # Save updated orders list
                self._save_orders_dataset(session_group, orders)

                logger.info(
                    "ORDER_CREATED",
                    session_id=session_id,
                    order_type=order_data.get("type"),
                    description=order_data.get("description"),
                    total_orders=len(orders),
                )

        except Exception as e:
            logger.error(
                "CREATE_ORDER_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def get_orders(self, session_id: str) -> list[dict[str, Any]]:
        """Get orders for session.

        Args:
            session_id: Session identifier

        Returns:
            List of order dicts or empty list if none
        """
        try:
            orders_path = f"{self.TASKS_GROUP}/{session_id}/orders"

            with h5py.File(self.h5_file_path, "r") as f:
                if orders_path not in f:
                    logger.debug(
                        "ORDERS_NOT_FOUND",
                        session_id=session_id,
                    )
                    return []

                orders_data = f[orders_path][()]
                orders_json = bytes(orders_data).decode("utf-8")
                orders = json.loads(orders_json)

                logger.debug(
                    "ORDERS_READ",
                    session_id=session_id,
                    order_count=len(orders),
                )
                return orders

        except Exception as e:
            logger.error(
                "GET_ORDERS_FAILED",
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            return []

    def update_order(
        self, session_id: str, order_id: str, updated_data: dict[str, Any]
    ) -> None:
        """Update an existing order.

        Args:
            session_id: Session identifier
            order_id: Order ID to update
            updated_data: Dict with updated fields (type, description, details)

        Raises:
            ValueError: If order not found
        """
        try:
            orders_path = f"{self.TASKS_GROUP}/{session_id}/orders"

            with h5py.File(self.h5_file_path, "a") as f:
                if orders_path not in f:
                    raise ValueError(f"No orders found for session {session_id}")

                orders_data = f[orders_path][()]
                orders_json = bytes(orders_data).decode("utf-8")
                orders = json.loads(orders_json)

                # Find and update order
                order_found = False
                for order in orders:
                    if str(order.get("order_id")) == str(order_id):
                        order.update(updated_data)
                        order_found = True
                        break

                if not order_found:
                    raise ValueError(f"Order {order_id} not found in session {session_id}")

                # Save updated orders list
                session_group = f[f"{self.TASKS_GROUP}/{session_id}"]
                self._save_orders_dataset(session_group, orders)

                logger.info(
                    "ORDER_UPDATED",
                    session_id=session_id,
                    order_id=order_id,
                )

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "UPDATE_ORDER_FAILED",
                session_id=session_id,
                order_id=order_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def delete_order(self, session_id: str, order_id: str) -> None:
        """Delete an order.

        Args:
            session_id: Session identifier
            order_id: Order ID to delete

        Raises:
            ValueError: If order not found
        """
        try:
            orders_path = f"{self.TASKS_GROUP}/{session_id}/orders"

            with h5py.File(self.h5_file_path, "a") as f:
                if orders_path not in f:
                    raise ValueError(f"No orders found for session {session_id}")

                orders_data = f[orders_path][()]
                orders_json = bytes(orders_data).decode("utf-8")
                orders = json.loads(orders_json)

                # Filter out deleted order
                original_count = len(orders)
                orders = [o for o in orders if str(o.get("order_id")) != str(order_id)]

                if len(orders) == original_count:
                    raise ValueError(f"Order {order_id} not found in session {session_id}")

                # Save updated orders list
                session_group = f[f"{self.TASKS_GROUP}/{session_id}"]
                self._save_orders_dataset(session_group, orders)

                logger.info(
                    "ORDER_DELETED",
                    session_id=session_id,
                    order_id=order_id,
                    remaining_orders=len(orders),
                )

        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "DELETE_ORDER_FAILED",
                session_id=session_id,
                order_id=order_id,
                error=str(e),
                exc_info=True,
            )
            raise

    def _save_orders_dataset(self, session_group: h5py.Group, orders: list[dict[str, Any]]) -> None:
        """Save orders list to HDF5 dataset.

        Args:
            session_group: HDF5 session group
            orders: List of orders to save
        """
        orders_json = json.dumps(orders, ensure_ascii=False, indent=2)

        if "orders" in session_group:
            del session_group["orders"]

        session_group.create_dataset(
            "orders",
            data=orders_json.encode("utf-8"),
            dtype=h5py.special_dtype(vlen=bytes),
        )
