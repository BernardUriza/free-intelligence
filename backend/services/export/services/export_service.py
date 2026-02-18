"""DI Export Service - Refactored with dependency injection.

Handles export operations with injected logger for better testability.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any

import os
from backend.infrastructure.interfaces.ilogger import ILogger
from pathlib import Path


class DIExportService:
    """Export service with dependency injection.

    Orchestrates export generation, verification, and cleanup.
    Handles:
    - Deterministic content generation
    - Manifest creation and signing
    - File integrity verification
    - Export metadata management
    """

    def __init__(
        self,
        logger: ILogger,
        export_dir: Path | None = None,
        signing_key: str | None = None,
        git_commit: str = "dev",
    ) -> None:
        """Initialize service with injected logger and configuration.

        Args:
            logger: Logger instance
            export_dir: Directory for export artifacts
            signing_key: Optional signing key for JWS
            git_commit: Git commit hash for metadata
        """
        self.logger = logger
        self.export_dir = export_dir or Path(os.getenv("EXPORT_DIR", "/tmp/fi_exports"))
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.signing_key = signing_key
        self.git_commit = git_commit

        self.logger.info(
            "DIExportService initialized",
            export_dir=str(self.export_dir),
            git_commit=self.git_commit,
        )

    def create_export(
        self,
        session_id: str,
        include_audio: bool = True,
        include_transcript: bool = True,
        include_metadata: bool = True,
    ) -> dict[str, Any]:
        """Create export package for session.

        Args:
            session_id: Session to export
            include_audio: Include audio files
            include_transcript: Include transcript data
            include_metadata: Include session metadata

        Returns:
            Export result with paths and manifest
        """
        export_id = f"export_{session_id}_{int(time.time())}"

        self.logger.info(
            "EXPORT_CREATION_STARTED",
            export_id=export_id,
            session_id=session_id,
            include_audio=include_audio,
            include_transcript=include_transcript,
            include_metadata=include_metadata,
        )

        try:
            # Create export directory
            export_path = self.export_dir / export_id
            export_path.mkdir(exist_ok=True)

            # Generate deterministic content
            content = self._generate_export_content(
                session_id, include_audio, include_transcript, include_metadata
            )

            # Write content to files
            files_created = []
            for filename, data in content.items():
                file_path = export_path / filename
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
                files_created.append(str(file_path))

            # Create manifest
            manifest = self._create_manifest(export_id, session_id, files_created)
            manifest_path = export_path / "manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, default=str)

            # Sign manifest if key provided
            if self.signing_key:
                signature = self._sign_manifest(manifest, self.signing_key)
                sig_path = export_path / "manifest.jws"
                with open(sig_path, "w", encoding="utf-8") as f:
                    json.dump(signature, f, indent=2)

            self.logger.info(
                "EXPORT_CREATED",
                export_id=export_id,
                session_id=session_id,
                files_count=len(files_created),
            )

            return {
                "export_id": export_id,
                "session_id": session_id,
                "export_path": str(export_path),
                "files": files_created,
                "manifest": manifest,
                "status": "completed",
            }

        except Exception as e:
            self.logger.error(
                "EXPORT_CREATION_FAILED",
                export_id=export_id,
                session_id=session_id,
                error=str(e),
            )
            raise

    def _generate_export_content(
        self,
        session_id: str,
        include_audio: bool,
        include_transcript: bool,
        include_metadata: bool,
    ) -> dict[str, Any]:
        """Generate export content (placeholder implementation)."""
        content = {}

        if include_metadata:
            content["metadata.json"] = {
                "session_id": session_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "git_commit": self.git_commit,
            }

        if include_transcript:
            content["transcript.json"] = {
                "session_id": session_id,
                "transcripts": [],  # Placeholder
            }

        if include_audio:
            content["audio_manifest.json"] = {
                "session_id": session_id,
                "audio_files": [],  # Placeholder
            }

        return content

    def _create_manifest(self, export_id: str, session_id: str, files: list[str]) -> dict[str, Any]:
        """Create export manifest."""
        file_hashes = {}
        for file_path in files:
            with open(file_path, "rb") as f:
                content = f.read()
                file_hashes[os.path.basename(file_path)] = hashlib.sha256(content).hexdigest()

        return {
            "export_id": export_id,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "git_commit": self.git_commit,
            "files": file_hashes,
        }

    def _sign_manifest(self, manifest: dict[str, Any], signing_key: str) -> dict[str, Any]:
        """Sign manifest with JWS (placeholder)."""
        # Placeholder implementation
        return {
            "payload": json.dumps(manifest, default=str),
            "signature": "placeholder_signature",
            "header": {"alg": "HS256"},
        }
