"""Immutable Value Objects for Checkpoint Domain.

Value Objects are immutable and defined by their attributes.
Using frozen dataclasses ensures immutability at runtime.

Best Practices:
- frozen=True: Prevents modification after creation
- slots=True: Memory efficiency, prevents dynamic attributes
- __post_init__: Validation at creation time
- No external dependencies in domain layer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class AudioFormat(Enum):
    """Supported audio formats for checkpoint concatenation."""

    WAV = "wav"
    WEBM = "webm"
    MP3 = "mp3"
    OGG = "ogg"

    @property
    def extension(self) -> str:
        return f".{self.value}"

    @property
    def ffmpeg_codec(self) -> str:
        """FFmpeg codec for this format."""
        codecs = {
            AudioFormat.WAV: "pcm_s16le",
            AudioFormat.WEBM: "libopus",
            AudioFormat.MP3: "libmp3lame",
            AudioFormat.OGG: "libvorbis",
        }
        return codecs[self]


@dataclass(frozen=True, slots=True)
class SessionId:
    """Immutable session identifier with validation.

    Example:
        >>> sid = SessionId("session_123_abc")
        >>> sid.value
        'session_123_abc'
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Session ID cannot be empty")
        if len(self.value) < 5:
            raise ValueError("Session ID must be at least 5 characters")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class AudioChunk:
    """Immutable audio chunk with metadata.

    Represents a single audio segment ready for concatenation.
    Audio data is stored as immutable bytes.
    """

    index: int
    audio_bytes: bytes
    format: AudioFormat = AudioFormat.WAV

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(f"Chunk index must be non-negative, got {self.index}")
        if not self.audio_bytes:
            raise ValueError(f"Chunk {self.index} has no audio data")

    @property
    def size_bytes(self) -> int:
        return len(self.audio_bytes)

    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024

    def has_valid_header(self) -> bool:
        """Check if audio has valid format header."""
        if len(self.audio_bytes) < 4:
            return False

        header = self.audio_bytes[:4]

        # WAV: RIFF header
        if header == b"RIFF":
            return True
        # WebM/Matroska: EBML header
        if header == bytes([0x1A, 0x45, 0xDF, 0xA3]):
            return True
        # OGG: OggS header
        if header == b"OggS":
            return True
        # MP3: ID3 or sync word
        if header[:3] == b"ID3" or (header[0] == 0xFF and header[1] in (0xFA, 0xFB)):
            return True

        return False


@dataclass(frozen=True, slots=True)
class CheckpointRange:
    """Immutable range specification for checkpoint operation.

    Defines which chunks to include in the checkpoint.
    """

    start_index: int  # Exclusive (last checkpoint)
    end_index: int  # Inclusive (new checkpoint)

    def __post_init__(self) -> None:
        if self.start_index < -1:
            raise ValueError(f"Start index must be >= -1, got {self.start_index}")
        if self.end_index < 0:
            raise ValueError(f"End index must be >= 0, got {self.end_index}")
        if self.end_index <= self.start_index:
            raise ValueError(
                f"End index ({self.end_index}) must be > start index ({self.start_index})"
            )

    @property
    def chunk_count(self) -> int:
        """Number of chunks in this range."""
        return self.end_index - self.start_index

    def contains(self, index: int) -> bool:
        """Check if index is within this range (exclusive start, inclusive end)."""
        return self.start_index < index <= self.end_index

    @classmethod
    def first_checkpoint(cls, end_index: int) -> CheckpointRange:
        """Create range for first checkpoint (from beginning)."""
        return cls(start_index=-1, end_index=end_index)


@dataclass(frozen=True, slots=True)
class CheckpointResult:
    """Immutable result of checkpoint operation.

    Contains the concatenated audio and metadata.
    """

    session_id: SessionId
    checkpoint_range: CheckpointRange
    chunks_concatenated: int
    audio_bytes: bytes
    output_format: AudioFormat
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.chunks_concatenated < 0:
            raise ValueError("chunks_concatenated must be non-negative")

    @property
    def size_bytes(self) -> int:
        return len(self.audio_bytes)

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def is_empty(self) -> bool:
        return self.chunks_concatenated == 0 or len(self.audio_bytes) == 0

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "session_id": str(self.session_id),
            "checkpoint_idx": self.checkpoint_range.end_index,
            "chunks_concatenated": self.chunks_concatenated,
            "audio_size_bytes": self.size_bytes,
            "output_format": self.output_format.value,
            "created_at": self.created_at.isoformat(),
        }
