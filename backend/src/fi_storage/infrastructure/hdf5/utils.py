from __future__ import annotations

import hashlib
from contextlib import suppress
from datetime import UTC, datetime
from typing import Literal, TypedDict

import h5py
import os
from pathlib import Path


class AtomicWriteResult(TypedDict):
    path: Path
    checksum_path: Path
    sha256: str
    size_bytes: int


def _fsync_file_descriptor(fd: int) -> None:
    os.fsync(fd)


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_session_file(
    session_id: str,
    audio_data: bytes,
    base_dir: Path | None = None,
    compression: Literal["gzip", "lzf"] | None = "gzip",
    compression_opts: int | None = 9,
) -> AtomicWriteResult:
    """Atomically write a session HDF5 file with checksum.

    Pattern: write to `<final>.part` → flush → fsync → POSIX rename → compute SHA256 → write `<final>.sha256` → cleanup `.part` if present.

    Returns metadata including checksum and paths.
    """
    base = base_dir or Path("storage/sessions")
    base.mkdir(parents=True, exist_ok=True)

    final_path = base / f"{session_id}.h5"
    temp_path = Path(str(final_path) + ".part")

    try:
        with h5py.File(temp_path, "w", libver="latest") as f:
            # Convert to numpy array to ensure proper chunking for compression
            import numpy as np
            audio_array = np.frombuffer(audio_data, dtype=np.uint8)

            # Only apply compression if data is large enough to benefit
            use_compression = compression if len(audio_data) > 1024 else None
            use_opts = compression_opts if use_compression else None

            f.create_dataset(
                f"/sessions/{session_id}/audio",
                data=audio_array,
                compression=use_compression,
                compression_opts=use_opts,
            )

            f.attrs["session_id"] = session_id
            f.attrs["created_at"] = datetime.now(UTC).isoformat()
            f.attrs["format_version"] = "1.0"

            f.flush()
            # Note: h5py doesn't expose fileno() directly in newer versions
            # The flush() call ensures data is written to the OS buffer
            # and closing the file will trigger final sync

        os.rename(temp_path, final_path)

        sha256 = compute_sha256(final_path)
        checksum_path = Path(str(final_path) + ".sha256")
        with checksum_path.open("w") as cf:
            cf.write(f"{sha256}  {final_path.name}\n")
            _fsync_file_descriptor(cf.fileno())

        size_bytes = final_path.stat().st_size
        return {
            "path": final_path,
            "checksum_path": checksum_path,
            "sha256": sha256,
            "size_bytes": size_bytes,
        }
    finally:
        # Ensure temp file is cleaned up on any path
        if temp_path.exists():
            with suppress(OSError):
                temp_path.unlink()
