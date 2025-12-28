"""Tests for task-based HDF5 repository.

Tests cover:
- Task creation with uniqueness enforcement
- Chunk appending and retrieval
- Metadata operations
- Task listing and existence checks

Author: Bernard Uriza Orozco
Created: 2025-11-14
Card: Architecture refactor - task-based HDF5
"""

from __future__ import annotations

import tempfile

import h5py
import pytest
from backend.models.task_type import TaskStatus, TaskType
from backend.src.fi_storage.infrastructure.hdf5.session_h5_manager import (
    get_session_h5_path,
)
from backend.src.fi_storage.infrastructure.hdf5.task_repository import (
    append_chunk_to_task,
    ensure_task_exists,
    get_task_chunks,
    get_task_metadata,
    get_task_transcript,
    list_session_tasks,
    task_exists,
    update_task_metadata,
)
from pathlib import Path


@pytest.fixture
def temp_corpus():
    """Create temporary HDF5 file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".h5", delete=False) as tmp:
        corpus_path = Path(tmp.name)

    yield corpus_path

    # Cleanup
    if corpus_path.exists():
        corpus_path.unlink()


@pytest.fixture
def temp_session_storage(tmp_path):
    """Create temporary session storage directory."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()

    # Mock the storage paths
    import backend.storage.session_h5_manager as session_h5_manager

    original_storage_dir = session_h5_manager.STORAGE_DIR
    original_sessions_dir = session_h5_manager.SESSIONS_DIR

    session_h5_manager.STORAGE_DIR = tmp_path
    session_h5_manager.SESSIONS_DIR = sessions_dir

    yield tmp_path

    # Restore original paths
    session_h5_manager.STORAGE_DIR = original_storage_dir
    session_h5_manager.SESSIONS_DIR = original_sessions_dir


def test_ensure_task_exists_creates_new(_):
    """Test creating a new task."""
    session_id = "test_session_001"
    task_type = TaskType.TRANSCRIPTION

    # Create task
    task_path = ensure_task_exists(session_id, task_type, allow_existing=False)

    assert task_path == f"/sessions/{session_id}/tasks/{task_type.value}"

    # Verify task exists in session HDF5 file
    from backend.src.fi_storage.infrastructure.hdf5.session_h5_manager import (
        get_session_h5_path,
    )

    session_file = get_session_h5_path(session_id)
    with h5py.File(session_file, "r") as f:
        assert f"sessions/{session_id}/tasks/{task_type.value}" in f


def test_ensure_task_exists_rejects_duplicate(temp_session_storage):
    """Test that duplicate tasks are rejected."""
    session_id = "test_session_002"
    task_type = TaskType.TRANSCRIPTION

    # Create first task
    ensure_task_exists(session_id, task_type, allow_existing=False)

    # Attempt to create duplicate should raise
    with pytest.raises(ValueError, match="already exists"):
        ensure_task_exists(session_id, task_type, allow_existing=False)


def test_ensure_task_exists_allows_existing(temp_session_storage):
    """Test that allow_existing=True doesn't raise on duplicate."""
    session_id = "test_session_003"
    task_type = TaskType.TRANSCRIPTION

    # Create task twice with allow_existing=True
    path1 = ensure_task_exists(session_id, task_type, allow_existing=True)
    path2 = ensure_task_exists(session_id, task_type, allow_existing=True)

    assert path1 == path2


def test_append_chunk_to_task(temp_session_storage):
    """Test appending chunks to a task."""
    session_id = "test_session_004_unique"
    task_type = TaskType.TRANSCRIPTION

    # Create task
    ensure_task_exists(session_id, task_type, allow_existing=False)

    # Append chunk
    chunk_path = append_chunk_to_task(
        session_id=session_id,
        task_type=task_type,
        chunk_idx=0,
        transcript="Hola, soy el paciente.",
        audio_hash="abc123",
        duration=3.5,
        language="es",
        timestamp_start=0.0,
        timestamp_end=3.5,
        confidence=0.95,
        audio_quality=0.88,
    )

    assert "chunk_0" in chunk_path

    # Verify chunk in session HDF5 file
    from backend.src.fi_storage.infrastructure.hdf5.session_h5_manager import (
        get_session_h5_path,
    )

    session_file = get_session_h5_path(session_id)
    with h5py.File(session_file, "r") as f:
        chunk_group = f[chunk_path]
        assert chunk_group["transcript"][()] == b"Hola, soy el paciente."
        assert chunk_group["duration"][()] == 3.5
        assert chunk_group["language"][()] == b"es"


