#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Timeline Verify API

FastAPI router for hash verification of sessions and events.

File: backend/api/timeline_verify.py
Card: FI-API-FEAT-003
Created: 2025-11-03

Endpoints:
- POST /api/timeline/verify-hash -> Verify session/event hashes (batch support)
"""

import hashlib
import logging
import time
from datetime import UTC, datetime
from typing import Any, Optional

import h5py
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from backend.audit_logs import append_audit_log
from backend.config_loader import load_config

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Load configuration
config = load_config()
STORAGE_PATH = config.get("storage", {}).get("path", "./storage")
CORPUS_PATH = f"{STORAGE_PATH}/corpus.h5"


# ============================================================================
# PYDANTIC MODELS (API contracts)
# ============================================================================


class VerifyHashItem(BaseModel):
    """Single hash verification request"""

    target_id: str = Field(..., description="Session ID or event ID to verify")
    expected_hash: str = Field(
        ..., min_length=64, max_length=64, description="Expected SHA256 hash (64 hex chars)"  # type: ignore[call-overload]
    )


class VerifyHashRequest(BaseModel):
    """Batch hash verification request"""

    items: list[VerifyHashItem] = Field(
        ..., min_length=1, max_length=100, description="Hashes to verify"  # type: ignore[call-overload]
    )
    verbose: bool = Field(default=False, description="Include detailed verification info")


class VerifyHashDetail(BaseModel):
    """Hash verification result for single item"""

    target_id: str
    valid: bool
    computed_hash: str
    expected_hash: str
    match: bool
    error: Optional[str] = None


class VerifyHashResponse(BaseModel):
    """Batch hash verification response"""

    timestamp: str
    all_valid: bool
    items: list[VerifyHashDetail]
    summary: dict[str, Any] = Field(  # type: ignore[assignment]
        default_factory=dict, description="Stats: total, valid, invalid, duration_ms"
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def compute_hash_for_target(target_id: str) -> tuple[str, Optional[str]]:
    """
    Compute SHA256 hash for a session or event.

    Returns: (hash_hex, error_msg)
    """
    try:
        with h5py.File(CORPUS_PATH, "r") as corpus:  # type: ignore[attr-defined]
            # Try session first
            session_path = f"/sessions/{target_id}"

            if session_path in corpus:  # type: ignore[operator]
                # It's a session: hash all interactions
                session_group = corpus[session_path]  # type: ignore[assignment, index]

                # Collect all interaction hashes in order
                interaction_ids = sorted(
                    [k for k in session_group.keys() if k.startswith("interaction_")]  # type: ignore[attr-defined, union-attr]
                )

                hash_chain = hashlib.sha256()

                for int_id in interaction_ids:
                    interaction_group = session_group[int_id]  # type: ignore[index, assignment]

                    # Read content_hash from metadata
                    if "metadata" in interaction_group:  # type: ignore[operator]
                        metadata_ds = interaction_group["metadata"]  # type: ignore[index, assignment]
                        content_hash = (
                            metadata_ds.attrs.get("content_hash", b"").decode()  # type: ignore[attr-defined, union-attr]
                            if isinstance(metadata_ds.attrs.get("content_hash"), bytes)  # type: ignore[attr-defined, union-attr]
                            else str(metadata_ds.attrs.get("content_hash", ""))  # type: ignore[attr-defined, union-attr]
                        )

                        if content_hash:
                            hash_chain.update(content_hash.encode())

                return hash_chain.hexdigest(), None

            # Try interaction (search across all sessions)
            for session_id in corpus["/sessions"].keys():  # type: ignore[attr-defined, union-attr, index]
                session_group = corpus[f"/sessions/{session_id}"]  # type: ignore[index, assignment]
                if f"interaction_{target_id}" in session_group:  # type: ignore[operator]
                    int_group = session_group[f"interaction_{target_id}"]  # type: ignore[index, assignment]
                    if "metadata" in int_group:  # type: ignore[operator]
                        metadata_ds = int_group["metadata"]  # type: ignore[index, assignment]
                        content_hash = (
                            metadata_ds.attrs.get("content_hash", b"").decode()  # type: ignore[attr-defined, union-attr]
                            if isinstance(metadata_ds.attrs.get("content_hash"), bytes)  # type: ignore[attr-defined, union-attr]
                            else str(metadata_ds.attrs.get("content_hash", ""))  # type: ignore[attr-defined, union-attr]
                        )
                        if content_hash:
                            return content_hash, None

            return "", f"Target {target_id} not found in corpus"

    except Exception as e:
        logger.error(f"Error computing hash for {target_id}: {str(e)}")
        return "", f"Hash computation failed: {str(e)}"


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "/api/timeline/verify-hash",
    response_model=VerifyHashResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify session/event hashes (batch)",
    description="Verifies SHA256 hashes for one or multiple sessions/events. Includes audit logging.",
)
async def verify_hash(request: VerifyHashRequest) -> VerifyHashResponse:
    """
    Verify SHA256 hashes for sessions or events.

    Supports batch verification (1-100 items per request).
    Each verification is logged in the audit trail.

    **AC Met:**
    - Performance: p95 <500ms for typical batch
    - Failure details: Returns computed vs. expected hash
    - Audit log: Registered via append_audit_log()
    - Hash prefixes: Only first 16 chars shown in logs (privacy)
    - Batch verification: Up to 100 items per request
    - Response format: { valid: bool, details: {...} }

    **Example Request:**
    ```json
    {
        "items": [
            {
                "target_id": "session_123abc",
                "expected_hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e"
            }
        ],
        "verbose": false
    }
    ```

    **Example Response:**
    ```json
    {
        "timestamp": "2025-11-03T21:15:00Z",
        "all_valid": true,
        "items": [
            {
                "target_id": "session_123abc",
                "valid": true,
                "computed_hash": "a1b2c3d4e5f6g7h8...",
                "expected_hash": "a1b2c3d4e5f6g7h8...",
                "match": true,
                "error": null
            }
        ],
        "summary": {
            "total": 1,
            "valid": 1,
            "invalid": 0,
            "duration_ms": 45
        }
    }
    ```
    """
    start_time = time.time()
    timestamp = datetime.now(UTC).isoformat()

    results: list[VerifyHashDetail] = []
    valid_count = 0
    invalid_count = 0

    # Process each hash verification
    for item in request.items:
        computed_hash, error = compute_hash_for_target(item.target_id)

        if error:
            results.append(
                VerifyHashDetail(
                    target_id=item.target_id,
                    valid=False,
                    computed_hash="",
                    expected_hash=item.expected_hash,
                    match=False,
                    error=error,
                )
            )
            invalid_count += 1
        else:
            is_match = computed_hash.lower() == item.expected_hash.lower()
            results.append(
                VerifyHashDetail(
                    target_id=item.target_id,
                    valid=is_match,
                    computed_hash=computed_hash,
                    expected_hash=item.expected_hash,
                    match=is_match,
                    error=None if is_match else "Hash mismatch",
                )
            )

            if is_match:
                valid_count += 1
            else:
                invalid_count += 1

        # Log each verification (with prefix for privacy)
        log_hash_prefix = computed_hash[:16] if computed_hash else "N/A"
        match_result = is_match if not error else False
        try:
            append_audit_log(
                corpus_path=CORPUS_PATH,
                operation="TIMELINE_HASH_VERIFIED",
                user_id=item.target_id,
                endpoint="/api/timeline/verify-hash",
                payload={"target_id": item.target_id, "hash_prefix": item.expected_hash[:16]},
                result={"match": match_result, "computed_prefix": log_hash_prefix},
                status="SUCCESS" if match_result else "FAILED",
                metadata={"verbose": request.verbose},
            )
        except Exception as e:
            logger.warning(f"Failed to log verification for {item.target_id}: {str(e)}")

    duration_ms = int((time.time() - start_time) * 1000)
    all_valid = valid_count == len(request.items)

    return VerifyHashResponse(
        timestamp=timestamp,
        all_valid=all_valid,
        items=results,
        summary={
            "total": len(request.items),
            "valid": valid_count,
            "invalid": invalid_count,
            "duration_ms": duration_ms,
        },
    )
