"""
HDF5 Utility Functions

Centralized HDF5 access patterns to eliminate type: ignore comments
and standardize error handling for h5py operations.

File: backend/common/h5py_utils.py
Created: 2025-11-05
Card: FI-TECH-DEBT-005
"""

from __future__ import annotations

from typing import Any, Optional

import h5py

from backend.logger import get_logger

# Type alias for h5py.File (h5py doesn't expose Optional in its type stubs)
File = h5py.File

logger = get_logger(__name__)


def safe_decode_string(value: Any) -> str:
    """
    Safely decode bytes or convert to string.

    Handles both byte strings from HDF5 and native Python strings.
    Falls back gracefully on encoding errors.

    Args:
        value: Value to decode (bytes or string)

    Returns:
        Decoded UTF-8 string

    Examples:
        >>> safe_decode_string(b"hello")
        'hello'
        >>> safe_decode_string("already string")
        'already string'
    """
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "DECODE_FALLBACK",
                value_len=len(value),
                fallback="utf-8 with replace",
            )
            return value.decode("utf-8", errors="replace")
    return str(value)


def get_h5_string(group: h5py.Group | h5py.Dataset, field: str, index: int) -> str:
    """
    Safely retrieve and decode string from HDF5 group or dataset.

    Handles both Group[field][index] and Dataset[index] access patterns.

    Args:
        group: HDF5 group or dataset
        field: Field name in group (ignored if group is Dataset)
        index: Row index to retrieve

    Returns:
        Decoded string value

    Raises:
        KeyError: If field doesn't exist in group
        IndexError: If index out of bounds
        UnicodeDecodeError: If decoding fails (uses fallback)

    Examples:
        >>> get_h5_string(group, "text", 5)
        'Speaker A: Hello'
    """
    try:
        if isinstance(group, h5py.Dataset):
            value = group[index]
        else:
            value = group[field][index]

        return safe_decode_string(value)
    except (KeyError, IndexError, TypeError) as e:
        logger.error("H5PY_STRING_ACCESS_FAILED", field=field, index=index, error=str(e))
        raise


def get_h5_value(
    group: h5py.Group | h5py.Dataset,
    field: Optional[str],
    index: int,
    dtype: type,
) -> Any:
    """
    Generic HDF5 value accessor with type coercion.

    Retrieves values from HDF5 with automatic type conversion.
    Strings are decoded from bytes automatically.

    Args:
        group: HDF5 group or dataset
        field: Field name (None if group is Dataset)
        index: Row index
        dtype: Desired return type (str, int, float, bool, etc.)

    Returns:
        Value coerced to requested dtype

    Raises:
        KeyError: If field doesn't exist
        IndexError: If index out of bounds
        ValueError: If type coercion fails

    Examples:
        >>> get_h5_value(group, "event_id", 0, str)
        'evt_123456'
        >>> get_h5_value(group, "count", 0, int)
        42
    """
    try:
        if isinstance(group, h5py.Dataset):
            value = group[index]
        elif field is None:
            raise ValueError("field must be specified for h5py.Group")
        else:
            value = group[field][index]

        if dtype == str:
            return safe_decode_string(value)
        elif dtype in (int, float, bool):
            return dtype(value)
        return value
    except (KeyError, IndexError, TypeError, ValueError) as e:
        logger.error(
            "H5PY_VALUE_ACCESS_FAILED",
            field=field,
            index=index,
            dtype=dtype.__name__,
            error=str(e),
        )
        raise


def check_h5_group_exists(group: h5py.Group, path: str) -> bool:
    """
    Check if a path exists in HDF5 group.

    Safe wrapper around h5py existence checking.

    Args:
        group: HDF5 group
        path: Path to check (e.g., "/consultations/cons_123")

    Returns:
        True if path exists, False otherwise
    """
    try:
        return path in group
    except (KeyError, TypeError):
        return False


def safe_h5_read(filepath: str, mode: str = "r") -> File | None:
    """
    Safely open HDF5 file with error handling.

    Args:
        filepath: Path to HDF5 file
        mode: File mode ("r", "r+", "w", etc.)

    Returns:
        Open h5py.File or None if open fails

    Examples:
        >>> h5file = safe_h5_read("corpus.h5")
        >>> if h5file:
        ...     data = h5file["sessions"]
        ...     h5file.close()
    """
    try:
        return h5py.File(filepath, mode)
    except (OSError, TypeError) as e:
        logger.error("H5PY_FILE_OPEN_FAILED", filepath=filepath, mode=mode, error=str(e))
        return None
