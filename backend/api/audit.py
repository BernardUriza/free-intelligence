#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Audit Logs API
Card: FI-UI-FEAT-206

Provides read-only access to audit logs with filtering and pagination.
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.audit_logs import get_audit_logs, get_audit_stats
from backend.config_loader import load_config

router = APIRouter(prefix="/api/audit")


class AuditLogEntry(BaseModel):
    """Audit log entry model"""

    audit_id: str = Field(..., description="UUID v4 for audit entry")
    timestamp: str = Field(..., description="ISO 8601 timestamp with timezone")
    operation: str = Field(..., description="Operation name (e.g., INTERACTION_APPENDED)")
    user_id: str = Field(..., description="User identifier")
    endpoint: str = Field(..., description="API endpoint or function name")
    payload_hash: str = Field(..., description="SHA256 hash of input payload")
    result_hash: str = Field(..., description="SHA256 hash of operation result")
    status: str = Field(..., description="SUCCESS, FAILED, BLOCKED")
    metadata: str = Field(..., description="JSON metadata")


class AuditLogsResponse(BaseModel):
    """Response model for audit logs list"""

    total: int
    limit: int
    logs: list[AuditLogEntry]
    operation_filter: Optional[str] = None
    user_filter: Optional[str] = None


class AuditStatsResponse(BaseModel):
    """Response model for audit stats"""

    total_logs: int
    exists: bool
    status_breakdown: dict[str, int] = Field(default_factory=dict)
    operation_breakdown: dict[str, int] = Field(default_factory=dict)


@router.get("/logs", response_model=AuditLogsResponse)
async def get_logs(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to retrieve"),
    operation: Optional[str] = Query(None, description="Filter by operation name"),
    user: Optional[str] = Query(None, description="Filter by user_id"),
):
    """
    Get audit logs with optional filtering.

    Returns logs in reverse chronological order (newest first).

    **Operation Types:**
    - LOGIN: User authenticated
    - POLICY_CHANGE: Change in fi.policy.yaml
    - VERIFY: Verification of session/interaction
    - EXPORT: Export of session
    - DELETE: Deletion of session (requires approval)
    - INTERACTION_APPENDED: New interaction added
    - SESSION_CREATED: New session created

    **Example:**
    ```
    GET /api/audit/logs?limit=50&operation=EXPORT
    ```
    """
    try:
        config = load_config()
        corpus_path = config["storage"]["corpus_path"]

        logs_data: list[dict[str, Any]] = get_audit_logs(
            corpus_path, limit=limit, operation_filter=operation, user_filter=user
        )

        # Convert dicts to AuditLogEntry objects
        logs: list[AuditLogEntry] = [AuditLogEntry(**log) for log in logs_data]

        return AuditLogsResponse(
            total=len(logs), limit=limit, logs=logs, operation_filter=operation, user_filter=user
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {str(e)}")


@router.get("/stats", response_model=AuditStatsResponse)
async def get_stats():
    """
    Get audit log statistics.

    Returns total count and breakdown by status and operation type.

    **Example:**
    ```
    GET /api/audit/stats
    ```
    """
    try:
        config = load_config()
        corpus_path = config["storage"]["corpus_path"]

        stats_data: dict[str, Any] = get_audit_stats(corpus_path)

        return AuditStatsResponse(**stats_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit stats: {str(e)}")


@router.get("/operations")
async def get_operations():
    """
    Get list of available operation types.

    Returns canonical operation types for filtering.

    **Example:**
    ```
    GET /api/audit/operations
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
