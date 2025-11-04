"""Service layer for triage intake operations.

Handles triage buffer management with atomic file operations and manifests.
Encapsulates triage data storage and retrieval.

Clean Code: This service layer makes endpoints simple and focused.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from backend.logger import get_logger

logger = get_logger(__name__)


class TriageService:
    """Service for triage intake operations.

    Orchestrates triage buffer creation, manifest generation, and retrieval.
    Handles:
    - Unique buffer ID generation
    - Atomic file writes with fsync
    - Manifest creation with SHA256 hashes
    - Buffer retrieval and metadata management
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Initialize service with triage data directory.

        Args:
            data_dir: Directory for triage buffers (default: ./data/triage_buffers)
        """
        self.data_dir = data_dir or Path(os.getenv("TRIAGE_DATA_DIR", "./data/triage_buffers"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"TriageService initialized with data_dir={self.data_dir}")

    def generate_buffer_id(self) -> str:
        """Generate unique buffer ID.

        Format: tri_{uuid_hex}

        Returns:
            Buffer identifier
        """
        return f"tri_{uuid4().hex}"

    def compute_payload_hash(self, payload: dict[str, Any]) -> str:
        """Compute SHA256 hash of payload.

        Args:
            payload: Payload dictionary

        Returns:
            SHA256 hex digest
        """
        payload_json = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(payload_json.encode()).hexdigest()

    def create_buffer(
        self,
        payload: dict[str, Any],
        client_ip: str,
        user_agent: str,
    ) -> dict[str, Any]:
        """Create triage buffer with atomic file operations.

        Steps:
        1. Generate unique buffer_id
        2. Create buffer directory
        3. Write intake.json atomically with fsync
        4. Generate manifest with SHA256 hash
        5. Return buffer metadata

        Args:
            payload: Triage intake payload
            client_ip: Client IP address
            user_agent: Client user agent

        Returns:
            Buffer metadata dict with buffer_id, received_at, manifest_url

        Raises:
            IOError: If file operations fail
        """
        buffer_id = self.generate_buffer_id()
        buffer_dir = self.data_dir / buffer_id

        try:
            # Create buffer directory
            buffer_dir.mkdir(parents=True, exist_ok=True)

            # Prepare intake data
            received_at = datetime.now(timezone.utc).isoformat() + "Z"
            intake_data = {
                "bufferId": buffer_id,
                "receivedAt": received_at,
                "payload": payload,
                "client": {
                    "ip": client_ip,
                    "userAgent": user_agent,
                },
            }

            # Compute payload hash (SHA256)
            payload_hash = self.compute_payload_hash(payload)

            # Create manifest
            manifest = {
                "version": "1.0.0",
                "bufferId": buffer_id,
                "receivedAt": received_at,
                "payloadHash": f"sha256:{payload_hash}",
                "payloadSubset": {
                    "reason": payload.get("reason", "")[:100],
                    "symptomsCount": len(payload.get("symptoms", [])),
                    "hasTranscription": payload.get("audioTranscription") is not None,
                },
                "metadata": payload.get("metadata", {}),
            }

            # Write intake.json atomically
            intake_path = buffer_dir / "intake.json"
            intake_tmp = buffer_dir / "intake.json.tmp"

            with open(intake_tmp, "w") as f:
                json.dump(intake_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Atomic write guarantee

            # Atomic rename
            intake_tmp.rename(intake_path)

            # Write manifest.json
            manifest_path = buffer_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            logger.info(
                f"TRIAGE_BUFFER_CREATED: buffer_id={buffer_id}, payload_hash={payload_hash}, ip={client_ip}"
            )

            return {
                "buffer_id": buffer_id,
                "received_at": received_at,
                "manifest_url": f"/api/triage/manifest/{buffer_id}",
                "payload_hash": payload_hash,
            }

        except OSError as e:
            logger.error(f"TRIAGE_BUFFER_CREATION_FAILED: buffer_id={buffer_id}, error={str(e)}")
            raise OSError(f"Failed to create triage buffer: {str(e)}") from e

    def get_manifest(self, buffer_id: str) -> Optional[dict[str, Any]]:
        """Retrieve manifest for a triage buffer.

        Args:
            buffer_id: Buffer identifier

        Returns:
            Manifest dict or None if not found

        Raises:
            IOError: If file read fails
        """
        manifest_path = self.data_dir / buffer_id / "manifest.json"

        if not manifest_path.exists():
            logger.warning(f"TRIAGE_MANIFEST_NOT_FOUND: buffer_id={buffer_id}")
            return None

        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            logger.info(f"TRIAGE_MANIFEST_RETRIEVED: buffer_id={buffer_id}")
            return manifest
        except OSError as e:
            logger.error(f"TRIAGE_MANIFEST_READ_FAILED: buffer_id={buffer_id}, error={str(e)}")
            raise OSError(f"Failed to read manifest: {str(e)}") from e

    def get_intake(self, buffer_id: str) -> Optional[dict[str, Any]]:
        """Retrieve intake data for a triage buffer.

        Args:
            buffer_id: Buffer identifier

        Returns:
            Intake dict or None if not found

        Raises:
            IOError: If file read fails
        """
        intake_path = self.data_dir / buffer_id / "intake.json"

        if not intake_path.exists():
            logger.warning(f"TRIAGE_INTAKE_NOT_FOUND: buffer_id={buffer_id}")
            return None

        try:
            with open(intake_path) as f:
                intake = json.load(f)
            logger.info(f"TRIAGE_INTAKE_RETRIEVED: buffer_id={buffer_id}")
            return intake
        except OSError as e:
            logger.error(f"TRIAGE_INTAKE_READ_FAILED: buffer_id={buffer_id}, error={str(e)}")
            raise OSError(f"Failed to read intake: {str(e)}") from e

    def list_buffers(self, limit: int = 100) -> list[dict[str, Any]]:
        """List triage buffers.

        Args:
            limit: Maximum number of buffers to return

        Returns:
            List of buffer metadata dicts
        """
        buffers = []
        for buffer_dir in sorted(self.data_dir.iterdir(), reverse=True)[:limit]:
            if buffer_dir.is_dir():
                manifest_path = buffer_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            manifest = json.load(f)
                        buffers.append(
                            {
                                "buffer_id": manifest.get("bufferId"),
                                "received_at": manifest.get("receivedAt"),
                                "payload_hash": manifest.get("payloadHash"),
                                "metadata": manifest.get("metadata", {}),
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            f"TRIAGE_BUFFER_LIST_ERROR: buffer_id={buffer_dir.name}, error={str(e)}"
                        )

        logger.info(f"TRIAGE_BUFFERS_LISTED: count={len(buffers)}")
        return buffers
