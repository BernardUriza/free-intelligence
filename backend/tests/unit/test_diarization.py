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

    def test_speaker_attributes(self) -> None:
        """Test Speaker attribute access."""
        from backend.providers.diarization import Speaker

        speaker = Speaker(
            speaker_id="PATIENT",
            name="John Doe",
            confidence=0.85,
        )

        assert speaker.speaker_id == "PATIENT"
        assert speaker.name == "John Doe"
        assert speaker.confidence == 0.85


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

    def test_segment_attributes(self) -> None:
        """Test DiarizationSegment attribute access."""
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

        assert segment.start_time == 0.0
        assert segment.end_time == 3.5
        assert segment.confidence == 0.75
        assert segment.text == "I have a headache."
        assert segment.speaker.speaker_id == "PATIENT"
        assert segment.duration == 3.5


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
# OBSOLETE TESTS (Commented out - API no longer exists)
# ==============================================================================
#
# The following tests were for diarize_with_llm() and related functions
# which have been replaced by provider-based architecture (PyannoteProvider,
# AWSTranscribeProvider, GoogleSpeechProvider, DeepgramProvider).
#
# Original tests: TestDiarizeWithLLM (140 lines) + TestPromptLoading (56 lines)
# Total: 196 lines of obsolete tests removed
#
# TODO: Rewrite tests for new provider-based API when needed
# ==============================================================================
