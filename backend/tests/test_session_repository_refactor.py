"""Test SessionRepository refactor with DRY + SOLID principles.

Critical test: Verify JSON serialization/deserialization works correctly.

Before refactor: metadata dicts were stored as JSON strings but not deserialized on read
After refactor: metadata dicts are properly serialized AND deserialized

NOTE: This test intentionally accesses protected methods (_serialize_value, _deserialize_value)
to verify internal serialization logic. Type warnings suppressed with # type: ignore.

Card: FIX - SessionRepository JSON serialization bug
Author: Bernard Uriza Orozco
Date: 2025-11-14
"""

# pyright: reportPrivateUsage=false
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from backend.repositories.session_repository import SessionRepository


class TestSessionRepositoryRefactor:
    """Test suite for SessionRepository SOLID + DRY refactor."""

    @pytest.fixture
    def temp_h5_file(self) -> Path:
        """Create temporary HDF5 file for testing."""
        temp = tempfile.NamedTemporaryFile(suffix=".h5", delete=False)
        temp.close()
        return Path(temp.name)

    @pytest.fixture
    def repo(self, temp_h5_file: Path) -> SessionRepository:
        """Create SessionRepository instance."""
        return SessionRepository(str(temp_h5_file))

    def test_serialize_deserialize_dict_metadata(self, repo: SessionRepository) -> None:
        """CRITICAL: Test dict metadata is properly serialized AND deserialized.

        This is the bug fix test - before refactor, dicts were stored as JSON strings
        but not deserialized on read, causing AttributeError in workers.
        """
        session_id = "test-session-001"

        # Create session with nested dict metadata
        complex_metadata = {
            "transcription_sources": {
                "webspeech_final": ["hello", "world"],
                "transcription_per_chunks": [
                    {"chunk_number": 0, "text": "test", "latency_ms": 100}
                ],
                "full_transcription": "hello world test",
            },
            "simple_string": "value",
            "simple_int": 42,
            "simple_bool": True,
            "simple_list": [1, 2, 3],
        }

        repo.create({"session_id": session_id, "user_id": "user-123", "metadata": complex_metadata})

        # Read session back
        session_data = repo.read(session_id)

        # CRITICAL ASSERTIONS
        assert session_data is not None
        assert session_data["session_id"] == session_id

        # Verify metadata is a dict (not string)
        metadata = session_data["metadata"]
        assert isinstance(metadata, dict)

        # Verify nested dict is properly deserialized (THIS WAS THE BUG)
        transcription_sources = metadata["transcription_sources"]
        assert isinstance(
            transcription_sources, dict
        ), "transcription_sources should be dict, not string!"

        # Verify we can use .get() on nested dict (this failed before refactor)
        webspeech = transcription_sources.get("webspeech_final", [])
        assert webspeech == ["hello", "world"]

        chunks = transcription_sources.get("transcription_per_chunks", [])
        assert len(chunks) == 1
        assert chunks[0]["chunk_number"] == 0

        full_text = transcription_sources.get("full_transcription", "")
        assert full_text == "hello world test"

        # Verify primitives pass through unchanged
        assert metadata["simple_string"] == "value"
        assert metadata["simple_int"] == 42
        assert metadata["simple_bool"] is True
        assert metadata["simple_list"] == [1, 2, 3]

    def test_update_with_dict_metadata(self, repo: SessionRepository) -> None:
        """Test update() also properly serializes/deserializes dicts."""
        session_id = "test-session-002"

        # Create simple session
        repo.create({"session_id": session_id, "metadata": {"initial": "value"}})

        # Update with complex metadata
        update_metadata = {
            "diarization_metadata": {
                "segment_count": 10,
                "model": "qwen2.5:3b",
                "speakers": ["MEDICO", "PACIENTE"],
            }
        }

        success = repo.update(session_id, {"metadata": update_metadata})
        assert success

        # Read back and verify deserialization
        session_data = repo.read(session_id)
        assert session_data is not None

        metadata = session_data["metadata"]
        diarization = metadata["diarization_metadata"]

        # CRITICAL: Must be dict, not string
        assert isinstance(diarization, dict)
        assert diarization["segment_count"] == 10
        assert diarization["model"] == "qwen2.5:3b"
        assert diarization["speakers"] == ["MEDICO", "PACIENTE"]

    def test_serialize_value_helper(self) -> None:
        """Test _serialize_value() helper method (DRY principle)."""
        # Primitives pass through
        assert SessionRepository._serialize_value("test") == "test"
        assert SessionRepository._serialize_value(42) == 42
        assert SessionRepository._serialize_value(3.14) == 3.14
        assert SessionRepository._serialize_value(True) is True

        # Dicts/lists serialize to JSON
        result = SessionRepository._serialize_value({"key": "value"})
        assert isinstance(result, str)
        assert result == '{"key": "value"}'

        result = SessionRepository._serialize_value([1, 2, 3])
        assert isinstance(result, str)
        assert result == "[1, 2, 3]"

        # None serializes to JSON null
        result = SessionRepository._serialize_value(None)
        assert result == "null"

    def test_deserialize_value_helper(self) -> None:
        """Test _deserialize_value() helper method (DRY principle)."""
        # Primitives pass through
        assert SessionRepository._deserialize_value("test") == "test"
        assert SessionRepository._deserialize_value(42) == 42
        assert SessionRepository._deserialize_value(3.14) == 3.14
        assert SessionRepository._deserialize_value(True) is True

        # JSON strings deserialize to Python types
        result = SessionRepository._deserialize_value('{"key": "value"}')
        assert result == {"key": "value"}

        result = SessionRepository._deserialize_value("[1, 2, 3]")
        assert result == [1, 2, 3]

        result = SessionRepository._deserialize_value("null")
        assert result is None

        # Non-JSON strings pass through
        assert SessionRepository._deserialize_value("not json") == "not json"

        # Malformed JSON passes through gracefully
        assert SessionRepository._deserialize_value("{invalid}") == "{invalid}"

    def test_bug_reproduction_original_error(self, repo: SessionRepository) -> None:
        """Reproduce the original bug: 'str' object has no attribute 'get'.

        This test would FAIL before the refactor and PASS after.
        """
        session_id = "bug-repro-session"

        # Simulate finalize endpoint saving transcription_sources
        repo.create(
            {
                "session_id": session_id,
                "metadata": {
                    "transcription_sources": {
                        "webspeech_final": ["test1", "test2"],
                        "full_transcription": "test1 test2",
                    }
                },
            }
        )

        # Read back (simulates worker reading session)
        session_data = repo.read(session_id)
        assert session_data is not None

        # THIS LINE FAILED BEFORE REFACTOR with AttributeError: 'str' object has no attribute 'get'
        transcription_sources = session_data.get("metadata", {}).get("transcription_sources", {})

        # Now it should work - transcription_sources is a dict
        webspeech = transcription_sources.get("webspeech_final", [])
        assert webspeech == ["test1", "test2"]

        # SUCCESS: Bug is fixed!
