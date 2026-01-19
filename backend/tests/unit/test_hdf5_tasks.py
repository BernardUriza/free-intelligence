"""Tests for HDF5 task storage modules.

Coverage target: SOAP, transcription_sources, chunks modules.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import h5py
import pytest
from backend.models.task_type import TaskType
from pathlib import Path


# Test fixtures for HDF5 operations
@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory for tests."""
    storage_path = tmp_path / "storage" / "sessions"
    storage_path.mkdir(parents=True)
    return storage_path


class TestSoapStorage:
    """Test SOAP note storage operations."""

    def test_save_soap_data_creates_dataset(self, temp_storage):
        """Test saving SOAP data creates HDF5 dataset."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.soap import (
            save_soap_data,
        )

        session_id = "test-session-soap"
        session_file = temp_storage / f"{session_id}.h5"
        soap_data = {
            "subjective": "Patient reports headache",
            "objective": "BP 120/80, HR 72",
            "assessment": "Tension headache",
            "plan": "Ibuprofen 400mg PRN",
        }

        # Create initial structure
        with h5py.File(session_file, "w") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.SOAP_GENERATION.value}"
            f.create_group(task_path)

        # Mock both functions that need to return the session path
        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.tasks.soap.get_session_h5_path",
            return_value=session_file,
        ), patch(
            "backend.src.fi_storage.infrastructure.hdf5.session_h5_manager.get_session_h5_path",
            return_value=session_file,
        ):
            result_path = save_soap_data(session_id, soap_data)

            assert TaskType.SOAP_GENERATION.value in result_path
            assert "soap_data" in result_path

        # Verify data was saved
        with h5py.File(session_file, "r") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.SOAP_GENERATION.value}"
            assert task_path in f
            assert "soap_data" in f[task_path]

            # Verify content
            stored_json = f[task_path]["soap_data"][()].decode("utf-8")
            stored_data = json.loads(stored_json)
            assert stored_data["subjective"] == "Patient reports headache"

    def test_save_soap_data_creates_version_history(self, temp_storage):
        """Test SOAP data saves to version history."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.soap import (
            save_soap_data,
        )

        session_id = "test-session-history"
        session_file = temp_storage / f"{session_id}.h5"

        # Create initial structure
        with h5py.File(session_file, "w") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.SOAP_GENERATION.value}"
            f.create_group(task_path)

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.tasks.soap.get_session_h5_path",
            return_value=session_file,
        ), patch(
            "backend.src.fi_storage.infrastructure.hdf5.session_h5_manager.get_session_h5_path",
            return_value=session_file,
        ):
            # Save first version
            save_soap_data(session_id, {"subjective": "First"})

        # Verify version history exists
        with h5py.File(session_file, "r") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.SOAP_GENERATION.value}"
            assert "version_history" in f[task_path]
            # Should have at least one version
            history = f[task_path]["version_history"]
            assert len(list(history.keys())) >= 1


class TestTranscriptionSourcesStorage:
    """Test transcription source storage operations."""

    def test_add_webspeech_transcripts(self, temp_storage):
        """Test adding WebSpeech transcripts."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.transcription_sources import (
            add_webspeech_transcripts,
        )

        session_id = "test-session-webspeech"
        session_file = temp_storage / f"{session_id}.h5"
        transcripts = [
            "Hello doctor",
            "I have been feeling unwell",
            "The headache started yesterday",
        ]

        # Create initial structure with TRANSCRIPTION task
        with h5py.File(session_file, "w") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}"
            f.create_group(task_path)

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.session_h5_manager.get_session_h5_path",
            return_value=session_file,
        ):
            # Add transcripts
            result_path = add_webspeech_transcripts(session_id, transcripts)

            assert "webspeech_final" in result_path

        # Verify data
        with h5py.File(session_file, "r") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}"
            assert "webspeech_final" in f[task_path]

            stored_json = f[task_path]["webspeech_final"][()]
            stored_list = json.loads(stored_json)
            assert len(stored_list) == 3
            assert stored_list[0] == "Hello doctor"

    def test_add_full_transcription(self, temp_storage):
        """Test adding full transcription text."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.transcription_sources import (
            add_full_transcription,
        )

        session_id = "test-session-full-tx"
        session_file = temp_storage / f"{session_id}.h5"
        full_text = "This is the complete transcription of the medical consultation."

        # Create initial structure
        with h5py.File(session_file, "w") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}"
            f.create_group(task_path)

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.session_h5_manager.get_session_h5_path",
            return_value=session_file,
        ):
            # Add full transcription
            result_path = add_full_transcription(session_id, full_text)

            assert "full_transcription" in result_path

        # Verify data
        with h5py.File(session_file, "r") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}"
            assert "full_transcription" in f[task_path]

            stored_text = f[task_path]["full_transcription"][()].decode("utf-8")
            assert "complete transcription" in stored_text

    def test_add_full_audio(self, temp_storage):
        """Test adding full audio bytes."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.transcription_sources import (
            add_full_audio,
        )

        session_id = "test-session-audio"
        session_file = temp_storage / f"{session_id}.h5"
        audio_bytes = b"\x00\x01\x02\x03" * 100  # Fake audio data

        # Create initial structure
        with h5py.File(session_file, "w") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}"
            f.create_group(task_path)

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.session_h5_manager.get_session_h5_path",
            return_value=session_file,
        ):
            # Add audio
            result_path = add_full_audio(session_id, audio_bytes)

            assert "full_audio.webm" in result_path

        # Verify data
        with h5py.File(session_file, "r") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}"
            assert "full_audio.webm" in f[task_path]

            stored_audio = bytes(f[task_path]["full_audio.webm"][()])
            assert len(stored_audio) == 400

    def test_add_webspeech_requires_existing_task(self, temp_storage):
        """Test that WebSpeech requires existing task."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.transcription_sources import (
            add_webspeech_transcripts,
        )

        session_id = "test-session-no-task"
        session_file = temp_storage / f"{session_id}.h5"

        # Create empty file (no task)
        with h5py.File(session_file, "w") as f:
            f.create_group(f"/sessions/{session_id}")

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.session_h5_manager.get_session_h5_path",
            return_value=session_file,
        ):
            # Should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                add_webspeech_transcripts(session_id, ["test"])

            assert "does not exist" in str(exc_info.value)


