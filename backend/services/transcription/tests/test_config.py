"""Unit tests for TranscriptionConfig validation.

Test Coverage:
    - Valid configs (default, custom)
    - Invalid configs (negative values, invalid ranges)
    - Environment variable parsing
    - Immutability (frozen=True)

Author: Claude Code
Created: 2026-01-31
Pattern: Type-Safe Config Validation
"""

import pytest
from pydantic import ValidationError
from backend.services.transcription.dependencies import TranscriptionConfig, get_transcription_config


class TestTranscriptionConfigValidation:
    """Test Pydantic validation rules."""

    def test_valid_default_config(self):
        """✅ Valid config with defaults."""
        config = TranscriptionConfig()

        assert config.max_audio_duration == 7200
        assert config.max_chunk_size == 10485760
        assert config.language == "es"
        assert config.model_name == "whisper-large-v3"
        assert config.enable_diarization is True
        assert config.min_speakers == 1
        assert config.max_speakers == 5

    def test_valid_custom_config(self):
        """✅ Valid config with custom values."""
        config = TranscriptionConfig(
            max_audio_duration=3600,
            max_chunk_size=5242880,
            language="en",
            model_name="whisper-medium",
            enable_diarization=False,
            min_speakers=2,
            max_speakers=8,
        )

        assert config.max_audio_duration == 3600
        assert config.language == "en"
        assert config.enable_diarization is False

    def test_negative_max_audio_duration_raises(self):
        """❌ Negative max_audio_duration should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(max_audio_duration=-100)

        errors = exc_info.value.errors()
        assert len(errors) >= 1
        error = errors[0]
        assert error["loc"] == ("max_audio_duration",)
        assert "greater than 0" in str(error["msg"])

    def test_zero_max_audio_duration_raises(self):
        """❌ Zero max_audio_duration should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(max_audio_duration=0)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("max_audio_duration",)

    def test_negative_max_chunk_size_raises(self):
        """❌ Negative max_chunk_size should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(max_chunk_size=-1000)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("max_chunk_size",)
        assert "greater than 0" in str(error["msg"])

    def test_invalid_language_raises(self):
        """❌ Too short language code should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(language="e")  # Only 1 char (min=2)

        errors = exc_info.value.errors()
        error = [e for e in errors if e["loc"][0] == "language"]
        assert len(error) > 0

    def test_min_speakers_out_of_range_raises(self):
        """❌ min_speakers < 1 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(min_speakers=0)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("min_speakers",)

    def test_max_speakers_out_of_range_raises(self):
        """❌ max_speakers > 10 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(max_speakers=15)

        errors = exc_info.value.errors()
        error = errors[0]
        assert error["loc"] == ("max_speakers",)

    def test_config_immutable(self):
        """✅ frozen=True prevents field modification."""
        config = TranscriptionConfig()

        with pytest.raises(ValidationError):
            config.max_audio_duration = 9999


class TestTranscriptionConfigFromEnv:
    """Test environment variable parsing."""

    def test_from_env_defaults(self, monkeypatch):
        """✅ Default config when env vars not set."""
        monkeypatch.delenv("MAX_AUDIO_DURATION", raising=False)
        monkeypatch.delenv("MAX_CHUNK_SIZE", raising=False)
        monkeypatch.delenv("AUDIO_LANGUAGE", raising=False)

        config = get_transcription_config()

        assert config.max_audio_duration == 7200
        assert config.language == "es"

    def test_from_env_custom_values(self, monkeypatch):
        """✅ Config from env vars."""
        monkeypatch.setenv("MAX_AUDIO_DURATION", "3600")
        monkeypatch.setenv("MAX_CHUNK_SIZE", "5242880")
        monkeypatch.setenv("AUDIO_LANGUAGE", "en")
        monkeypatch.setenv("WHISPER_MODEL", "whisper-medium")
        monkeypatch.setenv("ENABLE_DIARIZATION", "false")

        config = get_transcription_config()

        assert config.max_audio_duration == 3600
        assert config.max_chunk_size == 5242880
        assert config.language == "en"
        assert config.model_name == "whisper-medium"
        assert config.enable_diarization is False

    def test_from_env_invalid_raises(self, monkeypatch):
        """❌ Invalid env value should raise ValidationError."""
        monkeypatch.setenv("MAX_AUDIO_DURATION", "-500")

        with pytest.raises(ValidationError) as exc_info:
            get_transcription_config()

        errors = exc_info.value.errors()
        error = [e for e in errors if e["loc"][0] == "max_audio_duration"]
        assert len(error) > 0
