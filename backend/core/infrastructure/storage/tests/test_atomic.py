from __future__ import annotations

from backend.core.infrastructure.storage.infrastructure.atomic import (
    atomic_write_session_file,
    compute_sha256,
)
from pathlib import Path


def test_atomic_write_and_checksum(tmp_path: Path):
    session_id = "unit-atomic-001"
    audio = b"test-bytes-audio"
    final = tmp_path / f"{session_id}.h5"

    result = atomic_write_session_file(session_id, audio, final_path=final)

    assert Path(result["path"]).exists()
    checksum_path = Path(result["path"] + ".sha256")
    assert checksum_path.exists()

    # verify compute_sha256 matches stored value
    digest = compute_sha256(result["path"])
    assert digest == result["checksum"]

    # verify temp file cleaned up
    assert not Path(str(final) + ".part").exists()
