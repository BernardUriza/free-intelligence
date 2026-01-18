"""Diarization models and LLM-based diarization.

This module provides speaker diarization using the LLM provider.
The previous multi-provider architecture (Pyannote, AWS, Google, Deepgram)
has been consolidated to use the same LLM infrastructure as the rest of the system.

File: backend/providers/diarization.py
Refactored: 2026-01-18
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from backend.providers.llm import get_provider, llm_generate
from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)


# ==============================================================================
# DATA MODELS
# ==============================================================================


class Speaker:
    """Speaker information."""

    __slots__ = ("confidence", "name", "speaker_id")

    speaker_id: str  # "Speaker 1", "SPEAKER_01", etc.
    name: str | None  # "Doctor" or "Patient" (if known)
    confidence: float  # 0-1, confidence in assignment

    def __init__(
        self, speaker_id: str, name: str | None = None, confidence: float = 0.0
    ) -> None:
        self.speaker_id = speaker_id
        self.name = name
        self.confidence = confidence

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "speaker_id": self.speaker_id,
            "name": self.name,
            "confidence": self.confidence,
        }


class DiarizationSegment:
    """A segment of speech from one speaker."""

    __slots__ = (
        "confidence",
        "duration",
        "end_time",
        "improved_text",
        "speaker",
        "start_time",
        "text",
    )

    start_time: float
    end_time: float
    speaker: Speaker
    confidence: float
    text: str | None
    improved_text: str | None
    duration: float

    def __init__(
        self,
        start_time: float,
        end_time: float,
        speaker: Speaker,
        confidence: float,
        text: str | None = None,
        improved_text: str | None = None,
        duration: float | None = None,
    ) -> None:
        self.start_time = start_time
        self.end_time = end_time
        self.speaker = speaker
        self.confidence = confidence
        self.text = text
        self.improved_text = improved_text
        self.duration = duration if duration is not None else (end_time - start_time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "speaker": self.speaker.to_dict(),
            "confidence": self.confidence,
            "text": self.text,
            "improved_text": self.improved_text,
            "duration": self.duration,
        }


class DiarizationResponse:
    """Unified response from diarization."""

    __slots__ = (
        "confidence",
        "duration",
        "latency_ms",
        "metadata",
        "num_speakers",
        "provider",
        "segments",
        "speakers",
    )

    segments: list[DiarizationSegment]
    speakers: dict[str, Speaker]
    num_speakers: int
    duration: float
    confidence: float
    provider: str
    latency_ms: float | None
    metadata: dict[str, Any] | None

    def __init__(
        self,
        segments: list[DiarizationSegment],
        speakers: dict[str, Speaker],
        num_speakers: int,
        duration: float,
        confidence: float,
        provider: str,
        latency_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.segments = segments
        self.speakers = speakers
        self.num_speakers = num_speakers
        self.duration = duration
        self.confidence = confidence
        self.provider = provider
        self.latency_ms = latency_ms
        self.metadata = metadata


# ==============================================================================
# LLM-BASED DIARIZATION
# ==============================================================================

DIARIZATION_PROMPT = """Analyze this medical consultation transcript and identify speakers.

TRANSCRIPT:
{transcript}

INSTRUCTIONS:
1. Identify each speaker (typically Doctor and Patient)
2. Split the transcript into segments by speaker
3. For each segment, provide:
   - speaker: "Doctor" or "Patient"
   - text: The exact text spoken
   - improved_text: Cleaned/corrected version (fix typos, add punctuation)

Return JSON array:
[
  {{"speaker": "Doctor", "text": "...", "improved_text": "..."}},
  {{"speaker": "Patient", "text": "...", "improved_text": "..."}}
]

