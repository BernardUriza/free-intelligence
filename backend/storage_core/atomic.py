from __future__ import annotations

import h5py
import hashlib
import os
import structlog
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = structlog.get_logger(__name__)


def compute_sha256(file_path: str | os.PathLike[str]) -> str:
    """Compute SHA256 for a file and return hex digest."""
    path = Path(file_path)
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_session_file(
    session_id: str,
    audio_bytes: bytes,
    final_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """
    Atomically write a session HDF5 file with audio and metadata, then persist checksum.

    - Writes to `<final>.part` first
    - Flushes and fsyncs
    - Renames to final path atomically (POSIX)
    - Stores checksum to `<final>.sha256`
    """
    if final_path is None:
        final_path = Path("storage/sessions") / f"{session_id}.h5"
    else:
        final_path = Path(final_path)

    final_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = final_path.with_suffix(final_path.suffix + ".part")

    try:
        with h5py.File(str(temp_path), "w", libver="latest") as f:
            dset = f.create_dataset(
                f"/sessions/{session_id}/audio",
                data=audio_bytes,
                compression="gzip",
                compression_opts=9,
            )
            f.attrs["session_id"] = session_id
            f.attrs["created_at"] = datetime.now(UTC).isoformat()
            f.attrs["format_version"] = "1.0"

            f.flush()
            os.fsync(f.fileno())

        os.rename(str(temp_path), str(final_path))

        checksum = compute_sha256(final_path)
        checksum_path = Path(str(final_path) + ".sha256")
        with checksum_path.open("w") as cf:
            cf.write(f"{checksum}  {final_path.name}\n")
            cf.flush()
            os.fsync(cf.fileno())

        logger.info(
            "session_saved",
            session_id=session_id,
            size_bytes=len(audio_bytes),
            checksum=checksum[:16],
            path=str(final_path),
        )
        return {
            "session_id": session_id,
            "path": str(final_path),
            "checksum": checksum,
        }

    except Exception as e:
        logger.error("session_save_failed", session_id=session_id, error=str(e))
        raise

    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
