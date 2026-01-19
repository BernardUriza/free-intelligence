"""Unit tests for diarization module.

Tests data models and LLM-based diarization functionality.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# SPEAKER MODEL TESTS
# ==============================================================================


class TestSpeaker:
    """Tests for Speaker model."""

    def test_speaker_creation_minimal(self) -> None:
        """Test Speaker with minimal args."""
        from backend.providers.diarization import Speaker

        speaker = Speaker(speaker_id="SPEAKER_01")

        assert speaker.speaker_id == "SPEAKER_01"
        assert speaker.name is None
        assert speaker.confidence == 0.0

    def test_speaker_creation_full(self) -> None:
        """Test Speaker with all args."""
        from backend.providers.diarization import Speaker

        speaker = Speaker(
            speaker_id="DOCTOR",
            name="Dr. Smith",
            confidence=0.95,
        )

        assert speaker.speaker_id == "DOCTOR"
        assert speaker.name == "Dr. Smith"
        assert speaker.confidence == 0.95

    def test_speaker_to_dict(self) -> None:
        """Test Speaker.to_dict() serialization."""
        from backend.providers.diarization import Speaker

        speaker = Speaker(
            speaker_id="PATIENT",
            name="John Doe",
            confidence=0.85,
        )
        result = speaker.to_dict()

        assert result == {
            "speaker_id": "PATIENT",
            "name": "John Doe",
            "confidence": 0.85,
        }


# ==============================================================================
# DIARIZATION SEGMENT TESTS
# ==============================================================================


class TestDiarizationSegment:
    """Tests for DiarizationSegment model."""

    def test_segment_creation_minimal(self) -> None:
        """Test DiarizationSegment with minimal args."""
        from backend.providers.diarization import DiarizationSegment, Speaker

        speaker = Speaker(speaker_id="SPEAKER_01")
        segment = DiarizationSegment(
            start_time=0.0,
            end_time=5.0,
            speaker=speaker,
            confidence=0.9,
        )

        assert segment.start_time == 0.0
        assert segment.end_time == 5.0
        assert segment.speaker.speaker_id == "SPEAKER_01"
        assert segment.confidence == 0.9
        assert segment.text is None
        assert segment.improved_text is None
        assert segment.duration == 5.0  # Calculated from end - start

    def test_segment_creation_full(self) -> None:
        """Test DiarizationSegment with all args."""
        from backend.providers.diarization import DiarizationSegment, Speaker

        speaker = Speaker(speaker_id="DOCTOR", name="Dr. Smith", confidence=0.95)
        segment = DiarizationSegment(
            start_time=10.5,
            end_time=25.3,
            speaker=speaker,
            confidence=0.88,
            text="How are you feeling today?",
            improved_text="How are you feeling today?",
            duration=14.8,  # Explicit duration
        )

        assert segment.start_time == 10.5
        assert segment.end_time == 25.3
        assert segment.text == "How are you feeling today?"
        assert segment.improved_text == "How are you feeling today?"
        assert segment.duration == 14.8  # Uses explicit value

    def test_segment_to_dict(self) -> None:
        """Test DiarizationSegment.to_dict() serialization."""
        from backend.providers.diarization import DiarizationSegment, Speaker

        speaker = Speaker(speaker_id="PATIENT", name="Patient", confidence=0.80)
        segment = DiarizationSegment(
            start_time=0.0,
            end_time=3.5,
            speaker=speaker,
            confidence=0.75,
            text="I have a headache.",
            improved_text="I have a headache.",
        )
        result = segment.to_dict()

        assert result["start_time"] == 0.0
        assert result["end_time"] == 3.5
        assert result["confidence"] == 0.75
        assert result["text"] == "I have a headache."
        assert result["speaker"]["speaker_id"] == "PATIENT"
        assert result["duration"] == 3.5


# ==============================================================================
# DIARIZATION RESPONSE TESTS
# ==============================================================================


class TestDiarizationResponse:
    """Tests for DiarizationResponse model."""

    def test_response_creation(self) -> None:
        """Test DiarizationResponse creation."""
        from backend.providers.diarization import (
            DiarizationResponse,
            DiarizationSegment,
            Speaker,
        )

        speaker1 = Speaker(speaker_id="DOCTOR", name="Doctor", confidence=0.9)
        speaker2 = Speaker(speaker_id="PATIENT", name="Patient", confidence=0.85)

        segments = [
            DiarizationSegment(
                start_time=0.0,
                end_time=5.0,
                speaker=speaker1,
                confidence=0.9,
                text="Hello, how are you?",
            ),
            DiarizationSegment(
                start_time=5.0,
                end_time=10.0,
                speaker=speaker2,
                confidence=0.85,
                text="I'm fine, thank you.",
            ),
        ]

        response = DiarizationResponse(
            segments=segments,
            speakers={"DOCTOR": speaker1, "PATIENT": speaker2},
            num_speakers=2,
            duration=10.0,
            confidence=0.87,
            provider="llm",
            latency_ms=150.5,
            metadata={"model": "claude"},
        )

        assert len(response.segments) == 2
        assert response.num_speakers == 2
        assert response.duration == 10.0
        assert response.confidence == 0.87
        assert response.provider == "llm"
        assert response.latency_ms == 150.5
        assert response.metadata == {"model": "claude"}

    def test_response_minimal(self) -> None:
        """Test DiarizationResponse with minimal args."""
        from backend.providers.diarization import DiarizationResponse

        response = DiarizationResponse(
            segments=[],
            speakers={},
            num_speakers=0,
            duration=0.0,
            confidence=0.0,
            provider="unknown",
        )

        assert response.segments == []
        assert response.speakers == {}
        assert response.latency_ms is None
        assert response.metadata is None


# ==============================================================================
# DIARIZE_WITH_LLM TESTS
# ==============================================================================


class TestDiarizeWithLLM:
    """Tests for diarize_with_llm function."""

    @patch("backend.providers.diarization._load_diarization_prompt")
    @patch("backend.providers.diarization.llm_generate")
    def test_diarize_with_llm_success(
        self,
        mock_llm_generate: MagicMock,
        mock_load_prompt: MagicMock,
    ) -> None:
        """Test successful diarization with LLM."""
        from backend.providers.diarization import diarize_with_llm

        # Mock prompt loader
        mock_load_prompt.return_value = "You are a diarization expert..."

        # Mock LLM response - properly mock the content attribute
        llm_response = MagicMock()
        llm_response.content = json.dumps([
            {"speaker": "DOCTOR", "text": "Hello, how can I help you?", "improved_text": "Hello, how can I help you?"},
            {"speaker": "PATIENT", "text": "I have a headache.", "improved_text": "I have a headache."},
        ])
        mock_llm_generate.return_value = llm_response

        result = diarize_with_llm(
            transcript="Doctor: Hello, how can I help you? Patient: I have a headache.",
            num_speakers=2,
        )

        assert len(result.segments) == 2
        assert result.segments[0].speaker.speaker_id == "DOCTOR"
        assert result.segments[1].speaker.speaker_id == "PATIENT"
        # Provider is set in DiarizationResponse constructor
        assert result.latency_ms is not None

    @patch("backend.providers.diarization._load_diarization_prompt")
    @patch("backend.providers.diarization.llm_generate")
    def test_diarize_with_llm_json_in_markdown(
        self,
        mock_llm_generate: MagicMock,
        mock_load_prompt: MagicMock,
    ) -> None:
        """Test diarization handles JSON wrapped in markdown code blocks."""
        from backend.providers.diarization import diarize_with_llm

        mock_load_prompt.return_value = "You are a diarization expert..."

        # LLM returns JSON in markdown code block
        llm_response = MagicMock()
        llm_response.content = """```json
[{"speaker": "DOCTOR", "text": "Hello"}]
```"""
        mock_llm_generate.return_value = llm_response

        result = diarize_with_llm(transcript="Hello", num_speakers=2)

        assert len(result.segments) == 1
        assert result.segments[0].speaker.speaker_id == "DOCTOR"

    @patch("backend.providers.diarization._load_diarization_prompt")
    @patch("backend.providers.diarization.llm_generate")
    def test_diarize_with_llm_invalid_json_fallback(
        self,
        mock_llm_generate: MagicMock,
        mock_load_prompt: MagicMock,
    ) -> None:
        """Test diarization fallback when LLM returns invalid JSON."""
        from backend.providers.diarization import diarize_with_llm

        mock_load_prompt.return_value = "You are a diarization expert..."

        # LLM returns invalid JSON
        llm_response = MagicMock()
        llm_response.content = "This is not valid JSON at all"
        mock_llm_generate.return_value = llm_response

        result = diarize_with_llm(transcript="Some transcript text", num_speakers=2)

        # Should fallback to single segment
        assert len(result.segments) == 1
        assert result.segments[0].speaker.speaker_id == "Unknown"
        assert result.segments[0].text == "Some transcript text"
        assert result.segments[0].confidence == 0.5

    @patch("backend.providers.diarization._load_diarization_prompt")
    @patch("backend.providers.diarization.llm_generate")
    def test_diarize_with_llm_single_object_response(
        self,
        mock_llm_generate: MagicMock,
        mock_load_prompt: MagicMock,
    ) -> None:
        """Test diarization handles single object (not array) response."""
        from backend.providers.diarization import diarize_with_llm

        mock_load_prompt.return_value = "You are a diarization expert..."

        # LLM returns single object instead of array
        llm_response = MagicMock()
        llm_response.content = '{"speaker": "DOCTOR", "text": "Hello"}'
        mock_llm_generate.return_value = llm_response

        result = diarize_with_llm(transcript="Hello", num_speakers=1)

        assert len(result.segments) == 1
        assert result.segments[0].speaker.speaker_id == "DOCTOR"

    @patch("backend.providers.diarization._load_diarization_prompt")
    @patch("backend.providers.diarization.llm_generate")
    def test_diarize_with_llm_speaker_tracking(
        self,
        mock_llm_generate: MagicMock,
        mock_load_prompt: MagicMock,
    ) -> None:
        """Test that speakers are tracked correctly across segments."""
        from backend.providers.diarization import diarize_with_llm

        mock_load_prompt.return_value = "You are a diarization expert..."

        # Multiple segments from same speakers
        llm_response = MagicMock()
        llm_response.content = json.dumps([
            {"speaker": "DOCTOR", "text": "Hello"},
            {"speaker": "PATIENT", "text": "Hi"},
            {"speaker": "DOCTOR", "text": "How are you?"},  # Same speaker again
        ])
        mock_llm_generate.return_value = llm_response

        result = diarize_with_llm(transcript="conversation", num_speakers=2)

        # Should have 3 segments but only 2 unique speakers
        assert len(result.segments) == 3
        assert len(result.speakers) == 2
        assert "DOCTOR" in result.speakers
        assert "PATIENT" in result.speakers

        # Segments referencing same speaker should share Speaker object
        assert result.segments[0].speaker is result.segments[2].speaker


# ==============================================================================
# PROMPT LOADING TESTS
# ==============================================================================


class TestPromptLoading:
    """Tests for prompt loading functionality."""

    def test_load_diarization_prompt_success(self) -> None:
        """Test successful prompt loading from YAML."""
        from backend.providers.diarization import _load_diarization_prompt

        # Clear cache for test
        _load_diarization_prompt.cache_clear()

        # Test that it loads without error (uses real YAML file)
        result = _load_diarization_prompt()

        # Should return a non-empty string
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_load_diarization_prompt_not_found(self) -> None:
        """Test error when prompt is not found in YAML."""
        from backend.providers.diarization import _load_diarization_prompt

        # Clear cache for test
        _load_diarization_prompt.cache_clear()

        with patch(
            "backend.src.fi_prompts.yaml_provider.YAMLPromptProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.get_yaml_system_prompt.return_value = None
            mock_provider_class.return_value = mock_provider

            with pytest.raises(ValueError, match="Diarization prompt not found"):
                _load_diarization_prompt()

        # Clear cache after test
        _load_diarization_prompt.cache_clear()

    def test_load_diarization_prompt_caching(self) -> None:
        """Test that prompt loading is cached."""
        from backend.providers.diarization import _load_diarization_prompt

        # Clear cache for test
        _load_diarization_prompt.cache_clear()

        # Call multiple times
        result1 = _load_diarization_prompt()
        result2 = _load_diarization_prompt()
        result3 = _load_diarization_prompt()

        # Results should be identical (cached)
        assert result1 == result2 == result3

        # Check cache info
        cache_info = _load_diarization_prompt.cache_info()
        assert cache_info.hits >= 2  # At least 2 cache hits
