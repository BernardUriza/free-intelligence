"""Endpoint handlers for timeline verify API.

Implements the FastAPI endpoint functions for hash verification.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from backend.audit_logs import append_audit_log

from .config import CORPUS_PATH, logger
from .models import VerifyHashDetail, VerifyHashRequest, VerifyHashResponse
from .utils import build_summary, compute_hash_for_target, get_hash_prefix


async def verify_hash(request: VerifyHashRequest) -> VerifyHashResponse:
    """Verify SHA256 hashes for sessions or events.

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

    Args:
        request: Batch verification request with items and verbose flag

    Returns:
        Verification response with results and summary
    """
    start_time = time.time()
    timestamp = datetime.now(timezone.utc).isoformat()

    results: list[VerifyHashDetail] = []
    valid_count = 0
    invalid_count = 0

    # Process each hash verification
    for item in request.items:
        computed_hash, error = compute_hash_for_target(item.target_id)
        is_match = False  # Initialize to ensure it's always defined

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
        log_hash_prefix = get_hash_prefix(computed_hash)
        match_result = is_match if not error else False
        try:
            append_audit_log(
                corpus_path=CORPUS_PATH,
                operation="TIMELINE_HASH_VERIFIED",
                user_id=item.target_id,
                endpoint="/api/timeline/verify-hash",
                payload={
                    "target_id": item.target_id,
                    "hash_prefix": get_hash_prefix(item.expected_hash),
                },
                result={"match": match_result, "computed_prefix": log_hash_prefix},
                status="SUCCESS" if match_result else "FAILED",
                metadata={"verbose": request.verbose},
            )
        except Exception as e:
            logger.warning("Failed to log verification for %s: %s", item.target_id, str(e))

    duration_ms = int((time.time() - start_time) * 1000)
    all_valid = valid_count == len(request.items)

    return VerifyHashResponse(
        timestamp=timestamp,
        all_valid=all_valid,
        items=results,
        summary=build_summary(
            total=len(request.items),
            valid_count=valid_count,
            invalid_count=invalid_count,
            duration_ms=duration_ms,
        ),
    )
