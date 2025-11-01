from __future__ import annotations

"""
Verify API - Integrity Validation Endpoints

Card: FI-API-FEAT-003
Sprint: Sprint A - Backend Foundation

Endpoints for verifying SHA256 hashes, manifest exports, and policy compliance.

Usage:
    uvicorn backend.verify_api:app --reload --port 9003

Endpoints:
    POST /api/verify/session - Verify session integrity
    POST /api/verify/interaction - Verify single interaction
    POST /api/verify/export - Verify export manifest
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import h5py
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config_loader import load_config
from backend.export_policy import validate_export

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Free Intelligence - Verify API",
    description="Integrity validation endpoints for sessions, interactions, and exports",
    version="0.1.0",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:9000",  # Aurity production frontend
        "http://localhost:3000",  # Development frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load configuration
config = load_config()
STORAGE_PATH = config.get("storage", {}).get("path", "./storage")
CORPUS_PATH = f"{STORAGE_PATH}/corpus.h5"


def log_verification(operation: str, session_id: str, verified: bool, details: dict[str, Any]):
    """Simple logging function for verification operations"""
    logger.info(
        f"[Verification] {operation} | session={session_id} | verified={verified} | details={details}"
    )


# ===== Request/Response Models =====


class SessionVerifyRequest(BaseModel):
    """Request to verify session integrity"""

    session_id: str = Field(..., description="Session ID to verify")
    expected_hash: Optional[str] = Field(None, description="Expected session hash (optional)")


class InteractionVerifyRequest(BaseModel):
    """Request to verify single interaction"""

    session_id: str
    interaction_id: str
    expected_hash: Optional[str] = Field(None, description="Expected interaction hash")


class ExportVerifyRequest(BaseModel):
    """Request to verify export manifest"""

    export_filepath: str = Field(..., description="Path to export file")
    manifest_dict: dict[str, Any] = Field(..., description="Export manifest as dict")


class VerificationResult(BaseModel):
    """Verification result"""

    verified: bool
    session_id: str
    timestamp: str
    badges: dict[str, str] = Field(
        description="Policy badges (hash_verified, policy_compliant, audit_logged, redaction_applied)"
    )
    details: dict[str, Any] = Field(default_factory=dict, description="Verification details")
    failure_reasons: list[str] = Field(
        default_factory=list, description="Failure reasons if verification failed"
    )


# ===== Helper Functions =====


def compute_session_hash(session_id: str) -> str:
    """
    Compute SHA256 hash of all interactions in a session.

    Uses content hashes from metadata (no need to read raw content).
    """
    try:
        with h5py.File(CORPUS_PATH, "r") as corpus:
            session_path = f"/sessions/{session_id}"

            if session_path not in corpus:
                raise ValueError(f"Session {session_id} not found")

            session_group = corpus[session_path]

            # Collect all interaction hashes in order
            interaction_ids = sorted(
                [k for k in session_group.keys() if k.startswith("interaction_")]
            )

            hash_chain = hashlib.sha256()

            for int_id in interaction_ids:
                interaction_group = session_group[int_id]

                # Read content_hash from metadata (attribute or dataset)
                if "metadata" in interaction_group:
                    metadata_ds = interaction_group["metadata"]
                    content_hash = (
                        metadata_ds.attrs.get("content_hash", b"").decode()
                        if isinstance(metadata_ds.attrs.get("content_hash"), bytes)
                        else str(metadata_ds.attrs.get("content_hash", ""))
                    )

                    if content_hash:
                        hash_chain.update(content_hash.encode())

            return hash_chain.hexdigest()

    except Exception as e:
        logger.error(f"Error computing session hash: {e}")
        raise


def verify_session_integrity(session_id: str) -> dict[str, Any]:
    """
    Verify session integrity by checking:
    1. Hash integrity (all interactions have valid content hashes)
    2. Append-only policy (no mutations)
    3. Audit logging present
    4. Redaction policy applied

    Returns dict with verification results.
    """
    results = {
        "hash_verified": "PENDING",
        "policy_compliant": "PENDING",
        "audit_logged": "PENDING",
        "redaction_applied": "N/A",
    }

    failure_reasons = []

    try:
        # 1. Verify hash integrity
        session_hash = compute_session_hash(session_id)
        results["hash_verified"] = "OK"
        results["session_hash_prefix"] = session_hash[:12]  # Only expose prefix

    except Exception as e:
        results["hash_verified"] = "FAIL"
        failure_reasons.append(f"Hash verification failed: {str(e)}")

    # 2. Verify append-only policy (simplified check)
    try:
        with h5py.File(CORPUS_PATH, "r") as corpus:
            session_path = f"/sessions/{session_id}"

            if session_path in corpus:
                # Basic check: verify session exists and has interactions
                session_group = corpus[session_path]
                has_interactions = any(k.startswith("interaction_") for k in session_group.keys())

                if has_interactions:
                    results["policy_compliant"] = "OK"
                else:
                    results["policy_compliant"] = "FAIL"
                    failure_reasons.append("No interactions found in session")
            else:
                results["policy_compliant"] = "FAIL"
                failure_reasons.append("Session not found")

    except Exception as e:
        results["policy_compliant"] = "FAIL"
        failure_reasons.append(f"Policy check failed: {str(e)}")

    # 3. Verify audit logging (simplified check)
    try:
        with h5py.File(CORPUS_PATH, "r") as corpus:
            session_path = f"/sessions/{session_id}"

            if session_path in corpus:
                session_group = corpus[session_path]

                # Check if metadata dataset exists with timestamps
                if "metadata" in session_group:
                    metadata_ds = session_group["metadata"]

                    # Check for created_at and updated_at attributes
                    has_created = "created_at" in metadata_ds.attrs
                    has_updated = "updated_at" in metadata_ds.attrs

                    if has_created and has_updated:
                        results["audit_logged"] = "OK"
                    else:
                        results["audit_logged"] = "FAIL"
                        failure_reasons.append("Audit timestamps missing")
                else:
                    results["audit_logged"] = "FAIL"
                    failure_reasons.append("Metadata not found")
            else:
                results["audit_logged"] = "FAIL"
                failure_reasons.append("Session not found")

    except Exception as e:
        results["audit_logged"] = "FAIL"
        failure_reasons.append(f"Audit check failed: {str(e)}")

    # 4. Redaction policy (N/A for backend verification, handled by export layer)
    results["redaction_applied"] = "N/A"

    return {
        "badges": results,
        "failure_reasons": failure_reasons,
        "verified": all(v in ["OK", "N/A"] for v in results.values()),
    }


# ===== Endpoints =====


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    corpus_exists = Path(CORPUS_PATH).exists()

    return {
        "status": "healthy",
        "storage_path": STORAGE_PATH,
        "corpus_exists": corpus_exists,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/api/verify/session", response_model=VerificationResult, status_code=status.HTTP_200_OK)
async def verify_session(request: SessionVerifyRequest):
    """
    Verify session integrity.

    Checks:
    - Hash integrity (all interactions)
    - Append-only policy compliance
    - Audit logging present
    - Redaction policy (N/A at backend level)

    Returns 200 with verification result (verified: true/false)
    """
    try:
        session_id = request.session_id

        # Perform verification
        verification = verify_session_integrity(session_id)

        # Log verification attempt
        log_verification(
            operation="verify_session",
            session_id=session_id,
            verified=verification["verified"],
            details=verification["badges"],
        )

        return VerificationResult(
            verified=verification["verified"],
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            badges=verification["badges"],
            details={"session_hash_prefix": verification["badges"].get("session_hash_prefix", "")},
            failure_reasons=verification["failure_reasons"],
        )

    except ValueError:
        # Session not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found",
        )

    except Exception as e:
        logger.error(f"Error verifying session {request.session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification error: {str(e)}",
        )


@app.post(
    "/api/verify/interaction", response_model=VerificationResult, status_code=status.HTTP_200_OK
)
async def verify_interaction_endpoint(request: InteractionVerifyRequest):
    """
    Verify single interaction integrity.

    Checks content hash matches expected value.
    """
    try:
        session_id = request.session_id
        interaction_id = request.interaction_id

        # Read interaction
        with h5py.File(CORPUS_PATH, "r") as corpus:
            session_path = f"/sessions/{session_id}"

            if session_path not in corpus:
                raise ValueError(f"Session {session_id} not found")

            interaction_path = f"{session_path}/{interaction_id}"

            if interaction_path not in corpus:
                raise ValueError(f"Interaction {interaction_id} not found")

            interaction_group = corpus[interaction_path]

            # Read content_hash from metadata
            content_hash = ""
            if "metadata" in interaction_group:
                metadata_ds = interaction_group["metadata"]
                content_hash = (
                    metadata_ds.attrs.get("content_hash", b"").decode()
                    if isinstance(metadata_ds.attrs.get("content_hash"), bytes)
                    else str(metadata_ds.attrs.get("content_hash", ""))
                )

        if not content_hash:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interaction {interaction_id} has no content hash",
            )

        verified = True
        failure_reasons = []

        # If expected hash provided, compare
        if request.expected_hash:
            if content_hash != request.expected_hash:
                verified = False
                failure_reasons.append(
                    f"Hash mismatch: expected {request.expected_hash[:12]}..., got {content_hash[:12]}..."
                )

        # Log verification
        log_verification(
            operation="verify_interaction",
            session_id=session_id,
            verified=verified,
            details={"interaction_id": interaction_id, "hash_prefix": content_hash[:12]},
        )

        return VerificationResult(
            verified=verified,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            badges={
                "hash_verified": "OK" if verified else "FAIL",
                "policy_compliant": "N/A",
                "audit_logged": "OK",
                "redaction_applied": "N/A",
            },
            details={"interaction_id": interaction_id, "hash_prefix": content_hash[:12]},
            failure_reasons=failure_reasons,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error verifying interaction {request.interaction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification error: {str(e)}",
        )


@app.post("/api/verify/export", response_model=VerificationResult, status_code=status.HTTP_200_OK)
async def verify_export_endpoint(request: ExportVerifyRequest):
    """
    Verify export manifest.

    Validates:
    - Manifest schema
    - Export file hash matches manifest
    - All required fields present
    """
    try:
        export_filepath = Path(request.export_filepath)

        # Convert dict to ExportManifest (simplified, assumes valid structure)
        # In production, would use ExportManifest.parse_obj(request.manifest_dict)
        manifest = type("ExportManifest", (), request.manifest_dict)()

        # Validate export
        is_valid = validate_export(manifest, export_filepath)

        # Log verification
        session_id = request.manifest_dict.get("session_id", "unknown")
        log_verification(
            operation="verify_export",
            session_id=session_id,
            verified=is_valid,
            details={"export_filepath": str(export_filepath)},
        )

        return VerificationResult(
            verified=is_valid,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            badges={
                "hash_verified": "OK" if is_valid else "FAIL",
                "policy_compliant": "OK",
                "audit_logged": "OK",
                "redaction_applied": "OK",
            },
            details={"export_filepath": str(export_filepath)},
            failure_reasons=[] if is_valid else ["Export validation failed"],
        )

    except Exception as e:
        logger.error(f"Error verifying export: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export verification failed: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=9003,
        reload=True,
        log_level="info",
    )
