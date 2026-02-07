"""Encryption module for HDF5 session data.

Public API for AES-GCM-256 encryption with envelope encryption (KEK/DEK).

**Main Entry Point:**
    encrypt_session_worker() - Encrypt all datasets in a session

**Data Models:**
    WorkerResult - Worker execution result with status/error
    SessionMetadata - Session-level encryption metadata
    EncryptionManifestEntry - Manifest entry for encrypted dataset

**Constants:**
    CRYPTO_SCHEMA_VERSION - Current encryption schema version
    DEK_SIZE_BYTES - Data Encryption Key size (32 bytes)
    IV_SIZE_BYTES - Initialization Vector size (12 bytes)

**CLI:**
    Use: python -m backend.infrastructure.workers.tasks.encryption.cli

**Security:**
    - HIPAA 164.312(a)(2)(iv) compliant (encryption at rest)
    - NIST SP 800-38D (AES-GCM recommendations)
    - Envelope encryption (DEK wrapped with KEK)
    - NEVER reuses IV (unique per dataset)

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Module refactoring)
Card: Infrastructure Modularization - Quick Wins (Phoebe Moon)
"""

from __future__ import annotations

# Public API - Main entry point
from backend.infrastructure.workers.tasks.encryption.worker import encrypt_session_worker

# Public API - Data models
from backend.infrastructure.workers.tasks.encryption.models import (
    EncryptionManifestEntry,
    SessionMetadata,
    WorkerResult,
)

# Public API - Constants
from backend.infrastructure.workers.tasks.encryption.constants import (
    CRYPTO_SCHEMA_VERSION,
    DEK_SIZE_BYTES,
    IV_SIZE_BYTES,
)

__all__ = [
    # Main entry point
    "encrypt_session_worker",
    # Data models
    "WorkerResult",
    "SessionMetadata",
    "EncryptionManifestEntry",
    # Constants
    "CRYPTO_SCHEMA_VERSION",
    "DEK_SIZE_BYTES",
    "IV_SIZE_BYTES",
]

__version__ = "3.0.0"
