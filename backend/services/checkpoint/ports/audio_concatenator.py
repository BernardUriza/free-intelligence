"""Audio Concatenator Port - Secondary/Driven Port.

Defines the contract for audio concatenation operations.
Abstracts away the specific tool used (FFmpeg, Pydub, etc.).

Implementations:
- FFmpegConcatenator (production)
- MockConcatenator (testing)
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from typing import Protocol

from ..domain import AudioChunk, AudioFormat


class AudioConcatenatorPort(Protocol):
    """Abstract interface for audio concatenation.

    This is a Secondary Port (Driven) - the application uses this
    to concatenate audio files.

    Implementations should be stateless and handle temporary files internally.
    """

    @abstractmethod
    def concatenate(
        self,
        chunks: Sequence[AudioChunk],
        existing_audio: bytes | None,
        output_format: AudioFormat,
    ) -> bytes:
        """Concatenate audio chunks into a single file.

        Args:
            chunks: Sequence of audio chunks to concatenate (in order)
            existing_audio: Optional existing audio to prepend
            output_format: Desired output format

        Returns:
            Concatenated audio bytes

        Raises:
            ConcatenationError: If concatenation fails
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the concatenation tool is available.

        Returns:
            True if tool (e.g., ffmpeg) is installed and accessible
        """
        ...


class ConcatenationError(Exception):
    """Raised when audio concatenation fails."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(message)