def test_get_task_chunks(temp_session_storage):
    """Test retrieving chunks from a task."""

    session_id = "test_session_005_unique"
    task_type = TaskType.TRANSCRIPTION

    # Create task and add chunks
    ensure_task_exists(session_id, task_type, allow_existing=False)

    append_chunk_to_task(
        session_id=session_id,
        task_type=task_type,
        chunk_idx=0,
        transcript="Chunk 0",
        audio_hash="hash0",
        duration=2.0,
        language="es",
        timestamp_start=0.0,
        timestamp_end=2.0,
    )

    append_chunk_to_task(
        session_id=session_id,
        task_type=task_type,
        chunk_idx=1,
        transcript="Chunk 1",
        audio_hash="hash1",
        duration=2.0,
        language="es",
        timestamp_start=2.0,
        timestamp_end=4.0,
    )

    # Retrieve chunks
    chunks = get_task_chunks(session_id, task_type)

    assert len(chunks) == 2
    assert chunks[0]["chunk_idx"] == 0
    assert chunks[0]["transcript"] == "Chunk 0"
    assert chunks[1]["chunk_idx"] == 1
    assert chunks[1]["transcript"] == "Chunk 1"


def test_get_task_transcript(temp_session_storage):
    """Test concatenated transcript retrieval."""

    session_id = "test_session_006_unique"
    task_type = TaskType.TRANSCRIPTION

    # Create task and add chunks
    ensure_task_exists(session_id, task_type, allow_existing=False)

    append_chunk_to_task(
        session_id=session_id,
        task_type=task_type,
        chunk_idx=0,
        transcript="Primera frase.",
        audio_hash="hash0",
        duration=2.0,
        language="es",
        timestamp_start=0.0,
        timestamp_end=2.0,
    )

    append_chunk_to_task(
        session_id=session_id,
        task_type=task_type,
        chunk_idx=1,
        transcript="Segunda frase.",
        audio_hash="hash1",
        duration=2.0,
        language="es",
        timestamp_start=2.0,
        timestamp_end=4.0,
    )

    # Get full transcript
    transcript = get_task_transcript(session_id, task_type)

    assert transcript == "Primera frase. Segunda frase."


def test_update_and_get_task_metadata(temp_corpus, monkeypatch):
    """Test task metadata operations."""
    monkeypatch.setattr("backend.storage.task_repository.CORPUS_PATH", temp_corpus)

    session_id = "test_session_007_unique"
    task_type = TaskType.TRANSCRIPTION

    # Ensure clean state - remove session file if it exists
    session_file = get_session_h5_path(session_id)
    if session_file.exists():
        session_file.unlink()

    # Create task
    ensure_task_exists(session_id, task_type, allow_existing=False)

    # Update metadata
    metadata = {
        "job_id": "job_123",
        "status": TaskStatus.IN_PROGRESS.value,
        "progress_percent": 50,
        "total_chunks": 10,
        "processed_chunks": 5,
    }

    update_task_metadata(session_id, task_type, metadata)

    # Retrieve metadata
    retrieved = get_task_metadata(session_id, task_type)

    assert retrieved is not None
    assert retrieved["job_id"] == "job_123"
    assert retrieved["status"] == TaskStatus.IN_PROGRESS.value
    assert retrieved["progress_percent"] == 50
    assert retrieved["total_chunks"] == 10
    assert retrieved["processed_chunks"] == 5


def test_task_exists(temp_corpus, monkeypatch):
    """Test task existence check."""
    monkeypatch.setattr("backend.storage.task_repository.CORPUS_PATH", temp_corpus)

    session_id = "test_session_008_unique"
    task_type = TaskType.TRANSCRIPTION

    # Ensure clean state - remove session file if it exists
    session_file = get_session_h5_path(session_id)
    if session_file.exists():
        session_file.unlink()

    # Check non-existent task
    assert not task_exists(session_id, task_type)

    # Create task
    ensure_task_exists(session_id, task_type, allow_existing=False)

    # Check existing task
    assert task_exists(session_id, task_type)


