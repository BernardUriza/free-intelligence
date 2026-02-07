"""Cryptographic operations for large dataset encryption.

Handles chunking and AES-GCM encryption/decryption of large datasets.

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from encryption_worker.py)
Card: Infrastructure Modularization - Quick Wins (Tethys Moon)
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import h5py
import numpy as np
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.infrastructure.workers.tasks.encryption.constants import (
    CHUNK_SIZE_BYTES,
    CHUNK_SIZE_THRESHOLD_MB,
    CRYPTO_BASE_PATH,
    IV_SIZE_BYTES,
)
from backend.infrastructure.workers.tasks.encryption.models import EncryptionManifestEntry
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)


def b64e(b: bytes) -> str:
    """Base64 encode bytes to ASCII string.

    Args:
        b: Bytes to encode

    Returns:
        Base64-encoded ASCII string
    """
    import base64

    return base64.b64encode(b).decode("ascii")


def b64d(s: str) -> bytes:
    """Base64 decode ASCII string to bytes.

    Args:
        s: Base64-encoded string

    Returns:
        Decoded bytes
    """
    import base64

    return base64.b64decode(s.encode("ascii"))


def sha256_hex(b: bytes) -> str:
    """Compute SHA-256 checksum of bytes.

    Args:
        b: Bytes to hash

    Returns:
        Hex-encoded SHA-256 digest (64 chars)
    """
    import hashlib

    return hashlib.sha256(b).hexdigest()


def chunk_large_data(data: bytes, chunk_size: int = CHUNK_SIZE_BYTES) -> list[bytes]:
    """Split large data into chunks for encryption.

    Args:
        data: Raw bytes to chunk
        chunk_size: Maximum size per chunk (default: 50MB)

    Returns:
        List of byte chunks

    Note:
        Files > 500MB are automatically chunked to prevent memory issues
        and enable parallel encryption/decryption.
    """
    if len(data) <= chunk_size:
        return [data]

    chunks = []
    for i in range(0, len(data), chunk_size):
        chunks.append(data[i : i + chunk_size])

    logger.info(
        "data_chunked",
        extra={
            "total_bytes": len(data),
            "chunk_count": len(chunks),
            "chunk_size_mb": chunk_size // (1024 * 1024),
        },
    )
    return chunks


def encrypt_large_dataset(
    session_id: str,
    h5: h5py.File,
    ds_path: str,
    aesgcm: AESGCM,
    dek_id: str,
    read_dataset_as_bytes,  # type: ignore[no-untyped-def]
    write_json_dataset,  # type: ignore[no-untyped-def]
) -> list[EncryptionManifestEntry]:
    """Encrypt a large dataset with automatic chunking.

    Args:
        session_id: Session identifier
        h5: HDF5 file handle (open for read+write)
        ds_path: Dataset path
        aesgcm: AESGCM cipher
        dek_id: DEK identifier
        read_dataset_as_bytes: Function to read HDF5 dataset as bytes
        write_json_dataset: Function to write JSON to HDF5

    Returns:
        List of manifest entries (one per chunk)

    Note:
        For files > 500MB, splits into 50MB chunks. Each chunk gets:
        - Unique IV (NEVER reuse)
        - Separate manifest entry
        - Path suffix: original_path__chunk_N
    """
    ds = h5[ds_path]
    plain, orig_meta = read_dataset_as_bytes(ds)

    # Check if chunking needed
    threshold_bytes = CHUNK_SIZE_THRESHOLD_MB * 1024 * 1024
    if len(plain) <= threshold_bytes:
        # Small file: encrypt normally (single chunk)
        return []  # Signal to use normal encryption

    logger.info(
        "large_file_detected",
        extra={
            "path": ds_path,
            "size_mb": len(plain) // (1024 * 1024),
            "threshold_mb": CHUNK_SIZE_THRESHOLD_MB,
        },
    )

    # Chunk the data
    chunks = chunk_large_data(plain)
    manifest_entries: list[EncryptionManifestEntry] = []

    # Delete original dataset
    del h5[ds_path]

    # Create chunk group
    chunk_group_path = f"{ds_path}__chunks"
    chunk_group = h5.require_group(chunk_group_path)
    chunk_group.attrs["original_path"] = ds_path
    chunk_group.attrs["chunk_count"] = len(chunks)
    chunk_group.attrs["total_plaintext_bytes"] = len(plain)
    chunk_group.attrs["plaintext_sha256"] = sha256_hex(plain)

    # Encrypt each chunk
    for i, chunk_data in enumerate(chunks):
        chunk_path = f"{chunk_group_path}/chunk_{i:04d}"
        chunk_sha256 = sha256_hex(chunk_data)

        # Unique IV per chunk (CRITICAL: never reuse IV)
        iv = os.urandom(IV_SIZE_BYTES)
        aad = f"{session_id}:{chunk_path}".encode()

        # Encrypt chunk
        ciphertext = aesgcm.encrypt(iv, chunk_data, aad)

        # Store as dataset
        enc_array = np.frombuffer(ciphertext, dtype=np.uint8)
        dset = h5.create_dataset(chunk_path, data=enc_array, dtype=np.uint8)
        dset.attrs["enc:algorithm"] = "AES-GCM-256"
        dset.attrs["enc:dek_id"] = dek_id
        dset.attrs["enc:iv_b64"] = b64e(iv)
        dset.attrs["enc:plaintext_sha256"] = chunk_sha256
        dset.attrs["enc:chunk_index"] = i
        dset.attrs["enc:ts"] = datetime.now(UTC).isoformat()

        manifest_entries.append(
            EncryptionManifestEntry(
                path=chunk_path,
                iv_b64=b64e(iv),
                aad=f"{session_id}:{chunk_path}",
                plaintext_sha256=chunk_sha256,
                ciphertext_bytes=len(ciphertext),
                encrypted_at=datetime.now(UTC).isoformat(),
            )
        )

        logger.debug(
            "chunk_encrypted",
            extra={"chunk_path": chunk_path, "index": i, "bytes": len(ciphertext)},
        )

    # Save original metadata for reassembly
    orig_meta["chunked"] = True
    orig_meta["chunk_count"] = len(chunks)
    orig_meta_path = f"{CRYPTO_BASE_PATH}/orig_meta{ds_path.replace('/', '__')}"
    write_json_dataset(h5, orig_meta_path, orig_meta)

    logger.info(
        "large_file_encrypted",
        extra={
            "original_path": ds_path,
            "chunk_count": len(chunks),
            "total_ciphertext_bytes": sum(m.ciphertext_bytes for m in manifest_entries),
        },
    )

    return manifest_entries


def decrypt_chunked_dataset(
    session_id: str,
    h5: h5py.File,
    chunk_group_path: str,
    aesgcm: AESGCM,
) -> bytes:
    """Decrypt a chunked dataset and reassemble original data.

    Args:
        session_id: Session identifier
        h5: HDF5 file handle (open for read)
        chunk_group_path: Path to chunk group (e.g., "/audio/full_audio__chunks")
        aesgcm: AESGCM cipher with DEK

    Returns:
        Reassembled plaintext bytes

    Raises:
        ValueError: If chunk integrity check fails
        cryptography.exceptions.InvalidTag: If decryption fails

    Note:
        Verifies SHA-256 of reassembled data against stored checksum.
    """
    chunk_group = h5[chunk_group_path]
    chunk_count = chunk_group.attrs["chunk_count"]
    expected_sha256 = chunk_group.attrs["plaintext_sha256"]

    logger.info(
        "decrypting_chunked_dataset",
        extra={
            "chunk_group": chunk_group_path,
            "chunk_count": chunk_count,
        },
    )

    # Decrypt chunks in order
    plaintext_chunks: list[bytes] = []
    for i in range(chunk_count):
        chunk_path = f"{chunk_group_path}/chunk_{i:04d}"
        ds = h5[chunk_path]

        # Read ciphertext
        ciphertext = ds[...].tobytes()

        # Get IV and reconstruct AAD
        iv = b64d(ds.attrs["enc:iv_b64"])
        aad = f"{session_id}:{chunk_path}".encode()

        # Decrypt
        plaintext = aesgcm.decrypt(iv, ciphertext, aad)
        plaintext_chunks.append(plaintext)

        logger.debug(
            "chunk_decrypted",
            extra={"chunk_path": chunk_path, "index": i, "bytes": len(plaintext)},
        )

    # Reassemble
    full_plaintext = b"".join(plaintext_chunks)

    # Verify integrity
    actual_sha256 = sha256_hex(full_plaintext)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"Integrity check failed for {chunk_group_path}: "
            f"expected {expected_sha256[:16]}..., got {actual_sha256[:16]}..."
        )

    logger.info(
        "chunked_dataset_decrypted",
        extra={
            "chunk_group": chunk_group_path,
            "total_bytes": len(full_plaintext),
            "sha256_verified": True,
        },
    )

    return full_plaintext
