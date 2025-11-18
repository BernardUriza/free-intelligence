"""Public Audit API Router (Read-Only).

Public read-only access to audit logs for HIPAA compliance.
Card: FI-UI-FEAT-206

Architecture:
- PUBLIC layer (this file) - Read-only orchestrator
- Uses AuditService from DI container
- CORS enabled for frontend access

Event Types:
- LOGIN: User authenticated
- POLICY_CHANGE: Change in fi.policy.yaml
- VERIFY: Verification of session/interaction
- EXPORT: Export of session
- DELETE: Deletion of session (requires approval)
- INTERACTION_APPENDED: New interaction added
- SESSION_CREATED: New session created

File: backend/api/public/audit.py
Created: 2025-11-17
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.container import get_container
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class AuditLogEntry(BaseModel):
    """Audit log entry model."""

    audit_id: str = Field(..., description="UUID v4 for audit entry")
    timestamp: str = Field(..., description="ISO 8601 timestamp with timezone")
    operation: str = Field(..., description="Operation name (e.g., LOGIN, EXPORT)")
    user_id: str = Field(..., description="User identifier")
    endpoint: str = Field(..., description="API endpoint or function name")
    payload_hash: str = Field(..., description="SHA256 hash of input payload")
    result_hash: str = Field(..., description="SHA256 hash of operation result")
    status: str = Field(..., description="SUCCESS, FAILED, BLOCKED")
    metadata: str = Field(..., description="JSON metadata")


class AuditLogsResponse(BaseModel):
    """Response model for audit logs list."""

    total: int
    limit: int
    logs: list[AuditLogEntry]
    operation_filter: Optional[str] = None
    user_filter: Optional[str] = None


class AuditStatsResponse(BaseModel):
    """Response model for audit stats."""

    total_logs: int
    exists: bool
    status_breakdown: dict[str, int] = Field(default_factory=dict)
    operation_breakdown: dict[str, int] = Field(default_factory=dict)


@router.get("/logs", response_model=AuditLogsResponse, tags=["Audit"])
async def get_audit_logs(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to retrieve"),
    operation: Optional[str] = Query(None, description="Filter by operation name"),
    user: Optional[str] = Query(None, description="Filter by user_id"),
):
    """
    Get audit logs with optional filtering (read-only).

    **Public Endpoint** - CORS enabled for frontend access.

    Returns logs in reverse chronological order (newest first).

    **Operation Types:**
    - LOGIN: User authenticated
    - POLICY_CHANGE: Change in fi.policy.yaml
    - VERIFY: Verification of session/interaction
    - EXPORT: Export of session
    - DELETE: Deletion of session (requires approval)
    - INTERACTION_APPENDED: New interaction added
    - SESSION_CREATED: New session created

    **Filtering:**
    - `operation`: Filter by specific operation type
    - `user`: Filter by user_id
    - `limit`: Number of logs to return (1-1000, default 100)

    **Example:**
    ```
    GET /api/audit/logs?limit=50&operation=LOGIN
    GET /api/audit/logs?user=admin&limit=200
    ```

    **Frontend Usage:**
    ```typescript
    const response = await fetch('/api/audit/logs?limit=100&operation=EXPORT');
    const data = await response.json();
    console.log(data.logs); // Array of AuditLogEntry
    ```
    """
    try:
        # Get audit service from DI container
        audit_service = get_container().get_audit_service()

        # Delegate to service for log retrieval with filtering
        # AuditService.get_logs() method signature: get_logs(limit, action, user_id, resource)
        logs_data = audit_service.get_logs(
            limit=limit,
            action=operation,
            user_id=user,
        )

        # Transform internal schema to public API schema
        logs: list[AuditLogEntry] = []
        for log_data in logs_data:
            if not log_data:
                continue

            # Map internal fields to public API fields
            try:
                public_log = AuditLogEntry(
                    audit_id=log_data.get("log_id", ""),
                    timestamp=log_data.get("timestamp", ""),
                    operation=log_data.get("action", ""),
                    user_id=log_data.get("user_id", ""),
                    endpoint=log_data.get("resource", ""),
                    payload_hash="",  # Not stored in simple schema
                    result_hash="",   # Not stored in simple schema
                    status=log_data.get("result", "").upper(),  # SUCCESS/FAILED
                    metadata=str(log_data.get("details", {})),
                )
                logs.append(public_log)
            except Exception as validation_error:
                logger.warning("AUDIT_LOG_TRANSFORM_FAILED", error=str(validation_error), log_data=log_data)
                continue

        logger.info(
            "AUDIT_LOGS_RETRIEVED",
            total=len(logs),
            operation_filter=operation,
            user_filter=user,
        )

        return AuditLogsResponse(
            total=len(logs),
            limit=limit,
            logs=logs,
            operation_filter=operation,
            user_filter=user,
        )

    except Exception as e:
        logger.error("GET_AUDIT_LOGS_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {e!s}")


@router.get("/stats", response_model=AuditStatsResponse, tags=["Audit"])
async def get_audit_stats():
    """
    Get audit log statistics (read-only).

    **Public Endpoint** - CORS enabled for frontend access.

    Returns total count and breakdown by status and operation type.

    **Example:**
    ```
    GET /api/audit/stats
    ```

    **Response:**
    ```json
    {
      "total_logs": 150,
      "exists": true,
      "status_breakdown": {
        "SUCCESS": 145,
        "FAILED": 5
      },
      "operation_breakdown": {
        "LOGIN": 10,
        "EXPORT": 25,
        "SESSION_CREATED": 115
      }
    }
    ```
    """
    try:
        # Get audit service from DI container
        audit_service = get_container().get_audit_service()

        # Get all logs for aggregation (limit to reasonable number for stats)
        all_logs = audit_service.get_logs(limit=10000)

        # Calculate statistics
        total_logs = len(all_logs)
        exists = total_logs > 0

        # Aggregate by status
        status_breakdown: dict[str, int] = {}
        operation_breakdown: dict[str, int] = {}

        for log in all_logs:
            # Count by status
            status = log.get("status", "UNKNOWN")
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

            # Count by operation
            operation = log.get("operation", "UNKNOWN")
            operation_breakdown[operation] = operation_breakdown.get(operation, 0) + 1

        logger.info("AUDIT_STATS_RETRIEVED", total_logs=total_logs)

        return AuditStatsResponse(
            total_logs=total_logs,
            exists=exists,
            status_breakdown=status_breakdown,
            operation_breakdown=operation_breakdown,
        )

    except Exception as e:
        logger.error("GET_AUDIT_STATS_FAILED", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit stats: {e!s}")


@router.get("/operations", tags=["Audit"])
async def get_operation_types():
    """
    Get list of available operation types for filtering.

    **Public Endpoint** - CORS enabled for frontend access.

    Returns canonical operation types with labels and colors for UI rendering.

    **Example:**
    ```
    GET /api/audit/operations
    ```

    **Response:**
    ```json
    {
      "operations": [
        {"value": "LOGIN", "label": "Login", "color": "green"},
        {"value": "EXPORT", "label": "Export", "color": "purple"}
      ]
    }
    ```

    **Frontend Usage:**
    ```typescript
    const { operations } = await fetch('/api/audit/operations').then(r => r.json());
    // Render dropdown with operations
    operations.forEach(op => {
      console.log(`${op.label} (${op.value})`);
    });
    ```
    """
    return {
        "operations": [
            {"value": "LOGIN", "label": "Login", "color": "green"},
            {"value": "POLICY_CHANGE", "label": "Policy Change", "color": "yellow"},
            {"value": "VERIFY", "label": "Verify", "color": "blue"},
            {"value": "EXPORT", "label": "Export", "color": "purple"},
            {"value": "DELETE", "label": "Delete", "color": "red"},
            {"value": "INTERACTION_APPENDED", "label": "Interaction Added", "color": "gray"},
            {"value": "SESSION_CREATED", "label": "Session Created", "color": "gray"},
        ]
    }
