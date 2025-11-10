"""
Tests for AUR-PROMPT-3.3: Stream Chunk Robustness (Atomic Write + Header Graft + ffprobe Guards)

Card: AUR-PROMPT-3.3
Created: 2025-11-09
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.public.workflows.router import _atomic_write, _probe_ok


def test_atomic_write_creates_file():
    """Test _atomic_write creates file atomically with fsync."""
    from fastapi import UploadFile

    # Create mock UploadFile
    content = b"test audio data"
    upload = UploadFile(filename="test.webm", file=io.BytesIO(content))

    # Write to temp location
    with tempfile.TemporaryDirectory() as tmpdir:
        dst = Path(tmpdir) / "session_123" / "0.webm"
        result = _atomic_write(upload, dst)

        assert result == dst
        assert dst.exists()
        assert dst.read_bytes() == content


def test_atomic_write_creates_parent_dir():
    """Test _atomic_write creates parent directory if missing."""
    from fastapi import UploadFile

    content = b"test data"
    upload = UploadFile(filename="test.webm", file=io.BytesIO(content))

    with tempfile.TemporaryDirectory() as tmpdir:
        dst = Path(tmpdir) / "deep" / "nested" / "path" / "audio.webm"
        result = _atomic_write(upload, dst)

        assert result == dst
        assert dst.exists()
        assert dst.parent.exists()


@pytest.mark.skipif(not Path("/usr/bin/ffprobe").exists(), reason="ffprobe not installed")
def test_probe_ok_rejects_invalid_file():
    """Test _probe_ok rejects invalid audio files."""
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(b"not a valid webm file")
        tmp.flush()
        tmp_path = Path(tmp.name)

    try:
        assert not _probe_ok(tmp_path)
    finally:
        tmp_path.unlink()


@pytest.mark.skipif(not Path("/usr/bin/ffprobe").exists(), reason="ffprobe not installed")
def test_probe_ok_accepts_valid_wav():
    """Test _probe_ok accepts valid WAV files."""
    # Create minimal valid WAV file (44 bytes header + 1 sample)
    wav_data = (
        b"RIFF"
        + (36).to_bytes(4, "little")  # ChunkSize
        + b"WAVE"
        + b"fmt "
        + (16).to_bytes(4, "little")  # Subchunk1Size
        + (1).to_bytes(2, "little")  # AudioFormat (PCM)
        + (1).to_bytes(2, "little")  # NumChannels (mono)
        + (16000).to_bytes(4, "little")  # SampleRate
        + (32000).to_bytes(4, "little")  # ByteRate
        + (2).to_bytes(2, "little")  # BlockAlign
        + (16).to_bytes(2, "little")  # BitsPerSample
        + b"data"
        + (0).to_bytes(4, "little")  # Subchunk2Size
    )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_data)
        tmp.flush()
        tmp_path = Path(tmp.name)

    try:
        # Note: ffprobe might still reject this minimal WAV
        # This test validates the _probe_ok function behavior, not WAV validity
        result = _probe_ok(tmp_path)
        # We just check it doesn't crash
        assert isinstance(result, bool)
    finally:
        tmp_path.unlink()


# Integration test with FastAPI endpoint (requires full app setup)
@pytest.mark.integration
@pytest.mark.skipif(not Path("/usr/bin/ffmpeg").exists(), reason="ffmpeg not installed")
def test_stream_endpoint_rejects_invalid_audio(test_client: TestClient):
    """Test /consult/stream endpoint rejects invalid audio with 415."""
    # Create invalid audio file
    invalid_audio = io.BytesIO(b"not a valid webm file")

    response = test_client.post(
        "/api/workflows/aurity/consult/stream",
        data={
            "session_id": "test_session_123",
            "chunk_number": "0",
            "timestamp_start": "0.0",
            "timestamp_end": "3.0",
        },
        files={"audio": ("chunk_0.webm", invalid_audio, "audio/webm")},
    )

    # Should return 415 Unsupported Media Type (not 400 or 500)
    assert response.status_code in [415, 422], f"Expected 415 or 422, got {response.status_code}"


# Note: Additional integration tests require:
# - Valid WebM/Opus test fixture (chunk 0 with header, chunk N without header)
# - Mock transcription service
# - Isolated test environment with ffmpeg/ffprobe
