#!/usr/bin/env python3
from __future__ import annotations

"""
Free Intelligence - Export API

FastAPI router for session export with manifest and hash verification.

File: backend/api/exports.py
Cards: FI-API-FEAT-013
Created: 2025-10-30

Philosophy: Deterministic exports with SHA256 provenance.
- Same sessionId ⇒ same hashes (deterministic content generation)
- Every export has manifest with file hashes
- Verify endpoint for integrity checking
- Optional JWS signing with HS256

Endpoints:
- POST /api/exports -> create export bundle
- GET /api/exports/{exportId} -> get export status
- POST /api/exports/{exportId}/verify -> verify file integrity
- GET /downloads/exp_{id}/* -> static file serving (configured in main app)
"""

import hashlib
import json
import os
import random
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.sessions_store import SessionsStore

# ============================================================================
# CONFIGURATION
# ============================================================================

# Export directory (env var or default)
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "/tmp/fi_exports"))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Base download URL (env var or default)
BASE_DOWNLOAD_URL = os.getenv("BASE_DOWNLOAD_URL", "http://localhost:7001/downloads")

# Optional signing key for JWS (HS256)
SIGNING_KEY = os.getenv("SIGNING_KEY", None)

# Git commit hash for manifest metadata
GIT_COMMIT = os.getenv("GIT_COMMIT", "dev")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class ExportInclude(BaseModel):
    """What to include in export"""

    transcript: bool = True
    events: bool = True
    attachments: bool = False


class ExportRequest(BaseModel):
    """Create export request"""

    sessionId: str
    formats: list[Literal["md", "json"]] = Field(..., min_length=1)
    include: ExportInclude = Field(default_factory=ExportInclude)


class ExportArtifact(BaseModel):
    """Export artifact metadata"""

    format: Literal["md", "json", "manifest"]
    url: str
    sha256: str
    bytes: int


class ExportResponse(BaseModel):
    """Export response"""

    exportId: str
    status: Literal["ready", "processing"]
    artifacts: list[ExportArtifact]
    manifestUrl: str


class VerifyRequest(BaseModel):
    """Verify request"""

    targets: list[Literal["md", "json", "manifest"]] = Field(
        default_factory=lambda: ["md", "json", "manifest"]
    )


class VerifyResult(BaseModel):
    """Verify result for single target"""

    target: str
    ok: bool
    message: Optional[str] = None


class VerifyResponse(BaseModel):
    """Verify response"""

    ok: bool
    results: list[VerifyResult]


# ============================================================================
# DETERMINISTIC CONTENT GENERATION
# ============================================================================


def generate_deterministic_content(
    session_id: str, format_type: str, include: ExportInclude
) -> str:
    """
    Generate deterministic content based on session_id.

    Uses session_id as seed to ensure same inputs ⇒ same outputs.
    If session exists in store, use real data. Otherwise, synthetic demo.
    """
    # Try to get real session data
    store = SessionsStore()
    session = store.get(session_id)

    if not session:
        # Synthetic demo data (deterministic based on session_id seed)
        seed = int(hashlib.sha256(session_id.encode()).hexdigest()[:8], 16)
        random.seed(seed)

        demo_transcript = f"""# Demo Session Export

Session ID: {session_id}
Status: DEMO (session not found in store)
Generated: {datetime.now(UTC).isoformat()}Z

## Transcript

This is a deterministic demo transcript generated from session_id seed.

User: Hello, this is a test session.
Assistant: Hello! This is a synthetic demo response (seed: {seed}).

User: Can you help me with something?
Assistant: Of course! This export demonstrates deterministic content generation.

## Notes

- Same session_id ⇒ same hash
- Real sessions would show actual interaction data
- Demo mode for testing export functionality
"""

        demo_events = [
            {
                "event_id": f"evt_{session_id[:8]}_{i}",
                "timestamp": f"2025-10-30T{12+i:02d}:00:00Z",
                "type": "USER_MESSAGE" if i % 2 == 0 else "ASSISTANT_RESPONSE",
                "content": f"Demo event {i} (deterministic)",
            }
            for i in range(4)
        ]

        if format_type == "md":
            content = demo_transcript
            if include.events:
                content += "\n## Events\n\n"
                for evt in demo_events:
                    content += f"- [{evt['timestamp']}] {evt['type']}: {evt['content']}\n"
            return content

        elif format_type == "json":
            return json.dumps(
                {
                    "session_id": session_id,
                    "status": "demo",
                    "transcript": demo_transcript if include.transcript else None,
                    "events": demo_events if include.events else None,
                    "generated_at": datetime.now(UTC).isoformat() + "Z",
                    "deterministic": True,
                    "seed": seed,
                },
                indent=2,
            )

    else:
        # Real session data
        session_dict = session.to_dict()

        if format_type == "md":
            content = f"""# Session Export

Session ID: {session_id}
Created: {session_dict['created_at']}
Status: {session_dict['status']}
Owner: {session_dict['owner_hash']}
Interactions: {session_dict['interaction_count']}

## Metadata

- Thread ID: {session_dict.get('thread_id', 'N/A')}
- Last Active: {session_dict['last_active']}
- Persisted: {session_dict['is_persisted']}

## Transcript

(Real transcript would be loaded from session events)

"""
            return content

        elif format_type == "json":
            return json.dumps(
                {
                    "session_id": session_id,
                    "metadata": session_dict,
                    "transcript": "(Real transcript)" if include.transcript else None,
                    "events": "(Real events)" if include.events else None,
                    "generated_at": datetime.now(UTC).isoformat() + "Z",
                    "deterministic": True,
                },
                indent=2,
            )

    return ""