class TestLifecycleOperations:
    """Test task lifecycle operations."""

    def test_ensure_task_exists(self, temp_storage):
        """Test ensuring a task exists (creates if needed)."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle import (
            ensure_task_exists,
        )

        session_id = "test-session-lifecycle"
        session_file = temp_storage / f"{session_id}.h5"

        # Create initial session structure
        with h5py.File(session_file, "w") as f:
            f.create_group(f"/sessions/{session_id}")

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.get_session_h5_path",
            return_value=session_file,
        ), patch(
            "backend.src.fi_storage.infrastructure.hdf5.session_h5_manager.get_session_h5_path",
            return_value=session_file,
        ):
            result = ensure_task_exists(session_id, TaskType.TRANSCRIPTION)

            assert result is not None
            assert "TRANSCRIPTION" in result

        # Verify task was created
        with h5py.File(session_file, "r") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}"
            assert task_path in f

    def test_task_exists_returns_true_when_exists(self, temp_storage):
        """Test task_exists returns True when task exists."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle import (
            task_exists,
        )

        session_id = "test-session-exists"
        session_file = temp_storage / f"{session_id}.h5"

        # Create structure with task
        with h5py.File(session_file, "w") as f:
            task_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.value}"
            f.create_group(task_path)

        # Mock to use our temp file instead of production path
        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.session_h5_manager.get_session_h5_path",
            return_value=session_file,
        ):
            result = task_exists(session_id, TaskType.TRANSCRIPTION)
            assert result is True

    def test_task_exists_returns_false_when_missing(self, temp_storage):
        """Test task_exists returns False when task doesn't exist."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle import (
            task_exists,
        )

        session_id = "test-session-missing"
        session_file = temp_storage / f"{session_id}.h5"

        # Create structure without task
        with h5py.File(session_file, "w") as f:
            f.create_group(f"/sessions/{session_id}")

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle.get_session_h5_path",
            return_value=session_file,
        ):
            result = task_exists(session_id, TaskType.TRANSCRIPTION)
            assert result is False


class TestH5FileAccess:
    """Test HDF5 file access utilities."""

    def test_open_h5_read(self, temp_storage):
        """Test opening HDF5 file for reading."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks.h5_file_access import (
            open_h5_read,
        )

        # Create a test corpus file
        corpus_file = temp_storage.parent / "corpus.h5"
        with h5py.File(corpus_file, "w") as f:
            f.create_group("/test")

        with patch(
            "backend.src.fi_storage.infrastructure.hdf5.session_h5_manager.CORPUS_PATH",
            corpus_file,
        ), patch(
            "backend.src.fi_storage.infrastructure.hdf5.tasks.h5_file_access.CORPUS_PATH",
            corpus_file,
        ):
            with open_h5_read() as f:
                assert "/test" in f


class TestChunksStorage:
    """Test chunk storage operations.

    Note: Full chunk tests require more extensive mocking of the complex
    chunk storage architecture. These placeholder tests verify the modules load.
    """

    def test_chunks_module_imports(self):
        """Test that chunks module can be imported."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks import chunks

        # Verify key functions exist
        assert hasattr(chunks, "append_chunk_to_task")
        assert hasattr(chunks, "count_task_chunks")
        assert hasattr(chunks, "get_task_chunks")
        assert hasattr(chunks, "get_task_transcript")

    def test_diarization_module_imports(self):
        """Test that diarization module can be imported."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks import diarization

        # Verify module loaded
        assert diarization is not None

    def test_orders_module_imports(self):
        """Test that orders module can be imported."""
        from backend.src.fi_storage.infrastructure.hdf5.tasks import orders

        # Verify module loaded
        assert orders is not None
