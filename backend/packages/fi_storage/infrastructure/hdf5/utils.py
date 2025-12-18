from __future__ import annotations

import h5py
import hashlib
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict


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
            f.create_dataset(
                f"/sessions/{session_id}/audio",
                data=audio_data,
                compression=compression,
                compression_opts=compression_opts,
            )

            f.attrs["session_id"] = session_id
            f.attrs["created_at"] = datetime.now(UTC).isoformat()
            f.attrs["format_version"] = "1.0"

            f.flush()
            _fsync_file_descriptor(f.fileno())

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
            try:
                temp_path.unlink()
            except OSError:
                pass

