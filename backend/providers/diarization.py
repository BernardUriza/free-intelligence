"""Diarization models and LLM-based diarization.

This module provides speaker diarization using the LLM provider.
Single-provider architecture - prompts from fi_prompts/yaml_presets/

File: backend/providers/diarization.py
Refactored: 2026-01-18
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from backend.providers.llm import llm_generate
from backend.src.fi_common.logging.logger import get_logger

logger = get_logger(__name__)


# ==============================================================================
# PROMPT LOADING (from fi_prompts system)
# ==============================================================================


@lru_cache(maxsize=1)
def _load_diarization_prompt() -> str:
    """Load diarization prompt from fi_prompts YAML preset (cached)."""
    # Import directly to avoid broken __init__.py
    from pathlib import Path
    from backend.src.fi_prompts.yaml_provider import YAMLPromptProvider

    # Use path relative to this file (works from any cwd)
    prompts_dir = Path(__file__).parent.parent / "src" / "fi_prompts" / "yaml_presets"
    provider = YAMLPromptProvider(yaml_dir=str(prompts_dir))
    system_prompt = provider.get_yaml_system_prompt("diarization_analyst")

    if not system_prompt:
        raise ValueError("Diarization prompt not found in fi_prompts/yaml_presets/")

    return system_prompt


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

    # Load system prompt from fi_prompts YAML preset
    system_prompt = _load_diarization_prompt()

    # Build full prompt (system + user message combined)
    prompt = f"""{system_prompt}

---

TRANSCRIPT TO ANALYZE:
{transcript[:8000]}

Return a JSON array with each segment classified by speaker (DOCTOR, PATIENT, OTHER).
Format: [{{"speaker": "DOCTOR", "text": "...", "improved_text": "..."}}]"""

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
