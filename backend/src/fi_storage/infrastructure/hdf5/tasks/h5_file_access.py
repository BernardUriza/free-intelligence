"""Low-level HDF5 file access with SWMR mode support.

SWMR = Single Writer Multiple Readers.
Allows concurrent reads while one thread writes.

This module provides the foundational primitives for thread-safe HDF5 access
used by all other task modules.

Author: Bernard Uriza Orozco
Created: 2025-11-14
Refactored: 2026-01-18 (modularization)
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager

import h5py
from backend.src.fi_storage.infrastructure.hdf5.session_h5_manager import CORPUS_PATH

# Global lock for HDF5 file access (HDF5 is not thread-safe for concurrent writes)
# Using RLock to allow same thread to acquire lock multiple times
_h5_lock = threading.RLock()


@contextmanager
def open_h5_read() -> Iterator[h5py.File]:
    """Open HDF5 in SWMR read mode (allows concurrent writer).

    SWMR = Single Writer Multiple Readers.
    Multiple threads can read while one thread writes.
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _h5_lock:
        f = h5py.File(CORPUS_PATH, "r", swmr=True, libver="latest")
        try:
            yield f  # type: ignore[misc]
        finally:
            f.close()


@contextmanager
def open_h5_write() -> Iterator[h5py.File]:
    """Open HDF5 in SWMR write mode (allows concurrent readers).

    SWMR = Single Writer Multiple Readers.
    One writer can write while multiple readers read.
    """
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _h5_lock:
        f = h5py.File(CORPUS_PATH, "a", libver="latest")
        try:
            # Enable SWMR write mode AFTER opening
            if not f.swmr_mode:  # type: ignore[attr-defined]
                f.swmr_mode = True  # type: ignore[attr-defined]
            yield f  # type: ignore[misc]
        finally:
            f.close()


__all__ = [
    "_h5_lock",
    "open_h5_read",
    "open_h5_write",
]