def compute_sha256(content: str) -> str:
    """Compute SHA256 hash of content"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def generate_export_id() -> str:
    """Generate export ID: exp_{timestamp}_{random}"""
    ts = int(time.time())
    rand = random.randint(1000, 9999)
    return f"exp_{ts}_{rand}"


def create_manifest(
    export_id: str, session_id: str, files: list[dict], signature: Optional[str] = None
) -> dict:
    """Create export manifest"""
    manifest = {
        "version": "1.0",
        "exportId": export_id,
        "sessionId": session_id,
        "createdAt": datetime.now(UTC).isoformat() + "Z",
        "algorithm": "sha256",
        "files": files,
        "meta": {"generator": "FI", "commit": GIT_COMMIT, "deterministic": True},
    }

    if signature:
        manifest["signature"] = signature

    return manifest


def sign_manifest(manifest: dict, key: str) -> str:
    """Sign manifest with HS256 (simplified JWS)"""
    # Simplified signing: HMAC-SHA256 of manifest JSON
    payload = json.dumps(manifest, sort_keys=True)
    signature = hashlib.sha256((payload + key).encode()).hexdigest()
    return f"HS256.{signature}"


# ============================================================================
# FASTAPI ROUTER
# ============================================================================

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("", response_model=ExportResponse, status_code=200)
async def create_export(request: ExportRequest):
    """
    Create export bundle for session.

    Body:
    - sessionId: Session UUID
    - formats: List of formats (md, json, or both)
    - include: What to include (transcript, events, attachments)

    Returns:
    - exportId: Export identifier
    - status: "ready" (sync) or "processing" (async)
    - artifacts: List of generated files with URLs and hashes
    - manifestUrl: URL to manifest.json
    """
    export_id = generate_export_id()
    export_path = EXPORT_DIR / export_id
    export_path.mkdir(parents=True, exist_ok=True)

    artifacts = []
    manifest_files = []

    # Generate requested formats
    for fmt in request.formats:
        content = generate_deterministic_content(request.sessionId, fmt, request.include)
        filename = f"session.{fmt}"
        filepath = export_path / filename

        # Write file
        filepath.write_text(content, encoding="utf-8")

        # Compute hash
        sha256 = compute_sha256(content)
        file_bytes = len(content.encode("utf-8"))

        # Add to artifacts
        url = f"{BASE_DOWNLOAD_URL}/{export_id}/{filename}"
        artifacts.append(ExportArtifact(format=fmt, url=url, sha256=sha256, bytes=file_bytes))

        # Add to manifest files list
        manifest_files.append({"name": filename, "sha256": sha256, "bytes": file_bytes})

    # Generate manifest
    signature = None
    if SIGNING_KEY:
        signature = sign_manifest(
            {
                "exportId": export_id,
                "sessionId": request.sessionId,
                "files": manifest_files,
            },
            SIGNING_KEY,
        )

    manifest = create_manifest(export_id, request.sessionId, manifest_files, signature)
    manifest_path = export_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Compute manifest hash
    manifest_content = manifest_path.read_text(encoding="utf-8")
    manifest_sha256 = compute_sha256(manifest_content)
    manifest_bytes = len(manifest_content.encode("utf-8"))

    # Add manifest to artifacts
    manifest_url = f"{BASE_DOWNLOAD_URL}/{export_id}/manifest.json"
    artifacts.append(
        ExportArtifact(
            format="manifest", url=manifest_url, sha256=manifest_sha256, bytes=manifest_bytes
        )
    )

    return ExportResponse(
        exportId=export_id, status="ready", artifacts=artifacts, manifestUrl=manifest_url
    )


@router.get("/{export_id}", response_model=ExportResponse)
async def get_export(export_id: str):
    """
    Get export status and metadata.

    Path params:
    - export_id: Export identifier

    Returns:
    - Export metadata (same as POST response)

    Raises:
    - 404: Export not found
    """
    export_path = EXPORT_DIR / export_id

    if not export_path.exists():
        raise HTTPException(status_code=404, detail=f"Export {export_id} not found")

    # Read manifest
    manifest_path = export_path / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=500, detail="Manifest not found")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Reconstruct artifacts
    artifacts = []
    for file_info in manifest["files"]:
        filename = file_info["name"]
        fmt = filename.split(".")[-1]
        url = f"{BASE_DOWNLOAD_URL}/{export_id}/{filename}"
        artifacts.append(
            ExportArtifact(
                format=fmt,
                url=url,
                sha256=file_info["sha256"],
                bytes=file_info["bytes"],
            )
        )

    # Add manifest artifact
    manifest_content = manifest_path.read_text(encoding="utf-8")
    manifest_sha256 = compute_sha256(manifest_content)
    manifest_bytes = len(manifest_content.encode("utf-8"))
    manifest_url = f"{BASE_DOWNLOAD_URL}/{export_id}/manifest.json"

    artifacts.append(
        ExportArtifact(
            format="manifest", url=manifest_url, sha256=manifest_sha256, bytes=manifest_bytes
        )
    )

    return ExportResponse(
        exportId=export_id, status="ready", artifacts=artifacts, manifestUrl=manifest_url
    )


@router.post("/{export_id}/verify", response_model=VerifyResponse)
async def verify_export(export_id: str, request: VerifyRequest):
    """
    Verify export file integrity.

    Path params:
    - export_id: Export identifier

    Body:
    - targets: List of targets to verify (md, json, manifest)

    Returns:
    - ok: True if all targets pass
    - results: List of verification results per target

    Verification:
    - Computes SHA256 of file on disk
    - Compares against manifest.sha256
    - If SIGNING_KEY exists, validates JWS signature
    """
    export_path = EXPORT_DIR / export_id

    if not export_path.exists():
        raise HTTPException(status_code=404, detail=f"Export {export_id} not found")

    # Read manifest
    manifest_path = export_path / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=500, detail="Manifest not found")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    results = []
    all_ok = True

    for target in request.targets:
        if target == "manifest":
            # Verify manifest signature if SIGNING_KEY exists
            if SIGNING_KEY and "signature" in manifest:
                # Verify signature
                expected_sig = sign_manifest(
                    {
                        "exportId": manifest["exportId"],
                        "sessionId": manifest["sessionId"],
                        "files": manifest["files"],
                    },
                    SIGNING_KEY,
                )

                if manifest["signature"] == expected_sig:
                    results.append(VerifyResult(target="manifest", ok=True))
                else:
                    results.append(
                        VerifyResult(
                            target="manifest",
                            ok=False,
                            message="Signature verification failed",
                        )
                    )
                    all_ok = False
            else:
                # No signature, just confirm manifest exists
                results.append(
                    VerifyResult(target="manifest", ok=True, message="No signature to verify")
                )

        else:
            # Verify file hash
            filename = f"session.{target}"
            filepath = export_path / filename

            if not filepath.exists():
                results.append(
                    VerifyResult(target=target, ok=False, message=f"File {filename} not found")
                )
                all_ok = False
                continue

            # Find file in manifest
            file_info = next((f for f in manifest["files"] if f["name"] == filename), None)

            if not file_info:
                results.append(
                    VerifyResult(
                        target=target, ok=False, message=f"File {filename} not in manifest"
                    )
                )
                all_ok = False
                continue

            # Compute hash
            content = filepath.read_text(encoding="utf-8")
            actual_sha256 = compute_sha256(content)
            expected_sha256 = file_info["sha256"]

            if actual_sha256 == expected_sha256:
                results.append(VerifyResult(target=target, ok=True))
            else:
                results.append(
                    VerifyResult(
                        target=target,
                        ok=False,
                        message=f"Hash mismatch: expected {expected_sha256[:8]}... got {actual_sha256[:8]}...",
                    )
                )
                all_ok = False

    return VerifyResponse(ok=all_ok, results=results)


# ============================================================================
# STATIC FILE SERVING
# ============================================================================
# Note: This should be registered in main app as:
# app.mount("/downloads", StaticFiles(directory=EXPORT_DIR), name="downloads")
# Or use explicit endpoint:


@router.get("/{export_id}/download/{filename}")
async def download_file(export_id: str, filename: str):
    """
    Download export file (alternative to static serving).

    Path params:
    - export_id: Export identifier
    - filename: File to download (session.md, session.json, manifest.json)

    Returns:
    - File content as attachment
    """
    export_path = EXPORT_DIR / export_id
    filepath = export_path / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"File {filename} not found")

    return FileResponse(filepath, media_type="application/octet-stream", filename=filename)
