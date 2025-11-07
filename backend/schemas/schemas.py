"""Standardized API response schemas (DTOs).

Defines consistent request/response models for all API endpoints.
Improves API consistency, documentation, and error handling.

Clean Code Principles:
- DRY: Response structures defined once, used everywhere
- Consistency: All APIs follow same response format
- Type Safety: Pydantic models with validation
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class StatusCode(str, Enum):
    """Standard status codes for all API responses."""

    SUCCESS = "success"
    ERROR = "error"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"
    INTERNAL_ERROR = "internal_error"


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper for all endpoints.

    All API endpoints should return this structure for consistency.

    Example:
        {
            "status": "success",
            "code": 200,
            "data": {...},
            "timestamp": "2025-11-01T12:00:00Z",
            "request_id": "req_123"
        }
    """

    status: StatusCode = Field(description="Response status (success, error, etc.)")
    code: int = Field(description="HTTP status code")
    data: Optional[T] = Field(default=None, description="Response payload")
    message: Optional[str] = Field(default=None, description="Status message")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")
    request_id: Optional[str] = Field(default=None, description="Request tracking ID")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ErrorDetail(BaseModel):
    """Error detail for validation errors."""

    field: str = Field(description="Field that caused error")
    error: str = Field(description="Error message")
    value: Optional[Any] = Field(default=None, description="Invalid value")


class ValidationErrorResponse(BaseModel):
    """Response for validation errors."""

    status: StatusCode = Field(default=StatusCode.VALIDATION_ERROR)
    code: int = Field(default=422)
    message: str = Field(description="Validation failed")
    errors: list[ErrorDetail] = Field(description="List of validation errors")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: Optional[str] = Field(default=None)


class PaginationMeta(BaseModel):
    """Pagination metadata for list responses."""

    total: int = Field(description="Total items in dataset")
    limit: int = Field(description="Items per page")
    offset: int = Field(description="Current offset")
    has_more: bool = Field(description="Whether more items exist")


class PaginatedResponse(BaseModel, Generic[T]):
    """Response for paginated list endpoints."""

    status: StatusCode = Field(default=StatusCode.SUCCESS)
    code: int = Field(default=200)
    data: list[T] = Field(description="List of items")
    meta: PaginationMeta = Field(description="Pagination metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: Optional[str] = Field(default=None)


# Document-related responses


class DocumentMetadata(BaseModel):
    """Document metadata."""

    source: Optional[str] = Field(default=None)
    tags: list[str] = Field(default_factory=list)
    content_length: int = Field(description="Content size in bytes")
    created_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)


class DocumentResponse(BaseModel):
    """Document data response."""

    document_id: str = Field(description="Unique document ID")
    content: str = Field(description="Document content")
    metadata: DocumentMetadata = Field(description="Document metadata")


class DocumentSummaryResponse(BaseModel):
    """Summary of document (metadata only)."""

    document_id: str = Field(description="Unique document ID")
    metadata: DocumentMetadata = Field(description="Document metadata")
    content_length: int = Field(description="Content size in bytes")


# Session-related responses


class SessionResponse(BaseModel):
    """Session data response."""

    session_id: str = Field(description="Unique session ID")
    status: str = Field(description="Session status")
    user_id: Optional[str] = Field(default=None)
    created_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)


# Audit-related responses


class AuditLogResponse(BaseModel):
    """Audit log entry response."""

    log_id: str = Field(description="Unique audit log ID")
    timestamp: str = Field(description="When action occurred")
    action: str = Field(description="Action performed")
    user_id: str = Field(description="User who performed action")
    resource: str = Field(description="Resource affected")
    result: str = Field(description="Result status")
    details: dict[str, Optional[Any]] = Field(default=None, description="Additional context")


# Helper functions for building responses


def success_response(
    data: Any = None,
    message: str = "Operation successful",
    code: int = 200,
    request_id: Optional[str] = None,
) -> APIResponse:
    """Build a success response.

    Args:
        data: Response payload
        message: Status message
        code: HTTP status code
        request_id: Optional request tracking ID

    Returns:
        APIResponse instance
    """
    return APIResponse(
        status=StatusCode.SUCCESS,
        code=code,
        data=data,
        message=message,
        request_id=request_id,
    )


def error_response(
    message: str,
    code: int = 400,
    status: StatusCode = StatusCode.ERROR,
    request_id: Optional[str] = None,
) -> APIResponse:
    """Build an error response.

    Args:
        message: Error message
        code: HTTP status code
        status: Response status code
        request_id: Optional request tracking ID

    Returns:
        APIResponse instance
    """
    return APIResponse(
        status=status,
        code=code,
        message=message,
        request_id=request_id,
    )


def validation_error_response(
    errors: list[dict[str, Any]],
    message: str = "Validation failed",
    request_id: Optional[str] = None,
) -> ValidationErrorResponse:
    """Build a validation error response.

    Args:
        errors: List of validation errors with field, error, value
        message: Error message
        request_id: Optional request tracking ID

    Returns:
        ValidationErrorResponse instance
    """
    error_details = [
        ErrorDetail(
            field=e.get("field", "unknown"),
            error=e.get("error", ""),
            value=e.get("value"),
        )
        for e in errors
    ]

    return ValidationErrorResponse(
        message=message,
        errors=error_details,
        request_id=request_id,
    )


def paginated_response(
    data: list[Any],
    total: int,
    limit: int = 20,
    offset: int = 0,
    request_id: Optional[str] = None,
) -> PaginatedResponse:
    """Build a paginated list response.

    Args:
        data: List of items
        total: Total items in dataset
        limit: Items per page
        offset: Current offset
        request_id: Optional request tracking ID

    Returns:
        PaginatedResponse instance
    """
    return PaginatedResponse(
        data=data,
        meta=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(data)) < total,
        ),
        request_id=request_id,
    )