Only return the JSON array, no other text."""


def diarize_with_llm(
    transcript: str,
    num_speakers: int = 2,
    provider: str | None = None,
    **kwargs: Any,
) -> DiarizationResponse:
    """Perform speaker diarization using the LLM provider.

    Args:
        transcript: Full transcript text
        num_speakers: Expected number of speakers (default: 2)
        provider: LLM provider to use (default: from policy)
        **kwargs: Additional arguments (ignored for compatibility)

    Returns:
        DiarizationResponse with segments and speakers
    """
    start_time = datetime.now(UTC)

    logger.info(
        "DIARIZATION_LLM_START",
        transcript_length=len(transcript),
        num_speakers=num_speakers,
        provider=provider,
    )

    # Build prompt
    prompt = DIARIZATION_PROMPT.format(transcript=transcript[:8000])  # Limit context

    # Call LLM
    response = llm_generate(prompt=prompt, provider=provider)

    # Parse response
    segments: list[DiarizationSegment] = []
    speakers: dict[str, Speaker] = {}

    try:
        # Extract JSON from response
        content = response.content.strip()
        # Handle markdown code blocks
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\n?", "", content)
            content = re.sub(r"\n?```$", "", content)

        parsed = json.loads(content)

        if not isinstance(parsed, list):
            parsed = [parsed]

        # Build segments
        current_time = 0.0
        for i, item in enumerate(parsed):
            speaker_name = item.get("speaker", f"Speaker {i % num_speakers + 1}")
            text = item.get("text", "")
            improved_text = item.get("improved_text", text)

            # Estimate duration based on word count (~150 words/minute)
            word_count = len(text.split())
            duration = max(1.0, word_count / 150 * 60)

            # Create speaker if not exists
            if speaker_name not in speakers:
                speakers[speaker_name] = Speaker(
                    speaker_id=speaker_name,
                    name=speaker_name,
                    confidence=0.85,
                )

            segment = DiarizationSegment(
                start_time=current_time,
                end_time=current_time + duration,
                speaker=speakers[speaker_name],
                confidence=0.85,
                text=text,
                improved_text=improved_text,
                duration=duration,
            )
            segments.append(segment)
            current_time += duration

    except json.JSONDecodeError as e:
        logger.warning(
            "DIARIZATION_JSON_PARSE_FAILED",
            error=str(e),
            content_preview=content[:200] if content else "empty",
        )
        # Fallback: single segment with full transcript
        speaker = Speaker(speaker_id="Unknown", name="Unknown", confidence=0.5)
        speakers["Unknown"] = speaker
        segments.append(
            DiarizationSegment(
                start_time=0.0,
                end_time=60.0,
                speaker=speaker,
                confidence=0.5,
                text=transcript,
                improved_text=transcript,
            )
        )

    latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

    logger.info(
        "DIARIZATION_LLM_SUCCESS",
        segment_count=len(segments),
        speaker_count=len(speakers),
        latency_ms=round(latency_ms, 2),
    )

    return DiarizationResponse(
        segments=segments,
        speakers=speakers,
        num_speakers=len(speakers),
        duration=sum(s.duration for s in segments),
        confidence=0.85,
        provider=response.provider,
        latency_ms=latency_ms,
        metadata={"model": response.model, "tokens_used": response.tokens_used},
    )


def get_diarization_provider(provider_name: str, config: dict[str, Any] | None = None) -> Any:
    """Factory function for backward compatibility.

    Returns a simple wrapper that calls diarize_with_llm.
    This maintains API compatibility with the old multi-provider architecture.
    """

    class LLMDiarizationProvider:
        """LLM-based diarization provider wrapper."""

        def __init__(self, provider: str) -> None:
            self.provider = provider
            self.config = config or {}

        def diarize(
            self,
            audio_path: str | None = None,
            transcript: str | None = None,
            num_speakers: int = 2,
            **kwargs: Any,
        ) -> DiarizationResponse:
            """Perform diarization using LLM."""
            if not transcript:
                raise ValueError("Transcript is required for LLM-based diarization")

            return diarize_with_llm(
                transcript=transcript,
                num_speakers=num_speakers,
                provider=self.provider if self.provider != "azure_gpt4" else "azure",
                **kwargs,
            )

    # Map old provider names to LLM providers
    llm_provider = "azure" if provider_name in ("azure_gpt4", "azure") else provider_name

    return LLMDiarizationProvider(llm_provider)
