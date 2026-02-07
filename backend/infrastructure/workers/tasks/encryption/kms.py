"""Key Management Service (KMS) interface for envelope encryption.

Handles Data Encryption Key (DEK) generation and Key Encryption Key (KEK) management.

**Security Note:**
- Current implementation is SIMULATED for MVP
- Production MUST use real KMS (AWS KMS, Azure Key Vault, Synology KMS)
- KEK should never be stored in HDF5 (only wrapped_dek)
- Key rotation recommended every 90 days

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from encryption_worker.py)
Card: Infrastructure Modularization - Quick Wins (Dione Moon)
"""

from __future__ import annotations

import base64
import hashlib
import os
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.infrastructure.workers.tasks.encryption.constants import (
    DEK_SIZE_BYTES,
    IV_SIZE_BYTES,
)
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


def b64d(s: str) -> bytes:
    """Base64 decode ASCII string to bytes.

    Args:
        s: Base64-encoded string

    Returns:
        Decoded bytes
    """
    return base64.b64decode(s.encode("ascii"))


def generate_dek() -> tuple[str, bytes, AESGCM]:
    """Generate a new Data Encryption Key (DEK) for session.

    Returns:
        Tuple of (dek_id, raw_dek_bytes, aesgcm_cipher)

    Note:
        DEK ID format: dek_v1_{timestamp}_{random_suffix}
        This allows key rotation and tracking.
    """
    dek = os.urandom(DEK_SIZE_BYTES)
    timestamp = int(time.time())
    random_suffix = base64.urlsafe_b64encode(os.urandom(8)).decode("ascii").rstrip("=")
    dek_id = f"dek_v1_{timestamp}_{random_suffix}"
    aesgcm = AESGCM(dek)
    return dek_id, dek, aesgcm


def load_kek() -> bytes:
    """Load Key Encryption Key (KEK) from KMS.

    Returns:
        KEK bytes (32 bytes for AES-256)

    Note:
        **SIMULATED FOR MVP**
        Production must:
        1. Fetch KEK from AWS KMS / Azure Key Vault / Synology KMS
        2. Use envelope encryption (encrypt DEK with KEK)
        3. Store only wrapped_dek in HDF5
        4. Implement key rotation every 90 days

    Raises:
        NotImplementedError: If KMS_ENDPOINT not configured
    """
    # MVP: Use environment variable (NOT PRODUCTION SAFE)
    kek_b64 = os.environ.get("ENCRYPTION_KEK_B64")
    if kek_b64:
        logger.warning(
            "load_kek",
            extra={
                "source": "environment_variable",
                "warning": "NOT_PRODUCTION_SAFE_USE_KMS",
            },
        )
        return b64d(kek_b64)

    # MVP fallback: Generate deterministic KEK from hostname (INSECURE)
    import socket

    hostname = socket.gethostname()
    kek = hashlib.sha256(f"AURITY_KEK_{hostname}".encode()).digest()
    logger.warning(
        "load_kek_fallback",
        extra={
            "source": "hostname_derived",
            "warning": "INSECURE_MVP_ONLY",
            "hostname": hostname,
        },
    )
    return kek


def wrap_dek(dek: bytes, kek: bytes) -> bytes:
    """Wrap (encrypt) DEK with KEK using AES-GCM.

    Args:
        dek: Data Encryption Key (32 bytes)
        kek: Key Encryption Key (32 bytes)

    Returns:
        Wrapped DEK (ciphertext + GCM tag)

    Note:
        Envelope encryption: only wrapped_dek stored in HDF5
    """
    kek_cipher = AESGCM(kek)
    iv = os.urandom(IV_SIZE_BYTES)
    aad = b"AURITY_DEK_WRAP_V1"
    wrapped = kek_cipher.encrypt(iv, dek, aad)
    # Prepend IV for unwrapping (IV || ciphertext || tag)
    return iv + wrapped


def unwrap_dek(wrapped_dek: bytes, kek: bytes) -> bytes:
    """Unwrap (decrypt) DEK using KEK.

    Args:
        wrapped_dek: Wrapped DEK (IV || ciphertext || tag)
        kek: Key Encryption Key

    Returns:
        Unwrapped DEK (32 bytes)

    Raises:
        cryptography.exceptions.InvalidTag: If KEK incorrect or data tampered
    """
    kek_cipher = AESGCM(kek)
    iv = wrapped_dek[:IV_SIZE_BYTES]
    ciphertext = wrapped_dek[IV_SIZE_BYTES:]
    aad = b"AURITY_DEK_WRAP_V1"
    return kek_cipher.decrypt(iv, ciphertext, aad)
