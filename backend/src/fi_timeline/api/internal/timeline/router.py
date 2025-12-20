from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import h5py
import numpy as np
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/timeline", tags=["internal-timeline"])

CORPUS_PATH = Path(__file__).parent.parent.parent.parent.parent / "storage" / "corpus.h5"


def compute_dataset_hash(ds: h5py.Dataset) -> str:
    """Compute SHA-256 hash of an HDF5 dataset.

    Args:
        ds: HDF5 dataset object

    Returns:
        SHA-256 hex digest (64 characters)
    """
    # Handle string datasets
    if h5py.check_string_dtype(ds.dtype) is not None or ds.dtype.kind in ("S", "O", "U"):
        vals = ds.asstr()[...]
        if isinstance(vals, np.ndarray):
            data = "\n".join(str(v) for v in vals.flatten())
        else:
            data = str(vals)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()
    else:
        # Numeric/binary array
        arr = ds[...]
        return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def find_target_in_h5(h5: h5py.File, target_id: str) -> tuple[str | None, h5py.Dataset | None]:
    """Find a target in HDF5 by ID.

    Target ID formats supported:
    - session_<id>: Session group (computes hash of all datasets)
    - session_<id>/path/to/dataset: Specific dataset
    - <interaction_id>: Legacy interaction format

    Args:
        h5: HDF5 file handle
        target_id: Target identifier

    Returns:
        Tuple of (resolved_path, dataset) or (None, None) if not found
    """
    # Direct path
    if target_id in h5:
        obj = h5[target_id]
        if isinstance(obj, h5py.Dataset):
            return target_id, obj
        elif isinstance(obj, h5py.Group):
            # For groups, find first dataset
            for key in obj.keys():
                if isinstance(obj[key], h5py.Dataset):
                    path = f"{target_id}/{key}"
                    return path, obj[key]
        return None, None

    # Session format: session_<id>
    if target_id.startswith("session_"):
        session_path = f"/sessions/{target_id}"
        if session_path in h5:
            grp = h5[session_path]
            if isinstance(grp, h5py.Group):
                # Find first dataset in session
                for key in grp.keys():
                    if isinstance(grp[key], h5py.Dataset):
                        path = f"{session_path}/{key}"
                        return path, grp[key]

    # Search in sessions
    if "sessions" in h5:
        sessions = h5["sessions"]
        for sess_key in sessions.keys():
            sess = sessions[sess_key]
            if isinstance(sess, h5py.Group):
                # Check if target_id matches session or interaction
                if target_id == sess_key:
                    for key in sess.keys():
                        if isinstance(sess[key], h5py.Dataset):
                            path = f"/sessions/{sess_key}/{key}"
                            return path, sess[key]

    return None, None


class VerifyItem(BaseModel):
    target_id: str = Field(...)
    expected_hash: str = Field(...)

    @field_validator("expected_hash")
    @classmethod
    def must_be_sha256(cls, v: str) -> str:
        if len(v.strip()) != 64 or any(c not in "0123456789abcdefABCDEF" for c in v.strip()):
            raise ValueError("expected_hash must be a valid 64-char hex SHA256")
        return v.strip()


class VerifyRequest(BaseModel):
    items: list[VerifyItem] = Field(..., min_length=1, max_length=100)
    verbose: bool | None = Field(False)


