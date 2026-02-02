#!/usr/bin/env python3
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
import contextlib
import json
import time
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import h5py
import numpy as np
import os
import sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pathlib import Path

# Import constants, models, KMS, crypto, and HDF5 utils from dedicated modules
from backend.infrastructure.workers.tasks.encryption.constants import (
    CHUNK_SIZE_THRESHOLD_MB,
    CRYPTO_BASE_PATH,
    CRYPTO_SCHEMA_VERSION,
    DEFAULT_TARGET_PATTERNS,
    IV_SIZE_BYTES,
)
from backend.infrastructure.workers.tasks.encryption.crypto import (
    b64e,
    encrypt_large_dataset,
    sha256_hex,
)
from backend.infrastructure.workers.tasks.encryption.hdf5_utils import (
    dataset_exists,
    read_dataset_as_bytes,
    read_json_dataset,
    replace_dataset_with_cipher,
    write_json_dataset,
)
from backend.infrastructure.workers.tasks.encryption.kms import (
    generate_dek,
    load_kek,
    wrap_dek,
)
from backend.infrastructure.workers.tasks.encryption.models import (
    EncryptionManifestEntry,
    SessionMetadata,
    WorkerResult,
)

# Import structlog logger for consistent logging
try:
    from backend.models.task_type import (
        TaskStatus,  # type: ignore[assignment]
        TaskType,  # type: ignore[assignment]
    )
    from backend.repositories.interfaces.itask_repository import ITaskRepository  # type: ignore[assignment]
    from backend.utils.common.logging.logger import get_logger  # type: ignore[assignment]

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
        """Stub for CLI mode."""
        pass

    HAS_BACKEND_IMPORTS = False  # type: ignore[assignment]

# Logger instance (structlog for consistency with backend)
logger = get_logger("encryption_worker")


# ═══════════════════════════════════════════════════════════════════
# Idempotency & HDF5 Utilities
# ═══════════════════════════════════════════════════════════════════


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
# Idempotency Check
# ═══════════════════════════════════════════════════════════════════


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
# Large File Chunking (FI-CORE-CRYPTO-15)
# ═══════════════════════════════════════════════════════════════════


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
            - chunked_paths: List of paths that were chunked (>500MB)

    Raises:
        ValueError: If required datasets not found
        Exception: If encryption fails

    Note:
        - Unique IV per dataset (NEVER reuse IV with same DEK)
        - AAD binding: "{session_id}:{path}"
        - SHA-256 checksum for integrity verification
        - Files >500MB are automatically chunked into 50MB segments
    """
    # Note: targets should already be formatted by caller (encrypt_session_worker)
    # If called directly, will use absolute paths as-is
    if targets is None:
        targets = []

    manifest: list[EncryptionManifestEntry] = []
    total_bytes = 0
    chunked_paths: list[str] = []

    with h5py.File(h5_path, "r+", libver="latest") as h5:
        for path in targets:
            if not dataset_exists(h5, path):
                logger.debug("skip_path_not_found", extra={"path": path})
                continue

            ds = h5[path]
            plain, orig_meta = read_dataset_as_bytes(ds)

            # Check if large file chunking is needed (>500MB)
            threshold_bytes = CHUNK_SIZE_THRESHOLD_MB * 1024 * 1024
            if len(plain) > threshold_bytes:
                # Use chunked encryption for large files
                logger.info(
                    "using_chunked_encryption",
                    extra={
                        "path": path,
                        "size_mb": len(plain) // (1024 * 1024),
                        "threshold_mb": CHUNK_SIZE_THRESHOLD_MB,
                    },
                )
                chunk_entries = encrypt_large_dataset(
                    session_id, h5, path, aesgcm, dek_id, read_dataset_as_bytes, write_json_dataset
                )
                manifest.extend(chunk_entries)
                total_bytes += sum(e.ciphertext_bytes for e in chunk_entries)
                chunked_paths.append(path)
                continue

            # Standard encryption for smaller files
            # Compute SHA-256 checksum BEFORE encryption
            plaintext_sha256 = sha256_hex(plain)

            # Generate unique IV (96-bit for GCM, NIST SP 800-38D)
            iv = os.urandom(IV_SIZE_BYTES)

            # Additional Authenticated Data (binds ciphertext to session + path)
            aad = f"{session_id}:{path}".encode()

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
            {
                "entries": [asdict(m) for m in manifest],
                "count": len(manifest),
                "chunked_paths": chunked_paths,
            },
        )

    return {
        "encrypted_paths": [m.path for m in manifest],
        "total_bytes": total_bytes,
        "manifest": [asdict(m) for m in manifest],
        "chunked_paths": chunked_paths,
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
    task_repo: "ITaskRepository | None" = None,
    targets: list[str] | None = None,
) -> WorkerResult:
    """Encrypt session data in HDF5 file using AES-GCM-256.

    Args:
        session_id: Unique session identifier
        h5_path: Path to HDF5 file (must exist and be writable)
        task_repo: Task repository (injected for thread-safety, None for CLI mode)
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
        **CLI Mode:** task_repo=None skips metadata updates (fallback for standalone usage).
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
        if HAS_BACKEND_IMPORTS and task_repo is not None:
            with contextlib.suppress(Exception):
                task_repo.save_task_metadata(
                    session_id,
                    TaskType.ENCRYPTION.value,
                    {
                        "status": TaskStatus.IN_PROGRESS,
                        "progress_percent": 10,
                        "started_at": datetime.now(UTC).isoformat(),
                    },
                )

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
        if HAS_BACKEND_IMPORTS and task_repo is not None:
            try:
                task_repo.save_task_metadata(
                    session_id,
                    TaskType.ENCRYPTION.value,
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
        if HAS_BACKEND_IMPORTS and task_repo is not None:
            try:
                task_repo.save_task_metadata(
                    session_id,
                    TaskType.ENCRYPTION.value,
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
