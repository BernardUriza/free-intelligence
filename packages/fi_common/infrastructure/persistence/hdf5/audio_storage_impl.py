from __future__ import annotations

"""Audio storage implementation (migrated copy).

Session-scoped audio storage with atomic writes, SHA256 hashing, TTL metadata,
and manifest creation. Mirrors legacy backend.common.fi_common.storage.audio_storage
for backward compatibility while enabling clean architecture packaging.
"""

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from fi_common.shared.logging import get_logger

logger = get_logger(__name__)

# Storage configuration
AUDIO_STORAGE_DIR = Path(
    os.getenv("FI_AUDIO_ROOT", os.getenv("AUDIO_STORAGE_DIR", "./storage/audio"))
).resolve()
AUDIO_TTL_DAYS = int(os.getenv("AUDIO_TTL_DAYS", "7"))

# Ensure storage directory exists
AUDIO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
logger.info("AUDIO_STORAGE_INITIALIZED")


def validate_session_id(session_id: str) -> bool:
    """Validate session_id is a valid UUID4 format."""
    try:
        UUID(session_id, version=4)
        return True
    except (ValueError, AttributeError):
        return False


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def save_audio_file(
    session_id: str,
    audio_content: bytes,
    file_extension: str,
    metadata: dict[str, Any | None] | None = None,
) -> dict[str, Any]:
    """Save audio file with atomic write, manifest, and TTL metadata."""
    if not validate_session_id(session_id):
        raise ValueError(f"Invalid session_id format: {session_id} (must be UUID4)")

    allowed_extensions = {"webm", "wav", "mp3", "m4a", "ogg"}
    file_extension = file_extension.lower().lstrip(".")
    if file_extension not in allowed_extensions:
        raise ValueError(
            f"Invalid file extension: {file_extension} "
            + f"(allowed: {', '.join(allowed_extensions)})"
        )

    session_dir = AUDIO_STORAGE_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    timestamp_ms = int(datetime.now(UTC).timestamp() * 1000)
    filename = f"{timestamp_ms}.{file_extension}"
    file_path = session_dir / filename

    tmp_path = file_path.with_suffix(f".{file_extension}.tmp")
    with open(tmp_path, "wb") as f:
        f.write(audio_content)
        f.flush()
        os.fsync(f.fileno())

    tmp_path.rename(file_path)

    file_hash = f"sha256:{compute_sha256(file_path)}"
    file_size = len(audio_content)
    ttl_expires_at = datetime.now(UTC) + timedelta(days=AUDIO_TTL_DAYS)

    manifest_data = {
        "version": "1.0.0",
        "sessionId": session_id,
        "timestampMs": timestamp_ms,
        "receivedAt": datetime.now(UTC).isoformat() + "Z",
        "filePath": str(file_path.relative_to(AUDIO_STORAGE_DIR)),
        "fileSize": file_size,
        "fileHash": file_hash,
        "fileExtension": file_extension,
        "ttlDays": AUDIO_TTL_DAYS,
        "ttlExpiresAt": ttl_expires_at.isoformat() + "Z",
        "metadata": metadata or {},
    }

    manifest_path = session_dir / f"{timestamp_ms}.manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    logger.info(
        "AUDIO_FILE_SAVED",
        session_id=session_id,
        file_path=str(file_path.relative_to(AUDIO_STORAGE_DIR)),
        file_size=file_size,
        file_hash=file_hash,
        ttl_expires_at=ttl_expires_at.isoformat(),
    )

    return {
        "file_path": str(file_path.relative_to(AUDIO_STORAGE_DIR)),
        "file_size": file_size,
        "file_hash": file_hash,
        "timestamp_ms": timestamp_ms,
        "ttl_expires_at": ttl_expires_at.isoformat() + "Z",
        "manifest_path": str(manifest_path.relative_to(AUDIO_STORAGE_DIR)),
    }


def get_audio_manifest(session_id: str, timestamp_ms: int) -> dict[str, Any] | None:
    """Retrieve audio manifest by session_id and timestamp."""
    manifest_path = AUDIO_STORAGE_DIR / session_id / f"{timestamp_ms}.manifest.json"

    if not manifest_path.exists():
        return None

    with open(manifest_path) as f:
        return json.load(f)
