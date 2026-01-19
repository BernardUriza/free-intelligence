"""Medical orders CRUD operations for HDF5.

Provides CRUD operations for medical orders within session-level HDF5 files.
Medical orders include prescriptions, lab requests, imaging orders, referrals,
and other clinical directives generated during consultations.

Storage schema:
  /sessions/{session_id}/tasks/ORDERS/
    └── orders/                # Order records
        ├── order_YYYYMMDD_HHMMSS_FFFFFF
        └── ...

Author: Bernard Uriza Orozco
Created: 2025-11-14
Refactored: 2026-01-18 (modularization)
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from backend.models.task_type import TaskType
from backend.src.fi_common.logging.logger import get_logger
from backend.src.fi_storage.infrastructure.hdf5.session_h5_manager import (
    CORPUS_PATH,
)
from backend.src.fi_storage.infrastructure.hdf5.session_locks import locked_session_h5
from backend.src.fi_storage.infrastructure.hdf5.tasks.h5_file_access import (
    _h5_lock,
    open_h5_read,
)

__all__ = [
    "create_order",
    "get_orders",
    "update_order",
    "delete_order",
]

logger = get_logger(__name__)


def create_order(
    session_id: str,
    order: dict[str, Any],
    task_type: TaskType = TaskType.ORDERS,
) -> str:
    """Create a new medical order.

    Args:
        session_id: Session identifier
        order: Order data {type, description, details}
        task_type: Task type (default ORDERS)

    Returns:
        Order ID
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    order_id = f"order_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}"

    with _h5_lock, locked_session_h5(session_id, mode="a") as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        # Create task if doesn't exist
        if task_path not in f:  # type: ignore[operator]
            f.create_group(task_path)  # type: ignore[union-attr]

            task_group = f[task_path]  # type: ignore[index]

            # Create orders group if doesn't exist
            if "orders" not in task_group:  # type: ignore[operator]
                task_group.create_group("orders")  # type: ignore[union-attr]

            orders_group = task_group["orders"]  # type: ignore[index]

            # Save order as JSON
            order_data = {
                "id": order_id,
                "created_at": datetime.now(UTC).isoformat(),
                **order,
            }
            order_json = json.dumps(order_data)
            orders_group.create_dataset(order_id, data=order_json.encode("utf-8"))  # type: ignore[union-attr]

            logger.info(
                "ORDER_CREATED",
                session_id=session_id,
                order_id=order_id,
                order_type=order.get("type"),
            )

    return order_id


def get_orders(
    session_id: str,
    task_type: TaskType = TaskType.ORDERS,
) -> list[dict[str, Any]]:
    """Get all orders for a session.

    Args:
        session_id: Session identifier
        task_type: Task type (default ORDERS)

    Returns:
        List of order dictionaries
    """
    if not CORPUS_PATH.exists():
        raise ValueError(f"Corpus file not found: {CORPUS_PATH}")

    with open_h5_read() as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            # No orders task yet, return empty list
            return []

        task_group = f[task_path]  # type: ignore[index]

        if "orders" not in task_group:  # type: ignore[operator]
            return []

        orders_group = task_group["orders"]  # type: ignore[index]
        orders = []

        for order_key in orders_group:
            order_json = orders_group[order_key][()].decode("utf-8")  # type: ignore[index]
            order_data = json.loads(order_json)
            orders.append(order_data)

    logger.info(
        "ORDERS_LOADED",
        session_id=session_id,
        order_count=len(orders),
    )

    return orders


def update_order(
    session_id: str,
    order_id: str,
    order: dict[str, Any],
    task_type: TaskType = TaskType.ORDERS,
) -> None:
    """Update an existing order.

    Args:
        session_id: Session identifier
        order_id: Order ID
        order: Updated order data
        task_type: Task type (default ORDERS)

    Raises:
        ValueError: If order not found
    """
    with _h5_lock, locked_session_h5(session_id, mode="a") as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"No orders found for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        if "orders" not in task_group:  # type: ignore[operator]
            raise ValueError(f"No orders found for session {session_id}")

        orders_group = task_group["orders"]  # type: ignore[index]

        if order_id not in orders_group:  # type: ignore[operator]
            raise ValueError(f"Order {order_id} not found")

        # Update order
        order_data = {
            "id": order_id,
            "updated_at": datetime.now(UTC).isoformat(),
            **order,
        }
        order_json = json.dumps(order_data)

        # Delete and recreate (HDF5 doesn't support in-place update)
        del orders_group[order_id]  # type: ignore[index]
        orders_group.create_dataset(order_id, data=order_json.encode("utf-8"))  # type: ignore[union-attr]

        logger.info(
            "ORDER_UPDATED",
            session_id=session_id,
            order_id=order_id,
        )


def delete_order(
    session_id: str,
    order_id: str,
    task_type: TaskType = TaskType.ORDERS,
) -> None:
    """Delete an order.

    P0 ARCHITECTURE FIX: Uses session-level HDF5 files.

    WARNING: Contains del operation violating append-only pattern.

    Args:
        session_id: Session identifier
        order_id: Order ID
        task_type: Task type (default ORDERS)

    Raises:
        ValueError: If order not found
    """
    with locked_session_h5(session_id, mode="a") as f:
        task_path = f"/sessions/{session_id}/tasks/{task_type.value}"

        if task_path not in f:  # type: ignore[operator]
            raise ValueError(f"No orders found for session {session_id}")

        task_group = f[task_path]  # type: ignore[index]

        if "orders" not in task_group:  # type: ignore[operator]
            raise ValueError(f"No orders found for session {session_id}")

        orders_group = task_group["orders"]  # type: ignore[index]

        if order_id not in orders_group:  # type: ignore[operator]
            raise ValueError(f"Order {order_id} not found")

        del orders_group[order_id]  # type: ignore[index] # VIOLATION: append-only

        logger.info(
            "ORDER_DELETED",
            session_id=session_id,
            order_id=order_id,
        )
