"""Diarization provider base classes.

Abstract base class following Strategy Pattern for provider implementations.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

from backend.providers.diarization.models import DiarizationResponse
from backend.utils.common.logging.logger import get_logger


class DiarizationProviderType(Enum):
    """Supported diarization providers."""

    PYANNOTE = "pyannote"
    DEEPGRAM = "deepgram"
    AZURE_GPT4 = "azure_gpt4"


class DiarizationProvider(ABC):
    """Abstract base class for diarization providers.

    Implements Strategy Pattern - each provider is a concrete strategy.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def diarize(
        self,
        audio_path: str | Path,
        num_speakers: int | None = None,
    ) -> DiarizationResponse:
        """Identify speakers in audio file.

        Args:
            audio_path: Path to audio file
            num_speakers: Expected number of speakers (optional, can be auto-detected)

        Returns:
            DiarizationResponse with speaker segments and metadata
        """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider identifier string."""


class TextBasedDiarizationProvider(DiarizationProvider):
    """Base class for text-based diarization (LLM-powered).

    Text-based providers analyze transcripts rather than audio directly.
    They implement diarize() for interface compatibility but prefer diarize_text().
    """

    def diarize(
        self,
        audio_path: str | Path,
        num_speakers: int | None = None,
    ) -> DiarizationResponse:
        """Not supported for text-based providers.

        Use diarize_text() instead.
        """
        raise NotImplementedError(
            f"{self.get_provider_name()} is text-based. Use diarize_text() instead."
        )

    @abstractmethod
    def diarize_text(
        self,
        transcript: str,
        num_speakers: int = 2,
        chunks: list[dict[str, Any]] | None = None,
        webspeech_final: list[str] | None = None,
    ) -> DiarizationResponse:
        """Diarize from transcript text.

        Args:
            transcript: Full transcript text
            num_speakers: Expected number of speakers (default: 2 for doctor+patient)
            chunks: Optional ASR chunks with timestamps
            webspeech_final: Optional WebSpeech API final results

        Returns:
            DiarizationResponse with speaker segments
        """
