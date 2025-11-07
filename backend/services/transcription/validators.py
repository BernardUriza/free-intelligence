"""Audio file and session validators.

Validation logic for:
  - Session ID format (UUID4)
  - Audio file properties (MIME type, extension, size)
"""

from __future__ import annotations

from pathlib import Path

from fi_common.storage.audio_storage import (
    validate_session_id as storage_validate_session_id,
)


class ValidationError(ValueError):
    """Raised when validation fails."""

    pass


class SessionValidator:
    """Validates session IDs."""

    @staticmethod
    def validate(session_id: str) -> bool:
        """Validate session ID format (UUID4).

        Args:
            session_id: Session identifier.

        Returns:
            True if valid UUID4 format, False otherwise.
        """
        return storage_validate_session_id(session_id)


class AudioFileValidator:
    """Validates audio files."""

    # Allowed MIME types
    ALLOWED_MIME_TYPES = {
        "audio/webm",
        "audio/wav",
        "audio/wave",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/m4a",
        "audio/ogg",
    }

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {"webm", "wav", "mp3", "m4a", "ogg"}

    # File size limit (100 MB)
    MAX_FILE_SIZE_MB = 100
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    @classmethod
    def validate(cls, filename: str, content_type: str, file_size: int) -> None:
        """Validate audio file attributes.

        Args:
            filename: Original filename.
            content_type: MIME type.
            file_size: File size in bytes.

        Raises:
            ValidationError: If validation fails.
        """
        cls._validate_mime_type(content_type)
        cls._validate_extension(filename)
        cls._validate_size(file_size)

    @classmethod
    def _validate_mime_type(cls, content_type: str) -> None:
        """Validate MIME type."""
        if content_type not in cls.ALLOWED_MIME_TYPES:
            raise ValidationError(
                f"Invalid audio format. Allowed MIME types: "
                f"{', '.join(sorted(cls.ALLOWED_MIME_TYPES))}"
            )

    @classmethod
    def _validate_extension(cls, filename: str) -> None:
        """Validate file extension."""
        file_extension = Path(filename or "").suffix.lower().lstrip(".")
        if file_extension not in cls.ALLOWED_EXTENSIONS:
            raise ValidationError(
                f"Invalid file extension: .{file_extension}. "
                f"Allowed: {', '.join(sorted(cls.ALLOWED_EXTENSIONS))}"
            )

    @classmethod
    def _validate_size(cls, file_size: int) -> None:
        """Validate file size."""
        if file_size > cls.MAX_FILE_SIZE_BYTES:
            raise ValidationError(
                f"File size {file_size / 1024 / 1024:.1f} MB exceeds limit of "
                f"{cls.MAX_FILE_SIZE_MB} MB"
            )