@router.post("/verify-hash")
async def verify_hash(request: Request):
    """Verify SHA-256 hashes of sessions/events in HDF5 corpus.

    FI-API-FEAT-003: Hash verification endpoint for data integrity.

    Request body:
        {
            "items": [
                {"target_id": "session_123", "expected_hash": "abc123..."},
                {"target_id": "/path/to/dataset", "expected_hash": "def456..."}
            ],
            "verbose": false
        }

    Response:
        {
            "timestamp": "2025-12-08T12:00:00Z",
            "all_valid": true/false,
            "items": [...],
            "summary": {"total": N, "valid": M, "invalid": K, "duration_ms": X}
        }
    """
    start = datetime.now(UTC)

    # Validate payload explicitly so Pydantic validation errors are returned
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    try:
        req = VerifyRequest.model_validate(body)
    except ValidationError as ve:
        # Convert Pydantic validation error to JSON-serializable detail
        errors = []
        for error in ve.errors():
            clean_error = {
                "type": error["type"],
                "loc": error["loc"],
                "msg": error["msg"],
                "input": error.get("input"),
            }
            errors.append(clean_error)
        raise HTTPException(status_code=422, detail=errors)

    # If corpus HDF5 not present, return error response
    if not CORPUS_PATH.exists():
        logger.warning(
            "TIMELINE_VERIFY_NO_CORPUS",
            path=str(CORPUS_PATH),
            items_count=len(req.items),
        )
        items = []
        for it in req.items:
            items.append(
                {
                    "target_id": it.target_id,
                    "valid": False,
                    "computed_hash": "",
                    "expected_hash": it.expected_hash,
                    "match": False,
                    "error": "corpus_missing",
                }
            )

        duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "all_valid": False,
            "items": items,
            "summary": {
                "total": len(items),
                "valid": 0,
                "invalid": len(items),
                "duration_ms": duration_ms,
            },
        }

    # Process verification items
    items = []
    valid_count = 0

    try:
        with h5py.File(CORPUS_PATH, "r", swmr=True) as h5:
            for it in req.items:
                resolved_path, dataset = find_target_in_h5(h5, it.target_id)

                if dataset is None:
                    # Target not found
                    items.append(
                        {
                            "target_id": it.target_id,
                            "valid": False,
                            "computed_hash": "",
                            "expected_hash": it.expected_hash,
                            "match": False,
                            "error": "target_not_found",
                        }
                    )
                    logger.debug(
                        "VERIFY_TARGET_NOT_FOUND",
                        target_id=it.target_id,
                        expected_hash_prefix=it.expected_hash[:16],
                    )
                    continue

                # Compute actual hash
                try:
                    computed_hash = compute_dataset_hash(dataset)
                    is_match = computed_hash.lower() == it.expected_hash.lower()

                    items.append(
                        {
                            "target_id": it.target_id,
                            "valid": is_match,
                            "computed_hash": computed_hash
                            if req.verbose
                            else computed_hash[:16] + "...",
                            "expected_hash": it.expected_hash,
                            "match": is_match,
                            "error": None if is_match else "hash_mismatch",
                            "resolved_path": resolved_path if req.verbose else None,
                        }
                    )

                    if is_match:
                        valid_count += 1
                        logger.info(
                            "VERIFY_HASH_MATCH",
                            target_id=it.target_id,
                            hash_prefix=computed_hash[:16],
                        )
                    else:
                        logger.warning(
                            "VERIFY_HASH_MISMATCH",
                            target_id=it.target_id,
                            computed_prefix=computed_hash[:16],
                            expected_prefix=it.expected_hash[:16],
                        )

                except Exception as e:
                    items.append(
                        {
                            "target_id": it.target_id,
                            "valid": False,
                            "computed_hash": "",
                            "expected_hash": it.expected_hash,
                            "match": False,
                            "error": f"compute_error: {str(e)[:50]}",
                        }
                    )
                    logger.error(
                        "VERIFY_HASH_COMPUTE_ERROR",
                        target_id=it.target_id,
                        error=str(e),
                    )

    except Exception as e:
        logger.error("VERIFY_HASH_H5_ERROR", error=str(e))
        raise HTTPException(status_code=500, detail=f"HDF5 read error: {str(e)[:100]}")

    duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

    # Log audit summary
    logger.info(
        "VERIFY_HASH_COMPLETE",
        total=len(items),
        valid=valid_count,
        invalid=len(items) - valid_count,
        duration_ms=duration_ms,
        verbose=req.verbose,
    )

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "all_valid": valid_count == len(items) and len(items) > 0,
        "items": items,
        "summary": {
            "total": len(items),
            "valid": valid_count,
            "invalid": len(items) - valid_count,
            "duration_ms": duration_ms,
        },
    }
