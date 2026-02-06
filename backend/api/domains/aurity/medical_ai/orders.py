"""Medical Orders Workflow Endpoints - CRUD Operations.

PUBLIC layer endpoints for medical orders management:
- GET    /orders/sessions/{session_id} - Get all orders
- POST   /orders/sessions/{session_id} - Create new order
- PUT    /orders/sessions/{session_id}/{order_id} - Update order
- DELETE /orders/sessions/{session_id}/{order_id} - Delete order

Architecture:
  PUBLIC (this file) -> REPOSITORY -> HDF5

Author: Bernard Uriza Orozco
Created: 2026-02-03 (Domain Migration from routers/order/public/orders.py)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.infrastructure.auth import User, get_current_user, validate_session_access
from backend.infrastructure.common.repository_singletons import get_task_repository
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.utils.common.logging.logger import get_logger
from backend.validators import validate_session_id

from .orders_models import OrderCreateRequest, OrderUpdateRequest

logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])


# ============================================================================
# Orders CRUD Endpoints
# ============================================================================


@router.get(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
)
async def get_orders_workflow(
    session_id: str,
    current_user: User = Depends(get_current_user),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> dict:
    """Get all medical orders for a session (PUBLIC endpoint).

    Args:
        session_id: Session UUID
        task_repo: Injected task repository

    Returns:
        List of orders with metadata

    Raises:
        500: Failed to load orders
    """
    validate_session_id(session_id)
    validate_session_access(session_id, current_user, action="view orders")

    try:
        logger.info("ORDERS_GET_STARTED", session_id=session_id)

        orders = task_repo.get_orders(session_id)

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
    "/sessions/{session_id}",
    status_code=status.HTTP_201_CREATED,
)
async def create_order_workflow(
    session_id: str,
    request: OrderCreateRequest,
    current_user: User = Depends(get_current_user),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> dict:
    """Create a new medical order (PUBLIC endpoint).

    Args:
        session_id: Session UUID
        request: Order data
        task_repo: Injected task repository

    Returns:
        Created order with ID

    Raises:
        400: Invalid order data
        500: Failed to create order
    """
    validate_session_id(session_id)
    validate_session_access(session_id, current_user, action="create orders")

    try:
        logger.info(
            "ORDER_CREATE_STARTED",
            session_id=session_id,
            order_type=request.type,
        )

        task_repo.create_order(
            session_id,
            {
                "type": request.type,
                "description": request.description,
                "details": request.details,
                "source": "manual",
            },
        )

        # create_order doesn't return ID - it appends to list
        orders = task_repo.get_orders(session_id)
        order_id = orders[-1].get("order_id", f"{session_id}_order_{len(orders)}")

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
    "/sessions/{session_id}/{order_id}",
    status_code=status.HTTP_200_OK,
)
async def update_order_workflow(
    session_id: str,
    order_id: str,
    request: OrderUpdateRequest,
    task_repo: ITaskRepository = Depends(get_task_repository),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update an existing order (PUBLIC endpoint).

    Args:
        session_id: Session UUID
        order_id: Order ID
        request: Updated order data
        task_repo: Injected task repository

    Returns:
        Success message

    Raises:
        404: Order not found
        500: Failed to update order
    """
    validate_session_id(session_id)
    validate_session_access(session_id, current_user, action="update orders")

    try:
        logger.info(
            "ORDER_UPDATE_STARTED",
            session_id=session_id,
            order_id=order_id,
        )

        task_repo.update_order(
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
        audit_service.log_action(
            action="order_updated",
            user_id=current_user.id,
            resource=f"{session_id}/{order_id}",
            result="failure",
            details={"error": str(e), "error_type": "not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        audit_service.log_action(
            action="order_updated",
            user_id=current_user.id,
            resource=f"{session_id}/{order_id}",
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order: {e!s}",
        ) from e


@router.delete(
    "/sessions/{session_id}/{order_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_order_workflow(
    session_id: str,
    order_id: str,
    task_repo: ITaskRepository = Depends(get_task_repository),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete an order (PUBLIC endpoint).

    Args:
        session_id: Session UUID
        order_id: Order ID
        task_repo: Injected task repository

    Returns:
        Success message

    Raises:
        404: Order not found
        500: Failed to delete order
    """
    validate_session_id(session_id)
    validate_session_access(session_id, current_user, action="delete orders")

    try:
        logger.info(
            "ORDER_DELETE_STARTED",
            session_id=session_id,
            order_id=order_id,
        )

        task_repo.delete_order(session_id, order_id)

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
        audit_service.log_action(
            action="order_deleted",
            user_id=current_user.id,
            resource=f"{session_id}/{order_id}",
            result="failure",
            details={"error": str(e), "error_type": "not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        audit_service.log_action(
            action="order_deleted",
            user_id=current_user.id,
            resource=f"{session_id}/{order_id}",
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete order: {e!s}",
        ) from e
