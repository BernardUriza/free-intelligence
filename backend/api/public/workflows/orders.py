"""Medical Orders Workflow Endpoints - CRUD Operations.

PUBLIC layer endpoints for medical orders management:
- GET /sessions/{session_id}/orders → Get all orders
- POST /sessions/{session_id}/orders → Create new order
- PUT /sessions/{session_id}/orders/{order_id} → Update order
- DELETE /sessions/{session_id}/orders/{order_id} → Delete order

Architecture:
  PUBLIC (this file) → REPOSITORY → HDF5

Author: Bernard Uriza Orozco
Created: 2025-11-15 (Refactored from monolithic router)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================


class OrderCreateRequest(BaseModel):
    """Request body for order creation."""

    type: str = Field(
        ...,
        description="Order type: medication, lab, imaging, followup",
    )
    description: str = Field(..., min_length=1, description="Order description")
    details: str = Field(default="", description="Additional details")


class OrderUpdateRequest(BaseModel):
    """Request body for order update."""

    type: str = Field(..., description="Order type")
    description: str = Field(..., min_length=1, description="Order description")
    details: str = Field(default="", description="Additional details")


# ============================================================================
# Orders CRUD Endpoints
# ============================================================================


@router.get(
    "/sessions/{session_id}/orders",
    status_code=status.HTTP_200_OK,
)
async def get_orders_workflow(session_id: str) -> dict:
    """Get all medical orders for a session (PUBLIC endpoint).

    Args:
        session_id: Session UUID

    Returns:
        List of orders with metadata

    Raises:
        500: Failed to load orders
    """
    from backend.storage.task_repository import get_orders

    try:
        logger.info("ORDERS_GET_STARTED", session_id=session_id)

        orders = get_orders(session_id)

        logger.info("ORDERS_GET_SUCCESS", session_id=session_id, order_count=len(orders))

        return {
            "session_id": session_id,
            "orders": orders,
            "order_count": len(orders),
        }

    except Exception as e:
        logger.error(
            "ORDERS_GET_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {e!s}",
        ) from e


@router.post(
    "/sessions/{session_id}/orders",
    status_code=status.HTTP_201_CREATED,
)
async def create_order_workflow(
    session_id: str,
    request: OrderCreateRequest,
) -> dict:
    """Create a new medical order (PUBLIC endpoint).

    Args:
        session_id: Session UUID
        request: Order data

    Returns:
        Created order with ID

    Raises:
        400: Invalid order data
        500: Failed to create order
    """
    from backend.storage.task_repository import create_order

    try:
        logger.info(
            "ORDER_CREATE_STARTED",
            session_id=session_id,
            order_type=request.type,
        )

        order_id = create_order(
            session_id,
            {
                "type": request.type,
                "description": request.description,
                "details": request.details,
                "source": "manual",
            },
        )

        logger.info(
            "ORDER_CREATE_SUCCESS",
            session_id=session_id,
            order_id=order_id,
        )

        return {
            "success": True,
            "session_id": session_id,
            "order_id": order_id,
        }

    except Exception as e:
        logger.error(
            "ORDER_CREATE_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {e!s}",
        ) from e


@router.put(
    "/sessions/{session_id}/orders/{order_id}",
    status_code=status.HTTP_200_OK,
)
async def update_order_workflow(
    session_id: str,
    order_id: str,
    request: OrderUpdateRequest,
) -> dict:
    """Update an existing order (PUBLIC endpoint).

    Args:
        session_id: Session UUID
        order_id: Order ID
        request: Updated order data

    Returns:
        Success message

    Raises:
        404: Order not found
        500: Failed to update order
    """
    from backend.storage.task_repository import update_order

    try:
        logger.info(
            "ORDER_UPDATE_STARTED",
            session_id=session_id,
            order_id=order_id,
        )

        update_order(
            session_id,
            order_id,
            {
                "type": request.type,
                "description": request.description,
                "details": request.details,
            },
        )

        logger.info(
            "ORDER_UPDATE_SUCCESS",
            session_id=session_id,
            order_id=order_id,
        )

        return {
            "success": True,
            "session_id": session_id,
            "order_id": order_id,
        }

    except ValueError as e:
        logger.error("ORDER_NOT_FOUND", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "ORDER_UPDATE_FAILED",
            session_id=session_id,
            order_id=order_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order: {e!s}",
        ) from e


@router.delete(
    "/sessions/{session_id}/orders/{order_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_order_workflow(
    session_id: str,
    order_id: str,
) -> dict:
    """Delete an order (PUBLIC endpoint).

    Args:
        session_id: Session UUID
        order_id: Order ID

    Returns:
        Success message

    Raises:
        404: Order not found
        500: Failed to delete order
    """
    from backend.storage.task_repository import delete_order

    try:
        logger.info(
            "ORDER_DELETE_STARTED",
            session_id=session_id,
            order_id=order_id,
        )

        delete_order(session_id, order_id)

        logger.info(
            "ORDER_DELETE_SUCCESS",
            session_id=session_id,
            order_id=order_id,
        )

        return {
            "success": True,
            "session_id": session_id,
            "order_id": order_id,
        }

    except ValueError as e:
        logger.error("ORDER_NOT_FOUND", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "ORDER_DELETE_FAILED",
            session_id=session_id,
            order_id=order_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete order: {e!s}",
        ) from e
