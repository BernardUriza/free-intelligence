"""Unit tests for TranscriptionService with mocking.

Tests cover:
  - Audio file validation (MIME type, extension, size)
  - Session ID validation
  - Audio file storage
  - Whisper transcription integration
  - Audio format conversion
  - Error handling and graceful degradation

Card: FI-BACKEND-FEAT-003
Created: 2025-10-30
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from backend.services.transcription import TranscriptionService


@pytest.fixture
def transcription_service() -> TranscriptionService:
    """Create a TranscriptionService instance for testing."""
    return TranscriptionService()


@pytest.fixture
def valid_session_id() -> str:
    """Generate a valid UUID4 session ID."""
    return str(uuid4())


@pytest.fixture
def valid_audio_content() -> bytes:
    """Create mock audio content (WAV file signature)."""
    # WAV file magic number (RIFF header)
    return b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 1000


class TestSessionValidation:
    """Tests for session ID validation."""

    def test_validate_session_id_valid_uuid4(
        self, transcription_service: TranscriptionService, valid_session_id: str
    ) -> None:
        """Test validation of valid UUID4 session ID."""
        assert transcription_service.validate_session_id(valid_session_id) is True

    def test_validate_session_id_invalid_format(
        self, transcription_service: TranscriptionService
    ) -> None:
        """Test validation fails for non-UUID4 format."""
        assert transcription_service.validate_session_id("invalid-session-id") is False
        assert transcription_service.validate_session_id("") is False
        assert transcription_service.validate_session_id("not-a-uuid") is False

    def test_validate_session_id_none(self, transcription_service: TranscriptionService) -> None:
        """Test validation fails for None."""
        # Note: Python type system prevents None, but runtime may receive it
        try:
            transcription_service.validate_session_id(None)  # type: ignore
            assert False, "Should raise AttributeError"
        except (AttributeError, TypeError):
            pass


class TestAudioFileValidation:
    """Tests for audio file validation."""

    def test_validate_audio_file_valid(self, transcription_service: TranscriptionService) -> None:
        """Test validation passes for valid audio files."""
        # Should not raise
        transcription_service.validate_audio_file(
            filename="test.webm",
            content_type="audio/webm",
            file_size=1024 * 1024,  # 1 MB
        )

    @pytest.mark.parametrize(
        "filename,content_type,file_size,error_msg",
        [
            ("test.txt", "text/plain", 1024, "Invalid audio format"),
            ("test.webm", "text/plain", 1024, "Invalid audio format"),
            ("test.exe", "audio/webm", 1024, "Invalid file extension"),
            ("test.webm", "audio/webm", 101 * 1024 * 1024, "exceeds limit"),
        ],
    )
    def test_validate_audio_file_invalid(
        self,
        transcription_service: TranscriptionService,
        filename: str,
        content_type: str,
        file_size: int,
        error_msg: str,
    ) -> None:
        """Test validation fails for invalid audio files."""
        with pytest.raises(ValueError, match=error_msg):
            transcription_service.validate_audio_file(
                filename=filename,
                content_type=content_type,
                file_size=file_size,
            )

    def test_validate_audio_file_all_allowed_formats(
        self, transcription_service: TranscriptionService
    ) -> None:
        """Test validation passes for all allowed formats."""
        formats = [
            ("test.webm", "audio/webm"),
            ("test.wav", "audio/wav"),
            ("test.mp3", "audio/mpeg"),
            ("test.m4a", "audio/mp4"),
            ("test.ogg", "audio/ogg"),
        ]
        for filename, content_type in formats:
            # Should not raise
            transcription_service.validate_audio_file(
                filename=filename,
                content_type=content_type,
                file_size=1024,
            )


class TestAudioFileStorage:
    """Tests for audio file storage."""

    @patch("backend.storage.audio_storage.save_audio_file")
    def test_save_audio_file_success(
        self,
        mock_save: Mock,
        transcription_service: TranscriptionService,
        valid_session_id: str,
        valid_audio_content: bytes,
    ) -> None:
        """Test successful audio file storage (without mocking)."""
        # Don't mock - let it actually save to verify real behavior
        result = transcription_service.save_audio_file(
            session_id=valid_session_id,
            audio_content=valid_audio_content,
            file_extension="webm",
            metadata={"client_ip": "127.0.0.1"},
        )

        # Check structure (not exact values, as timestamps/hashes vary)
        assert "file_path" in result
        assert "file_hash" in result
        assert result["file_size"] == len(valid_audio_content)
        assert "timestamp_ms" in result
        assert "ttl_expires_at" in result
        assert "manifest_path" in result
        assert valid_session_id in result["file_path"]
        assert result["file_hash"].startswith("sha256:")

    def test_save_audio_file_invalid_extension(
        self,
        transcription_service: TranscriptionService,
        valid_session_id: str,
        valid_audio_content: bytes,
    ) -> None:
        """Test handling of invalid file extensions."""
        # save_audio_file validates extension internally
        with pytest.raises(ValueError, match="Invalid file extension"):
            transcription_service.save_audio_file(
                session_id=valid_session_id,
                audio_content=valid_audio_content,
                file_extension="xyz",  # Invalid
            )


class TestAudioConversion:
    """Tests for audio format conversion."""

    def test_convert_to_wav_success(self, transcription_service: TranscriptionService) -> None:
        """Test successful audio conversion to WAV (mocked)."""
        with patch.object(transcription_service, "_convert_audio_to_wav", return_value=True):
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = Path(tmpdir) / "input.mp3"
                output_path = Path(tmpdir) / "output.wav"

                result = transcription_service.convert_to_wav(input_path, output_path)

                assert result is True

    def test_convert_to_wav_failure(self, transcription_service: TranscriptionService) -> None:
        """Test handling of conversion failures."""
        with patch.object(transcription_service, "_convert_audio_to_wav", return_value=False):
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = Path(tmpdir) / "input.mp3"
                output_path = Path(tmpdir) / "output.wav"

                result = transcription_service.convert_to_wav(input_path, output_path)

                assert result is False

    def test_convert_to_wav_exception(self, transcription_service: TranscriptionService) -> None:
        """Test exception handling during conversion."""
        with patch.object(
            transcription_service,
            "_convert_audio_to_wav",
            side_effect=Exception("ffmpeg not found"),
        ):
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = Path(tmpdir) / "input.mp3"
                output_path = Path(tmpdir) / "output.wav"

                result = transcription_service.convert_to_wav(input_path, output_path)

                assert result is False


class TestTranscription:
    """Tests for Whisper transcription."""

    def test_transcribe_success(
        self,
        transcription_service: TranscriptionService,
    ) -> None:
        """Test successful transcription (mocked internally)."""
        # Mock the internal Whisper model
        with patch.object(transcription_service, "_get_whisper_model") as mock_model, patch.object(
            transcription_service, "_is_whisper_available", return_value=True
        ):
            # Create mock segments and info
            mock_segment = type(
                "Segment",
                (),
                {
                    "start": 0.0,
                    "end": 2.5,
                    "text": "Hola, esto es una prueba.",
                },
            )()
            mock_info = type(
                "Info",
                (),
                {
                    "language": "es",
                    "duration": 2.5,
                },
            )()
            mock_model.return_value.transcribe.return_value = (
                [mock_segment],
                mock_info,
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = Path(tmpdir) / "test.wav"
                audio_path.write_bytes(b"mock audio")

                result = transcription_service.transcribe(
                    audio_path=audio_path,
                    language="es",
                    vad_filter=True,
                )

                assert result["available"] is True
                assert "Hola" in result["text"]

    def test_transcribe_whisper_unavailable(
        self,
        transcription_service: TranscriptionService,
    ) -> None:
        """Test transcription when Whisper is unavailable."""
        # Patch internal availability flag
        with patch.object(transcription_service, "_is_whisper_available", return_value=False):
            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = Path(tmpdir) / "test.wav"
                audio_path.write_bytes(b"mock audio")

                result = transcription_service.transcribe(audio_path=audio_path)

                assert result["available"] is False
                assert "(Transcription unavailable" in result["text"]

    def test_transcribe_with_auto_detect_language(
        self,
        transcription_service: TranscriptionService,
    ) -> None:
        """Test transcription with auto-detected language."""
        with patch.object(transcription_service, "_get_whisper_model") as mock_model, patch.object(
            transcription_service, "_is_whisper_available", return_value=True
        ):
            mock_segment = type(
                "Segment",
                (),
                {
                    "start": 0.0,
                    "end": 1.0,
                    "text": "This is a test.",
                },
            )()
            mock_info = type(
                "Info",
                (),
                {
                    "language": "en",
                    "duration": 1.0,
                },
            )()
            mock_model.return_value.transcribe.return_value = (
                [mock_segment],
                mock_info,
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = Path(tmpdir) / "test.wav"
                audio_path.write_bytes(b"mock audio")

                result = transcription_service.transcribe(
                    audio_path=audio_path,
                    language=None,  # Auto-detect
                )

                assert result["language"] == "en"

    def test_transcribe_failure(
        self,
        transcription_service: TranscriptionService,
    ) -> None:
        """Test handling of transcription failures (FileNotFoundError)."""
        with patch.object(transcription_service, "_get_whisper_model") as mock_model, patch.object(
            transcription_service, "_is_whisper_available", return_value=True
        ):
            # Make transcribe raise FileNotFoundError (simulating missing file)
            mock_model.return_value.transcribe.side_effect = FileNotFoundError("File not found")

            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = Path(tmpdir) / "missing.wav"

                # _transcribe_with_whisper catches FileNotFoundError and raises ValueError
                with pytest.raises(ValueError):
                    transcription_service.transcribe(audio_path=audio_path)


class TestProcessTranscription:
    """Tests for end-to-end transcription processing."""

    def test_process_transcription_end_to_end(
        self,
        transcription_service: TranscriptionService,
        valid_session_id: str,
        valid_audio_content: bytes,
    ) -> None:
        """Test complete transcription workflow (orchestration)."""
        # Mock all the internal methods
        with patch.object(
            transcription_service, "_transcribe_with_whisper"
        ) as mock_transcribe, patch.object(
            transcription_service, "_convert_audio_to_wav", return_value=True
        ), patch.object(
            transcription_service, "_is_whisper_available", return_value=True
        ), patch.object(transcription_service, "save_audio_file") as mock_save:
            # Setup mocks
            mock_save.return_value = {
                "file_path": f"audio/{valid_session_id}/1234567890.webm",
                "file_size": len(valid_audio_content),
                "file_hash": "sha256:test",
                "timestamp_ms": 1234567890,
                "ttl_expires_at": "2025-11-12T12:00:00Z",
                "manifest_path": f"audio/{valid_session_id}/1234567890.manifest.json",
            }
            mock_transcribe.return_value = {
                "text": "Test transcription",
                "segments": [{"start": 0.0, "end": 1.0, "text": "Test"}],
                "language": "en",
                "duration": 1.0,
                "available": True,
            }

            # Test the orchestration
            with patch("backend.storage.audio_storage.AUDIO_STORAGE_DIR") as mock_dir:
                mock_dir.parent = Path("/tmp")

                result = transcription_service.process_transcription(
                    session_id=valid_session_id,
                    audio_content=valid_audio_content,
                    filename="test.webm",
                    content_type="audio/webm",
                    metadata={"test": "data"},
                )

                # Verify orchestration
                assert result["text"] == "Test transcription"
                assert result["available"] is True
                assert "audio_file" in result
                mock_save.assert_called_once()

    def test_process_transcription_invalid_session_id(
        self,
        transcription_service: TranscriptionService,
        valid_audio_content: bytes,
    ) -> None:
        """Test processing with invalid session ID."""
        with pytest.raises(ValueError, match="Invalid session_id format"):
            transcription_service.process_transcription(
                session_id="invalid-id",
                audio_content=valid_audio_content,
                filename="test.webm",
                content_type="audio/webm",
            )

    def test_process_transcription_invalid_file_type(
        self,
        transcription_service: TranscriptionService,
        valid_session_id: str,
        valid_audio_content: bytes,
    ) -> None:
        """Test processing with invalid file type."""
        with pytest.raises(ValueError, match="Invalid audio format"):
            transcription_service.process_transcription(
                session_id=valid_session_id,
                audio_content=valid_audio_content,
                filename="test.txt",
                content_type="text/plain",
            )

    def test_process_transcription_file_too_large(
        self,
        transcription_service: TranscriptionService,
        valid_session_id: str,
    ) -> None:
        """Test processing with file exceeding size limit."""
        oversized_content = b"x" * (101 * 1024 * 1024)

        with pytest.raises(ValueError, match="exceeds limit"):
            transcription_service.process_transcription(
                session_id=valid_session_id,
                audio_content=oversized_content,
                filename="test.webm",
                content_type="audio/webm",
            )


class TestHealthCheck:
    """Tests for health check."""

    def test_health_check_whisper_available(
        self,
        transcription_service: TranscriptionService,
    ) -> None:
        """Test health check when Whisper is available."""
        with patch.object(transcription_service, "_is_whisper_available", return_value=True):
            health = transcription_service.health_check()

            assert health["status"] == "healthy"
            assert health["whisper_available"] is True

    def test_health_check_whisper_unavailable(
        self,
        transcription_service: TranscriptionService,
    ) -> None:
        """Test health check when Whisper is unavailable."""
        with patch.object(transcription_service, "_is_whisper_available", return_value=False):
            health = transcription_service.health_check()

            assert health["status"] == "healthy"
            assert health["whisper_available"] is False
