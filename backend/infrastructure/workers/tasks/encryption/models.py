"""Encryption data models and type definitions.

Dataclasses for encryption manifest entries, session metadata, and worker results.

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from encryption_worker.py)
Card: Infrastructure Modularization - Quick Wins (Iapetus Moon)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EncryptionManifestEntry:
    """Manifest entry for a single encrypted dataset.

    Attributes:
        path: HDF5 dataset path (e.g., "/audio/full_audio")
        iv_b64: Base64-encoded IV (12 bytes)
        aad: Additional Authenticated Data used for GCM
        plaintext_sha256: SHA-256 checksum of plaintext (integrity verification)
        ciphertext_bytes: Size of ciphertext including GCM tag
        encrypted_at: ISO 8601 timestamp of encryption
    """

    path: str
    iv_b64: str
    aad: str
    plaintext_sha256: str
    ciphertext_bytes: int
    encrypted_at: str


@dataclass
class SessionMetadata:
    """Session-level encryption metadata.

    Attributes:
        session_id: Unique session identifier
        algorithm: Encryption algorithm (AES-GCM-256)
        dek_id: DEK identifier (for key rotation)
        idempotency_key: Unique key for idempotent operations
        encrypted_at: ISO 8601 timestamp
        encrypted_count: Number of datasets encrypted
        total_bytes: Total bytes encrypted (including GCM tags)
        schema_version: Crypto schema version
    """

    session_id: str
    algorithm: str
    dek_id: str
    idempotency_key: str
    encrypted_at: str
    encrypted_count: int
    total_bytes: int
    schema_version: str


@dataclass
class WorkerResult:
    """Worker execution result.

    Attributes:
        session_id: Session identifier
        status: SUCCESS | FAILED
        result: Result data (encrypted paths, bytes, etc.)
        duration_seconds: Execution time
        error: Error message (if failed)
    """

    session_id: str
    status: str
    result: dict[str, Any]
    duration_seconds: float
    error: str | None = None
