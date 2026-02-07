"""Diarization data models.

Immutable data structures for speaker diarization results.
All models use __slots__ for memory efficiency.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor)
"""

from __future__ import annotations

from typing import Any


class Speaker:
    """Speaker information."""

    __slots__ = ("confidence", "name", "speaker_id")

    def __init__(
        self,
        speaker_id: str,
        name: str | None = None,
        confidence: float = 0.0,
    ) -> None:
        self.speaker_id = speaker_id
        self.name = name
        self.confidence = confidence

    def __repr__(self) -> str:
        return f"Speaker(id={self.speaker_id!r}, name={self.name!r})"


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

    def __repr__(self) -> str:
        return (
            f"DiarizationSegment("
            f"{self.start_time:.1f}s-{self.end_time:.1f}s, "
            f"speaker={self.speaker.speaker_id!r})"
        )


class DiarizationResponse:
    """Unified response from diarization provider."""

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

    def __repr__(self) -> str:
        return (
            f"DiarizationResponse("
            f"provider={self.provider!r}, "
            f"speakers={self.num_speakers}, "
            f"segments={len(self.segments)})"
        )
