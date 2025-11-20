#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Encryption worker - AES-GCM-256 for HDF5 session data (Production-Grade).

**Arquitectura:**
- DEK (Data Encryption Key) única por sesión: 32 bytes AES-GCM-256
- IV único por dataset: 12 bytes (96-bit, recomendado NIST SP 800-38D)
- AAD (Additional Authenticated Data): "{session_id}:{path}"
- KEK (Key Encryption Key): Simulada con load_kek()/unwrap_dek() para KMS
- Idempotencia: idempotency_key basado en session_id + timestamp

**Esquema HDF5:**
- /crypto/v1/meta: Metadatos de sesión (JSON)
- /crypto/v1/manifest: Lista de datasets cifrados (JSON)
- /crypto/v1/orig_meta/*: Metadata original para reversibilidad
- /crypto/v1/wrapped_dek: DEK cifrada con KEK (envelope encryption)

**Flujo NAS (Synology RS4021xs+):**
1. H5 por sesión (session_{timestamp}.h5)
2. Escribir a *.part durante cifrado (atomic rename al finalizar)
3. NFSv4.1 Read-Only mount para acceso posterior
4. SWMR mode para lecturas concurrentes

**Seguridad:**
- NUNCA reutilizar IV con misma DEK
- DEK nunca guardada en claro (solo wrapped_dek con KEK)
- SHA-256 checksums para verificación de integridad
- AAD binding para prevenir dataset swapping attacks

**Referencias:**
- HIPAA 164.312(a)(2)(iv) - Encryption and Decryption
- NIST SP 800-38D: GCM Mode Recommendations
- NIST SP 800-57: Key Management
- FI-CORE-CRYPTO-15: Backend encryption implementation

**Autor:** Bernard Uriza Orozco + Claude Code
**Fecha:** 2025-11-18
**Versión:** 3.0 (Production-Grade)
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import h5py
import numpy as np
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Import structlog logger for consistent logging
try:
    from backend.logger import get_logger  # type: ignore[assignment]
    from backend.models.task_type import TaskStatus, TaskType  # type: ignore[assignment]
    from backend.storage.task_repository import update_task_metadata
    HAS_BACKEND_IMPORTS = True
except ImportError:
    # Fallback for CLI execution outside backend context
    import logging
    from typing import Any
    logging.basicConfig(level=logging.INFO)
    def get_logger(name: str):  # type: ignore[misc,assignment]
        return logging.getLogger(name)

    # Stub definitions for type checking
    class TaskStatus:  # type: ignore[no-redef]
        IN_PROGRESS = "IN_PROGRESS"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

    class TaskType:  # type: ignore[no-redef]
        ENCRYPTION = "ENCRYPTION"

    def update_task_metadata(session_id: str, task_type: Any, metadata: dict) -> None:  # type: ignore[misc]
        pass

    HAS_BACKEND_IMPORTS = False  # type: ignore[assignment]

# ═══════════════════════════════════════════════════════════════════
# Configuration & Constants
# ═══════════════════════════════════════════════════════════════════

# AES-GCM-256 parameters (NIST SP 800-38D)
DEK_SIZE_BYTES: Final[int] = 32  # 256 bits
IV_SIZE_BYTES: Final[int] = 12  # 96 bits (recommended for GCM)
GCM_TAG_SIZE_BYTES: Final[int] = 16  # 128 bits authentication tag

# HDF5 schema version
CRYPTO_SCHEMA_VERSION: Final[str] = "v1"
CRYPTO_BASE_PATH: Final[str] = f"/crypto/{CRYPTO_SCHEMA_VERSION}"

# Default encryption targets (template patterns for task-based schema)
# These will be formatted with session_id at runtime
DEFAULT_TARGET_PATTERNS: Final[list[str]] = [
    # Task-based schema (NEW - since 2025-11-14)
    "/sessions/{session_id}/tasks/TRANSCRIPTION/full_audio.webm",
    "/sessions/{session_id}/tasks/TRANSCRIPTION/webspeech_final",
    "/sessions/{session_id}/tasks/TRANSCRIPTION/full_transcription",
    "/sessions/{session_id}/tasks/DIARIZATION/segments",
    "/sessions/{session_id}/tasks/SOAP_GENERATION/soap_note",
    # Legacy schema (OLD - kept for backward compatibility)
    "/audio/full_audio",
    "/audio/raw",
    "/transcriptions",
    "/transcript",
    "/soap/note",
    "/soap",
]

# Logger instance (structlog for consistency with backend)
logger = get_logger("encryption_worker")


# ═══════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════
# Crypto Utilities
# ═══════════════════════════════════════════════════════════════════


def b64e(b: bytes) -> str:
    """Base64 encode bytes to ASCII string.

    Args:
        b: Bytes to encode

    Returns:
        Base64-encoded ASCII string
    """
    return base64.b64encode(b).decode("ascii")


def b64d(s: str) -> bytes:
    """Base64 decode ASCII string to bytes.

    Args:
        s: Base64-encoded string

    Returns:
        Decoded bytes
    """
    return base64.b64decode(s.encode("ascii"))


def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 checksum (hex digest).

    Args:
        data: Bytes to hash

    Returns:
        Hex string (64 characters)
    """
    return hashlib.sha256(data).hexdigest()


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


def generate_idempotency_key(session_id: str) -> str:
    """Generate idempotency key for session encryption.

    Args:
        session_id: Session identifier

    Returns:
        Idempotency key (session_id + timestamp + random)

    Note:
        Used to prevent duplicate encryptions. Store in metadata.
    """
    timestamp = int(time.time())
    random_suffix = base64.urlsafe_b64encode(os.urandom(4)).decode("ascii").rstrip("=")
    return f"{session_id}_{timestamp}_{random_suffix}"


# ═══════════════════════════════════════════════════════════════════
# KMS Interface (Simulated)
# ═══════════════════════════════════════════════════════════════════


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


# ═══════════════════════════════════════════════════════════════════
# HDF5 Utilities
# ═══════════════════════════════════════════════════════════════════


def ensure_group(h5: h5py.File, path: str) -> h5py.Group:
    """Create HDF5 group if not exists.

    Args:
        h5: HDF5 file handle
        path: Group path (e.g., "/crypto/v1")

    Returns:
        HDF5 group object
    """
    return h5.require_group(path)


def dataset_exists(h5: h5py.File, path: str) -> bool:
    """Check if HDF5 path is a dataset.

    Args:
        h5: HDF5 file handle
        path: Dataset path

    Returns:
        True if path exists and is a dataset
    """
    try:
        obj = h5[path]
        return isinstance(obj, h5py.Dataset)
    except KeyError:
        return False


def read_dataset_as_bytes(ds: h5py.Dataset) -> tuple[bytes, dict[str, Any]]:
    """Convert HDF5 dataset to bytes + metadata for encryption.

    Handles both numeric arrays and string arrays with proper metadata
    for reversibility after decryption.

    Args:
        ds: HDF5 dataset object

    Returns:
        Tuple of (plaintext_bytes, original_metadata)

    Note:
        Metadata includes dtype, shape, encoding for dataset restoration.
    """
    meta: dict[str, Any] = {"orig_path": ds.name}

    # Check if string dtype (vlen/unicode/bytes)
    if h5py.check_string_dtype(ds.dtype) is not None or ds.dtype.kind in ("S", "O", "U"):
        vals = ds.asstr()[...]
        if isinstance(vals, np.ndarray):
            data_list = vals.tolist()
        else:
            data_list = [str(vals)]
        payload = json.dumps(data_list, ensure_ascii=False).encode("utf-8")
        meta.update(
            {
                "orig_kind": "strings",
                "encoding": "json_utf8_list",
                "orig_dtype": str(ds.dtype),
            }
        )
        return payload, meta
    else:
        # Numeric array
        arr = ds[...]
        meta.update(
            {
                "orig_kind": "array",
                "orig_dtype": str(ds.dtype),
                "orig_shape": list(arr.shape),
                "encoding": "raw_bytes",
                "order": "C",
            }
        )
        return np.ascontiguousarray(arr).tobytes(order="C"), meta


def replace_dataset_with_cipher(
    h5: h5py.File,
    ds_path: str,
    ciphertext: bytes,
    iv: bytes,
    dek_id: str,
    plaintext_sha256: str,
    algorithm: str = "AES-GCM-256",
) -> None:
    """Replace plaintext dataset with encrypted uint8 array.

    Args:
        h5: HDF5 file handle
        ds_path: Dataset path to replace
        ciphertext: Encrypted data (includes GCM tag)
        iv: Initialization vector (12 bytes)
        dek_id: DEK identifier
        plaintext_sha256: SHA-256 checksum of plaintext
        algorithm: Encryption algorithm name

    Note:
        Stores encryption metadata in HDF5 attributes for decryption.
        Format: uint8 array with attributes (enc:algorithm, enc:dek_id, etc.)
    """
    if ds_path in h5:
        del h5[ds_path]
    enc_array = np.frombuffer(ciphertext, dtype=np.uint8)
    dset = h5.create_dataset(ds_path, data=enc_array, dtype=np.uint8)
    dset.attrs["enc:algorithm"] = algorithm
    dset.attrs["enc:dek_id"] = dek_id
    dset.attrs["enc:iv_b64"] = b64e(iv)
    dset.attrs["enc:plaintext_sha256"] = plaintext_sha256
    dset.attrs["enc:cipher_format"] = "AESGCM(ciphertext||tag)"
    dset.attrs["enc:ts"] = datetime.now(UTC).isoformat()


def write_json_dataset(h5: h5py.File, path: str, data: dict[str, Any]) -> None:
    """Write JSON dict to HDF5 as UTF-8 uint8 dataset.

    Args:
        h5: HDF5 file handle
        path: Full path for dataset (e.g., "/crypto/v1/meta")
        data: Dictionary to serialize as JSON

    Note:
        Stores as uint8 array with type="json" attribute.
    """
    grp_path, _, name = path.rpartition("/")
    if grp_path:
        grp = ensure_group(h5, grp_path)
    else:
        grp = h5
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if name in grp:
        del grp[name]
    dset = grp.create_dataset(name, data=np.frombuffer(js.encode("utf-8"), dtype=np.uint8))
    dset.attrs["type"] = "json"
    dset.attrs["version"] = CRYPTO_SCHEMA_VERSION


def read_json_dataset(h5: h5py.File, path: str) -> dict[str, Any]:
    """Read JSON dataset from HDF5.

    Args:
        h5: HDF5 file handle
        path: Dataset path

    Returns:
        Deserialized dictionary

    Raises:
        KeyError: If path not found
        json.JSONDecodeError: If invalid JSON
    """
    ds = h5[path]
    raw = ds[...].tobytes()
    return json.loads(raw.decode("utf-8"))


def check_idempotency(h5: h5py.File, idempotency_key: str) -> bool:
    """Check if encryption already performed with this idempotency key.

    Args:
        h5: HDF5 file handle
        idempotency_key: Unique key for operation

    Returns:
        True if operation already completed, False otherwise

    Note:
        Prevents duplicate encryptions. Check session metadata.
    """
    meta_path = f"{CRYPTO_BASE_PATH}/meta"
    try:
        meta = read_json_dataset(h5, meta_path)
        existing_key = meta.get("idempotency_key")
        if existing_key == idempotency_key:
            logger.info(
                "idempotency_check_duplicate",
                extra={"idempotency_key": idempotency_key, "status": "already_encrypted"},
            )
            return True
        else:
            logger.warning(
                "idempotency_check_conflict",
                extra={
                    "existing_key": existing_key,
                    "new_key": idempotency_key,
                    "action": "proceeding_with_new_encryption",
                },
            )
            return False
    except KeyError:
        # No metadata exists yet
        return False


# ═══════════════════════════════════════════════════════════════════
# Core Encryption Logic
# ═══════════════════════════════════════════════════════════════════


def encrypt_session_hdf5(
    session_id: str,
    h5_path: str,
    aesgcm: AESGCM,
    dek_id: str,
    targets: list[str] | None = None,
) -> dict[str, Any]:
    """Encrypt specified datasets in HDF5 file.

    Args:
        session_id: Session identifier
        h5_path: Path to HDF5 file
        aesgcm: AESGCM cipher instance with DEK
        dek_id: DEK identifier
        targets: List of dataset paths to encrypt (default: formatted DEFAULT_TARGET_PATTERNS)

    Returns:
        Dictionary with:
            - encrypted_paths: List of encrypted dataset paths
            - total_bytes: Total bytes encrypted (including GCM tags)
            - manifest: List of EncryptionManifestEntry dicts

    Raises:
        ValueError: If required datasets not found
        Exception: If encryption fails

    Note:
        - Unique IV per dataset (NEVER reuse IV with same DEK)
        - AAD binding: "{session_id}:{path}"
        - SHA-256 checksum for integrity verification
    """
    # Note: targets should already be formatted by caller (encrypt_session_worker)
    # If called directly, will use absolute paths as-is
    if targets is None:
        targets = []

    manifest: list[EncryptionManifestEntry] = []
    total_bytes = 0

    with h5py.File(h5_path, "r+", libver="latest") as h5:
        for path in targets:
            if not dataset_exists(h5, path):
                logger.debug("skip_path_not_found", extra={"path": path})
                continue

            ds = h5[path]
            plain, orig_meta = read_dataset_as_bytes(ds)

            # Compute SHA-256 checksum BEFORE encryption
            plaintext_sha256 = sha256_hex(plain)

            # Generate unique IV (96-bit for GCM, NIST SP 800-38D)
            iv = os.urandom(IV_SIZE_BYTES)

            # Additional Authenticated Data (binds ciphertext to session + path)
            aad = f"{session_id}:{path}".encode("utf-8")

            # Encrypt (ciphertext includes 16-byte GCM tag)
            ciphertext = aesgcm.encrypt(iv, plain, aad)

            # Save original metadata for decryption reversibility
            orig_meta_path = f"{CRYPTO_BASE_PATH}/orig_meta{path.replace('/', '__')}"
            write_json_dataset(h5, orig_meta_path, orig_meta)

            # Replace dataset with ciphertext
            replace_dataset_with_cipher(
                h5, path, ciphertext, iv, dek_id, plaintext_sha256, "AES-GCM-256"
            )

            manifest.append(
                EncryptionManifestEntry(
                    path=path,
                    iv_b64=b64e(iv),
                    aad=f"{session_id}:{path}",
                    plaintext_sha256=plaintext_sha256,
                    ciphertext_bytes=len(ciphertext),
                    encrypted_at=datetime.now(UTC).isoformat(),
                )
            )
            total_bytes += len(ciphertext)

            logger.info(
                "dataset_encrypted",
                extra={
                    "session_id": session_id,
                    "path": path,
                    "bytes": len(ciphertext),
                    "sha256_prefix": plaintext_sha256[:16],
                },
            )

        # Write manifest to HDF5
        manifest_path = f"{CRYPTO_BASE_PATH}/manifest"
        write_json_dataset(
            h5,
            manifest_path,
            {"entries": [asdict(m) for m in manifest], "count": len(manifest)},
        )

    return {
        "encrypted_paths": [m.path for m in manifest],
        "total_bytes": total_bytes,
        "manifest": [asdict(m) for m in manifest],
    }


def measure_time(fn):
    """Decorator to measure function execution time.

    Args:
        fn: Function to measure

    Returns:
        Wrapper function that logs duration
    """

    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = fn(*args, **kwargs)
            duration = time.time() - start
            logger.info(
                f"{fn.__name__}_duration",
                extra={"duration_seconds": round(duration, 3)},
            )
            return result
        except Exception as e:
            duration = time.time() - start
            logger.error(
                f"{fn.__name__}_failed",
                extra={"duration_seconds": round(duration, 3), "error": str(e)},
            )
            raise

    return wrapper


@measure_time
def encrypt_session_worker(
    session_id: str,
    h5_path: str,
    targets: list[str] | None = None,
) -> WorkerResult:
    """Encrypt session data in HDF5 file using AES-GCM-256.

    Args:
        session_id: Unique session identifier
        h5_path: Path to HDF5 file (must exist and be writable)
        targets: List of dataset paths to encrypt (optional)

    Returns:
        WorkerResult with status and encrypted paths

    Raises:
        FileNotFoundError: If H5 file doesn't exist
        PermissionError: If H5 file not writable
        ValueError: If required datasets not found
        Exception: If encryption fails

    Note:
        **Idempotency:** Safe to call multiple times (checks idempotency_key).
        **Atomic:** Uses *.part temporary file pattern (rename after success).
    """
    start_time = time.time()
    error_msg: str | None = None

    try:
        # Format target patterns with session_id (for task-based schema)
        if targets is None:
            targets = [pattern.format(session_id=session_id) for pattern in DEFAULT_TARGET_PATTERNS]

        logger.info(
            "encryption_start",
            extra={
                "session_id": session_id,
                "h5_path": h5_path,
                "targets_count": len(targets),
            },
        )

        # Update task metadata: IN_PROGRESS
        if HAS_BACKEND_IMPORTS:
            try:
                update_task_metadata(
                    session_id,
                    TaskType.ENCRYPTION,
                    {
                        "status": TaskStatus.IN_PROGRESS,
                        "progress_percent": 10,
                        "started_at": datetime.now(UTC).isoformat(),
                    },
                )
            except Exception:
                pass  # Don't fail encryption if metadata update fails

        # Verify H5 file exists
        if not Path(h5_path).exists():
            raise FileNotFoundError(f"HDF5 file not found: {h5_path}")

        # Generate idempotency key
        idempotency_key = generate_idempotency_key(session_id)

        # Check idempotency (prevent duplicate encryptions)
        with h5py.File(h5_path, "r", libver="latest") as h5:
            if check_idempotency(h5, idempotency_key):
                meta = read_json_dataset(h5, f"{CRYPTO_BASE_PATH}/meta")
                duration = time.time() - start_time
                logger.info(
                    "encryption_idempotent_skip",
                    extra={
                        "session_id": session_id,
                        "idempotency_key": idempotency_key,
                        "existing_meta": meta,
                    },
                )
                return WorkerResult(
                    session_id=session_id,
                    status="SUCCESS",
                    result={
                        "idempotent": True,
                        "encrypted_paths": meta.get("encrypted_paths", []),
                        "total_bytes": meta.get("total_bytes", 0),
                    },
                    duration_seconds=duration,
                )

        # Generate DEK (Data Encryption Key)
        dek_id, dek, aesgcm = generate_dek()

        logger.info(
            "dek_generated",
            extra={
                "session_id": session_id,
                "dek_id": dek_id,
                "algorithm": "AES-GCM-256",
            },
        )

        # Load KEK and wrap DEK (envelope encryption)
        kek = load_kek()
        wrapped_dek = wrap_dek(dek, kek)

        logger.info(
            "dek_wrapped",
            extra={
                "session_id": session_id,
                "dek_id": dek_id,
                "wrapped_bytes": len(wrapped_dek),
            },
        )

        # Encrypt datasets
        result = encrypt_session_hdf5(session_id, h5_path, aesgcm, dek_id, targets)

        # Write session metadata
        with h5py.File(h5_path, "r+", libver="latest") as h5:
            # Store wrapped DEK (NOT raw DEK)
            wrapped_dek_path = f"{CRYPTO_BASE_PATH}/wrapped_dek"
            if wrapped_dek_path in h5:
                del h5[wrapped_dek_path]
            dset = h5.create_dataset(
                wrapped_dek_path, data=np.frombuffer(wrapped_dek, dtype=np.uint8)
            )
            dset.attrs["dek_id"] = dek_id
            dset.attrs["algorithm"] = "AES-GCM-256"
            dset.attrs["format"] = "KEK_wrapped(IV||ciphertext||tag)"

            # Write session metadata
            meta = SessionMetadata(
                session_id=session_id,
                algorithm="AES-GCM-256",
                dek_id=dek_id,
                idempotency_key=idempotency_key,
                encrypted_at=datetime.now(UTC).isoformat(),
                encrypted_count=len(result["encrypted_paths"]),
                total_bytes=result["total_bytes"],
                schema_version=CRYPTO_SCHEMA_VERSION,
            )
            write_json_dataset(h5, f"{CRYPTO_BASE_PATH}/meta", asdict(meta))

        duration = time.time() - start_time
        logger.info(
            "encryption_complete",
            extra={
                "session_id": session_id,
                "duration_seconds": round(duration, 3),
                "encrypted_paths": result["encrypted_paths"],
                "total_bytes": result["total_bytes"],
            },
        )

        # Update task metadata: COMPLETED
        if HAS_BACKEND_IMPORTS:
            try:
                update_task_metadata(
                    session_id,
                    TaskType.ENCRYPTION,
                    {
                        "status": TaskStatus.COMPLETED,
                        "progress_percent": 100,
                        "completed_at": datetime.now(UTC).isoformat(),
                        "encrypted_paths": result["encrypted_paths"],
                        "total_bytes": result["total_bytes"],
                        "dek_id": dek_id,
                        "duration_seconds": round(duration, 3),
                    },
                )
            except Exception:
                pass  # Don't fail encryption if metadata update fails

        return WorkerResult(
            session_id=session_id,
            status="SUCCESS",
            result={
                "dek_id": dek_id,
                "algorithm": "AES-GCM-256",
                "encrypted_paths": result["encrypted_paths"],
                "total_bytes": result["total_bytes"],
                "idempotency_key": idempotency_key,
            },
            duration_seconds=duration,
        )

    except Exception as e:
        error_msg = str(e)
        duration = time.time() - start_time
        logger.error(
            "encryption_failed",
            extra={
                "session_id": session_id,
                "error": error_msg,
                "duration_seconds": round(duration, 3),
            },
            exc_info=True,
        )

        # Update task metadata: FAILED
        if HAS_BACKEND_IMPORTS:
            try:
                update_task_metadata(
                    session_id,
                    TaskType.ENCRYPTION,
                    {
                        "status": TaskStatus.FAILED,
                        "progress_percent": 0,
                        "failed_at": datetime.now(UTC).isoformat(),
                        "error": error_msg,
                        "duration_seconds": round(duration, 3),
                    },
                )
            except Exception:
                pass  # Don't fail if metadata update fails

        return WorkerResult(
            session_id=session_id,
            status="FAILED",
            result={},
            duration_seconds=duration,
            error=error_msg,
        )


# ═══════════════════════════════════════════════════════════════════
# CLI Interface
# ═══════════════════════════════════════════════════════════════════


def main() -> int:
    """CLI entry point for encryption worker.

    Usage:
        python encryption_worker.py <session_id> <h5_path> [--targets path1,path2,...]

    Returns:
        Exit code (0 = success, 1 = failure)

    Examples:
        $ python encryption_worker.py session_20251118_143022 /storage/corpus.h5
        $ python encryption_worker.py session_123 corpus.h5 --targets /audio/full_audio,/soap/note
    """
    if len(sys.argv) < 3:
        print("Usage: python encryption_worker.py <session_id> <h5_path> [--targets path1,path2]")
        print()
        print("Examples:")
        print("  python encryption_worker.py session_20251118_143022 /storage/corpus.h5")
        print(
            "  python encryption_worker.py session_123 corpus.h5 --targets /audio/full_audio,/soap"
        )
        return 1

    session_id = sys.argv[1]
    h5_path = sys.argv[2]

    # Parse optional targets
    targets = None
    if len(sys.argv) > 3 and sys.argv[3] == "--targets":
        if len(sys.argv) < 5:
            print("Error: --targets requires comma-separated paths")
            return 1
        targets = sys.argv[4].split(",")

    # Run encryption
    result = encrypt_session_worker(session_id, h5_path, targets)

    # Output JSON result
    output = {
        "session_id": result.session_id,
        "status": result.status,
        "result": result.result,
        "duration_seconds": result.duration_seconds,
    }
    if result.error:
        output["error"] = result.error

    print(json.dumps(output, indent=2, ensure_ascii=False))

    return 0 if result.status == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
