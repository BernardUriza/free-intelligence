"""Exception Handler - Map exceptions to HTTP responses.

Provides consistent error handling across all API endpoints.

Usage:
    from backend.utils.exception_handler import handle_exception
    from backend.exceptions import SessionNotFoundError

    try:
        session = get_session(session_id)
    except SessionNotFoundError as e:
        return handle_exception(e)

Created: 2025-01-XX
Author: Claude Code (P1 Architectural Fix)
"""

from __future__ import annotations

from backend.exceptions import FIException
from backend.utils.common.logging.logger import get_logger
from fastapi import HTTPException, status

logger = get_logger(__name__)


def handle_exception(
    exc: Exception,
    default_message: str = "An error occurred",
    log_error: bool = True,
) -> HTTPException | dict:
    """Handle exception and return appropriate HTTP response.

    Maps domain exceptions to HTTP status codes and standardized responses.

    Args:
        exc: Exception to handle
        default_message: Default message if exception doesn't have one
        log_error: Whether to log the error

    Returns:
        HTTPException for FastAPI to raise, or dict for direct return

    Example:
        try:
            result = operation()
        except SessionNotFoundError as e:
            raise handle_exception(e)  # Returns HTTPException(404)
    """
    # Handle FIException hierarchy
    if isinstance(exc, FIException):
        if log_error:
            logger.error(
                "FI_EXCEPTION_RAISED",
                exception_type=exc.__class__.__name__,
                message=exc.message,
                context=exc.context,
                status_code=exc.status_code,
            )

        # Return HTTPException for FastAPI
        return HTTPException(
            status_code=exc.status_code,
            detail={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "context": exc.context,
            },
        )

    # Handle standard Python exceptions
    if isinstance(exc, ValueError):
        if log_error:
            logger.warning("VALIDATION_ERROR", error=str(exc))
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "ValidationError", "message": str(exc)},
        )

    if isinstance(exc, KeyError):
        if log_error:
            logger.warning("NOT_FOUND", error=str(exc))
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NotFound", "message": f"Resource not found: {exc}"},
        )

    if isinstance(exc, PermissionError):
        if log_error:
            logger.warning("PERMISSION_DENIED", error=str(exc))
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "PermissionDenied", "message": str(exc)},
        )

    # Generic exception
    if log_error:
        logger.error(
            "UNHANDLED_EXCEPTION",
            exception_type=exc.__class__.__name__,
            error=str(exc),
            exc_info=True,
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"error": "InternalError", "message": default_message},
    )