def test_list_session_tasks(temp_session_storage):
    """Test listing all tasks for a session."""

    session_id = "test_session_009_unique"

    # Create multiple tasks
    ensure_task_exists(session_id, TaskType.TRANSCRIPTION, allow_existing=False)
    ensure_task_exists(session_id, TaskType.DIARIZATION, allow_existing=False)
    ensure_task_exists(session_id, TaskType.ENCRYPTION, allow_existing=False)

    # List tasks
    tasks = list_session_tasks(session_id)

    assert len(tasks) == 3
    assert TaskType.TRANSCRIPTION.value in tasks
    assert TaskType.DIARIZATION.value in tasks
    assert TaskType.ENCRYPTION.value in tasks


def test_append_chunk_creates_chunks_group(temp_session_storage):
    """Test that appending chunk creates chunks/ group automatically."""
    session_id = "test_session_010_unique"
    task_type = TaskType.TRANSCRIPTION

    # Create task (without chunks group)
    ensure_task_exists(session_id, task_type, allow_existing=False)

    # Append chunk (should create chunks/ group)
    append_chunk_to_task(
        session_id=session_id,
        task_type=task_type,
        chunk_idx=0,
        transcript="Auto-create test",
        audio_hash="hash",
        duration=1.0,
        language="es",
        timestamp_start=0.0,
        timestamp_end=1.0,
    )

    # Verify chunks group exists
    from backend.src.fi_storage.infrastructure.hdf5.session_h5_manager import (
        get_session_h5_path,
    )

    session_file = get_session_h5_path(session_id)
    with h5py.File(session_file, "r") as f:
        assert f"sessions/{session_id}/tasks/{task_type.value}/chunks" in f


def test_get_task_chunks_empty(temp_session_storage):
    """Test retrieving chunks from task with no chunks."""

    session_id = "test_session_011_unique"
    task_type = TaskType.TRANSCRIPTION

    # Create task without chunks
    ensure_task_exists(session_id, task_type, allow_existing=False)

    # Get chunks (should return empty list)
    chunks = get_task_chunks(session_id, task_type)

    assert chunks == []


def test_get_task_metadata_nonexistent(temp_session_storage):
    """Test getting metadata from nonexistent task."""

    session_id = "test_session_012_unique"
    task_type = TaskType.TRANSCRIPTION

    # Get metadata without creating task
    metadata = get_task_metadata(session_id, task_type)

    assert metadata is None


def test_chunk_ordering(temp_session_storage):
    """Test that chunks are retrieved in correct order."""

    session_id = "test_session_013_unique"
    task_type = TaskType.TRANSCRIPTION

    ensure_task_exists(session_id, task_type, allow_existing=False)

    # Add chunks out of order
    append_chunk_to_task(
        session_id=session_id,
        task_type=task_type,
        chunk_idx=2,
        transcript="Chunk 2",
        audio_hash="hash2",
        duration=1.0,
        language="es",
        timestamp_start=4.0,
        timestamp_end=5.0,
    )

    append_chunk_to_task(
        session_id=session_id,
        task_type=task_type,
        chunk_idx=0,
        transcript="Chunk 0",
        audio_hash="hash0",
        duration=1.0,
        language="es",
        timestamp_start=0.0,
        timestamp_end=1.0,
    )

    append_chunk_to_task(
        session_id=session_id,
        task_type=task_type,
        chunk_idx=1,
        transcript="Chunk 1",
        audio_hash="hash1",
        duration=1.0,
        language="es",
        timestamp_start=2.0,
        timestamp_end=3.0,
    )

    # Retrieve chunks (should be ordered by chunk_idx)
    chunks = get_task_chunks(session_id, task_type)

    assert len(chunks) == 3
    assert chunks[0]["chunk_idx"] == 0
    assert chunks[1]["chunk_idx"] == 1
    assert chunks[2]["chunk_idx"] == 2
    assert chunks[0]["transcript"] == "Chunk 0"
    assert chunks[1]["transcript"] == "Chunk 1"
    assert chunks[2]["transcript"] == "Chunk 2"
