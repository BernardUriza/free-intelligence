"""
Tests for Audio Storage Module
Card: FI-BACKEND-FEAT-003
"""

import json
import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from backend.audio_storage import (
    compute_sha256,
    get_audio_manifest,
    save_audio_file,
    validate_session_id,
)

# Test data directory
TEST_STORAGE_DIR = Path("./storage/test_audio")


@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and cleanup test storage directory"""
    # Override storage dir for tests
    import backend.audio_storage as audio_module

    original_dir = audio_module.AUDIO_STORAGE_DIR
    audio_module.AUDIO_STORAGE_DIR = TEST_STORAGE_DIR

    # Create test directory
    TEST_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    yield

    # Restore original and cleanup
    audio_module.AUDIO_STORAGE_DIR = original_dir
    if TEST_STORAGE_DIR.exists():
        shutil.rmtree(TEST_STORAGE_DIR)


def test_validate_session_id_valid() -> None:
    """Test session_id validation with valid UUID4"""
    session_id = str(uuid4())
    assert validate_session_id(session_id) is True


def test_validate_session_id_invalid() -> None:
    """Test session_id validation with invalid formats"""
    assert validate_session_id("not-a-uuid") is False
    assert validate_session_id("12345678") is False
    assert validate_session_id("") is False


def test_compute_sha256() -> None:
    """Test SHA256 hash computation"""
    # Create temporary file
    test_file = TEST_STORAGE_DIR / "test.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test content")

    # Compute hash
    file_hash = compute_sha256(test_file)

    # Verify format
    assert len(file_hash) == 64  # SHA256 hex is 64 chars
    assert all(c in "0123456789abcdef" for c in file_hash)


def test_save_audio_file_webm() -> None:
    """Test saving audio file with WEBM format"""
    session_id = str(uuid4())
    audio_content = b"fake audio data"
    file_extension = "webm"

    result = save_audio_file(
        session_id=session_id,
        audio_content=audio_content,
        file_extension=file_extension,
        metadata={"source": "test"},
    )

    # Verify response
    assert "file_path" in result
    assert "file_size" in result
    assert "file_hash" in result
    assert "timestamp_ms" in result
    assert "ttl_expires_at" in result
    assert "manifest_path" in result

    assert result["file_size"] == len(audio_content)
    assert result["file_hash"].startswith("sha256:")

    # Verify file exists
    file_path = TEST_STORAGE_DIR.parent / result["file_path"]
    assert file_path.exists()

    # Verify manifest exists
    manifest_path = TEST_STORAGE_DIR.parent / result["manifest_path"]
    assert manifest_path.exists()

    # Verify manifest content
    with open(manifest_path) as f:
        manifest = json.load(f)

    assert manifest["sessionId"] == session_id
    assert manifest["fileExtension"] == file_extension
    assert manifest["fileHash"] == result["file_hash"]
    assert manifest["metadata"]["source"] == "test"


def test_save_audio_file_invalid_session_id() -> None:
    """Test saving audio file with invalid session_id"""
    with pytest.raises(ValueError, match="Invalid session_id format"):
        save_audio_file(
            session_id="invalid-uuid",
            audio_content=b"test",
            file_extension="webm",
        )


def test_save_audio_file_invalid_extension() -> None:
    """Test saving audio file with invalid extension"""
    session_id = str(uuid4())

    with pytest.raises(ValueError, match="Invalid file extension"):
        save_audio_file(
            session_id=session_id,
            audio_content=b"test",
            file_extension="exe",  # Not allowed
        )


def test_save_audio_file_multiple_formats() -> None:
    """Test saving audio files with different formats"""
    session_id = str(uuid4())
    allowed_formats = ["webm", "wav", "mp3", "m4a", "ogg"]

    for ext in allowed_formats:
        result = save_audio_file(
            session_id=session_id,
            audio_content=b"test audio",
            file_extension=ext,
        )

        # Verify file path contains correct extension
        assert result["file_path"].endswith(f".{ext}")


def test_get_audio_manifest_exists() -> None:
    """Test retrieving audio manifest that exists"""
    session_id = str(uuid4())
    audio_content = b"test audio"

    # Save audio file
    result = save_audio_file(
        session_id=session_id,
        audio_content=audio_content,
        file_extension="webm",
    )

    timestamp_ms = result["timestamp_ms"]

    # Retrieve manifest
    manifest = get_audio_manifest(session_id, timestamp_ms)

    assert manifest is not None
    assert manifest["sessionId"] == session_id
    assert manifest["timestampMs"] == timestamp_ms


def test_get_audio_manifest_not_exists() -> None:
    """Test retrieving audio manifest that doesn't exist"""
    session_id = str(uuid4())
    timestamp_ms = 1234567890

    manifest = get_audio_manifest(session_id, timestamp_ms)

    assert manifest is None


def test_atomic_write_no_tmp_file_left() -> None:
    """Test that atomic write doesn't leave .tmp files"""
    session_id = str(uuid4())
    audio_content = b"test audio"

    result = save_audio_file(
        session_id=session_id,
        audio_content=audio_content,
        file_extension="webm",
    )

    # Verify no .tmp file exists
    file_path = TEST_STORAGE_DIR.parent / result["file_path"]
    tmp_file = file_path.with_suffix(".webm.tmp")

    assert not tmp_file.exists()
    assert file_path.exists()
