"""Service layer for export operations.

Handles session export with manifest and hash verification.
Encapsulates deterministic content generation and file operations.

Clean Code: This service layer makes endpoints simple and focused.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.logger import get_logger

logger = get_logger(__name__)


class ExportService:
    """Service for export operations.

    Orchestrates export generation, verification, and cleanup.
    Handles:
    - Deterministic content generation
    - Manifest creation and signing
    - File integrity verification
    - Export metadata management
    """

    def __init__(
        self,
        export_dir: Optional[Path] = None,
        signing_key: Optional[str] = None,
        git_commit: str = "dev",
    ) -> None:
        """Initialize service with configuration.

        Args:
            export_dir: Directory for export artifacts
            signing_key: Optional signing key for JWS
            git_commit: Git commit hash for metadata
        """
        self.export_dir = export_dir or Path(os.getenv("EXPORT_DIR", "/tmp/fi_exports"))
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.signing_key = signing_key
        self.git_commit = git_commit

        logger.info("ExportService initialized", export_dir=str(self.export_dir))

    def generate_export_id(self) -> str:
        """Generate unique export ID.

        Format: exp_{timestamp}_{random}

        Returns:
            Export identifier
        """
        ts = int(time.time())
        rand = random.randint(1000, 9999)
        return f"exp_{ts}_{rand}"

    def compute_sha256(self, content: str) -> str:
        """Compute SHA256 hash of content.

        Args:
            content: Content to hash

        Returns:
            SHA256 hex digest
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def sign_manifest(self, manifest: dict, key: str) -> str:
        """Sign manifest with HS256 (simplified JWS).

        Args:
            manifest: Manifest dict to sign
            key: Signing key

        Returns:
            Signature string (HS256.{signature})
        """
        payload = json.dumps(manifest, sort_keys=True)
        signature = hashlib.sha256((payload + key).encode()).hexdigest()
        return f"HS256.{signature}"

    def create_manifest(
        self,
        export_id: str,
        session_id: str,
        files: list[dict],
        signature: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create export manifest.

        Args:
            export_id: Export identifier
            session_id: Session identifier
            files: List of file metadata dicts
            signature: Optional JWS signature

        Returns:
            Manifest dict with version, metadata, files
        """
        manifest = {
            "version": "1.0",
            "exportId": export_id,
            "sessionId": session_id,
            "createdAt": datetime.now(timezone.utc).isoformat() + "Z",
            "algorithm": "sha256",
            "files": files,
            "meta": {"generator": "FI", "commit": self.git_commit, "deterministic": True},
        }

        if signature:
            manifest["signature"] = signature

        return manifest

    def create_export(
        self,
        session_id: str,
        content_dict: dict[str, str],
        formats: list[str],
    ) -> dict[str, Any]:
        """Create export bundle.

        Args:
            session_id: Session identifier
            content_dict: Dict with format -> content mapping
            formats: List of formats to export

        Returns:
            Export metadata with exportId, artifacts, manifestUrl

        Raises:
            ValueError: If input validation fails
            IOError: If file operations fail
        """
        if not session_id:
            raise ValueError("session_id required")

        if not formats or len(formats) == 0:
            raise ValueError("At least one format required")

        try:
            # Generate export ID and create directory
            export_id = self.generate_export_id()
            export_path = self.export_dir / export_id
            export_path.mkdir(parents=True, exist_ok=True)

            artifacts = []
            manifest_files = []

            # Generate requested formats
            for fmt in formats:
                if fmt not in content_dict:
                    logger.warning(f"CONTENT_NOT_PROVIDED: format={fmt}, export_id={export_id}")
                    continue

                content = content_dict[fmt]
                filename = f"session.{fmt}"
                filepath = export_path / filename

                # Write file
                filepath.write_text(content, encoding="utf-8")

                # Compute hash
                sha256 = self.compute_sha256(content)
                file_bytes = len(content.encode("utf-8"))

                # Add to artifacts
                artifacts.append(
                    {
                        "format": fmt,
                        "sha256": sha256,
                        "bytes": file_bytes,
                    }
                )

                # Add to manifest files list
                manifest_files.append({"name": filename, "sha256": sha256, "bytes": file_bytes})

            # Generate manifest
            signature = None
            if self.signing_key:
                signature = self.sign_manifest(
                    {
                        "exportId": export_id,
                        "sessionId": session_id,
                        "files": manifest_files,
                    },
                    self.signing_key,
                )

            manifest = self.create_manifest(export_id, session_id, manifest_files, signature)
            manifest_path = export_path / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            # Compute manifest hash
            manifest_content = manifest_path.read_text(encoding="utf-8")
            manifest_sha256 = self.compute_sha256(manifest_content)
            manifest_bytes = len(manifest_content.encode("utf-8"))

            # Add manifest to artifacts
            artifacts.append(
                {
                    "format": "manifest",
                    "sha256": manifest_sha256,
                    "bytes": manifest_bytes,
                }
            )

            logger.info(
                "EXPORT_CREATED",
                export_id=export_id,
                session_id=session_id,
                formats=formats,
            )

            return {
                "export_id": export_id,
                "session_id": session_id,
                "artifacts": artifacts,
                "manifest_sha256": manifest_sha256,
            }

        except OSError as e:
            logger.error("EXPORT_CREATION_FAILED", error=str(e))
            raise

    def get_export_metadata(self, export_id: str) -> dict[str, Optional[Any]] | None:
        """Get export metadata and artifacts.

        Args:
            export_id: Export identifier

        Returns:
            Export metadata or None if not found

        Raises:
            IOError: If file read fails
        """
        export_path = self.export_dir / export_id

        if not export_path.exists():
            logger.warning(f"EXPORT_NOT_FOUND: export_id={export_id}")
            return None

        try:
            # Read manifest
            manifest_path = export_path / "manifest.json"
            if not manifest_path.exists():
                logger.error("MANIFEST_NOT_FOUND", export_id=export_id)
                return None

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            # Reconstruct artifacts
            artifacts = []
            for file_info in manifest["files"]:
                filename = file_info["name"]
                fmt = filename.split(".")[-1]
                artifacts.append(
                    {
                        "format": fmt,
                        "sha256": file_info["sha256"],
                        "bytes": file_info["bytes"],
                    }
                )

            # Add manifest artifact
            manifest_content = manifest_path.read_text(encoding="utf-8")
            manifest_sha256 = self.compute_sha256(manifest_content)
            manifest_bytes = len(manifest_content.encode("utf-8"))

            artifacts.append(
                {
                    "format": "manifest",
                    "sha256": manifest_sha256,
                    "bytes": manifest_bytes,
                }
            )

            return {
                "export_id": export_id,
                "session_id": manifest.get("sessionId"),
                "artifacts": artifacts,
                "created_at": manifest.get("createdAt"),
            }

        except OSError as e:
            logger.error("EXPORT_METADATA_FAILED", export_id=export_id, error=str(e))
            raise

    def verify_export(self, export_id: str, targets: list[str]) -> dict[str, Any]:
        """Verify export file integrity.

        Args:
            export_id: Export identifier
            targets: List of targets to verify (md, json, manifest)  # type: ignore[call-arg]

        Returns:
            Verification results with ok status and per-target results

        Raises:
            IOError: If file read fails
        """
        export_path = self.export_dir / export_id

        if not export_path.exists():
            raise OSError(f"Export {export_id} not found")

        try:
            # Read manifest
            manifest_path = export_path / "manifest.json"
            if not manifest_path.exists():
                raise OSError(f"Manifest not found in {export_id}")

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            results = []
            all_ok = True

            for target in targets:
                if target == "manifest":
                    # Verify manifest signature if SIGNING_KEY exists
                    if self.signing_key and "signature" in manifest:
                        expected_sig = self.sign_manifest(
                            {
                                "exportId": manifest["exportId"],
                                "sessionId": manifest["sessionId"],
                                "files": manifest["files"],
                            },
                            self.signing_key,
                        )

                        if manifest["signature"] == expected_sig:
                            results.append(
                                {
                                    "target": "manifest",
                                    "ok": True,
                                }
                            )
                        else:
                            results.append(
                                {
                                    "target": "manifest",
                                    "ok": False,
                                    "message": "Signature verification failed",
                                }
                            )
                            all_ok = False
                    else:
                        # No signature, just confirm manifest exists
                        results.append(
                            {
                                "target": "manifest",
                                "ok": True,
                                "message": "No signature to verify",
                            }
                        )

                else:
                    # Verify file hash
                    filename = f"session.{target}"
                    filepath = export_path / filename

                    if not filepath.exists():
                        results.append(
                            {
                                "target": target,
                                "ok": False,
                                "message": f"File {filename} not found",
                            }
                        )
                        all_ok = False
                        continue

                    # Compute hash and compare
                    file_content = filepath.read_text(encoding="utf-8")
                    computed_sha256 = self.compute_sha256(file_content)

                    # Find in manifest
                    manifest_entry = next(
                        (f for f in manifest["files"] if f["name"] == filename), None
                    )

                    if manifest_entry and manifest_entry["sha256"] == computed_sha256:
                        results.append(
                            {
                                "target": target,
                                "ok": True,
                            }
                        )
                    else:
                        results.append(
                            {
                                "target": target,
                                "ok": False,
                                "message": "Hash mismatch",
                            }
                        )
                        all_ok = False

            logger.info("EXPORT_VERIFIED", export_id=export_id, all_ok=all_ok)

            return {
                "ok": all_ok,
                "results": results,
            }

        except OSError as e:
            logger.error("EXPORT_VERIFICATION_FAILED", export_id=export_id, error=str(e))
            raise

    def delete_export(self, export_id: str) -> bool:
        """Delete export (soft delete).

        Args:
            export_id: Export identifier

        Returns:
            True if deletion successful
        """
        export_path = self.export_dir / export_id

        if not export_path.exists():
            logger.warning(f"EXPORT_NOT_FOUND_FOR_DELETE: export_id={export_id}")
            return False

        try:
            # Mark as deleted (keep for audit trail)
            delete_marker = export_path / ".deleted"
            delete_marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")

            logger.info("EXPORT_DELETED", export_id=export_id)
            return True

        except OSError as e:
            logger.error("EXPORT_DELETION_FAILED", export_id=export_id, error=str(e))
            raise
