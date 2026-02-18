"""HDF5 utility functions for encryption operations.

Helper functions for HDF5 dataset operations, group management, and
data serialization/deserialization.

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from encryption_worker.py)
Card: Infrastructure Modularization - Quick Wins (Enceladus Moon)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import h5py
import numpy as np

from backend.infrastructure.workers.tasks.encryption.constants import CRYPTO_SCHEMA_VERSION
from backend.infrastructure.workers.tasks.encryption.crypto import b64e


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
        data_list = vals.tolist() if isinstance(vals, np.ndarray) else [str(vals)]
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
    grp = ensure_group(h5, grp_path) if grp_path else h5
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
