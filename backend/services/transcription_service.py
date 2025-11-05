"""Service layer for transcription operations.

Handles audio file validation, transcription processing, and result management.
Encapsulates whisper integration and audio storage operations.

Clean Code: This service layer makes endpoints simple and focused.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from backend.audio_storage import save_audio_file, validate_session_id
from backend.logger import get_logger
from backend.whisper_service import (
    convert_audio_to_wav,
    is_whisper_available,
    transcribe_audio,
)

logger = get_logger(__name__)


class TranscriptionService:
    """Service for transcription operations.

    Orchestrates audio file handling, transcription, and result management.
    Handles:
    - Audio file validation (MIME type, extension, size)
    - Session ID validation
    - Audio file storage with metadata
    - Whisper transcription orchestration
    - Audio format conversion (to WAV)
    - Result assembly and logging
    """

    # File size limit (100 MB)
    MAX_FILE_SIZE_MB = 100
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

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

    def __init__(self) -> None:
        """Initialize service."""
        logger.info("TranscriptionService initialized")

    def validate_session_id(self, session_id: str) -> bool:
        """Validate session ID format.

        Args:
            session_id: Session identifier

        Returns:
            True if valid UUID4 format, False otherwise
        """
        return validate_session_id(session_id)

    def validate_audio_file(self, filename: str, content_type: str, file_size: int) -> None:
        """Validate audio file attributes.

        Args:
            filename: Original filename
            content_type: MIME type
            file_size: File size in bytes

        Raises:
            ValueError: If validation fails
        """
        # Validate MIME type
        if content_type not in self.ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Invalid audio format. Allowed MIME types: {', '.join(sorted(self.ALLOWED_MIME_TYPES))}"
            )

        # Validate file extension
        file_extension = Path(filename or "").suffix.lower().lstrip(".")
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Invalid file extension: .{file_extension}. Allowed: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}"
            )

        # Validate file size
        if file_size > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File size {file_size / 1024 / 1024:.1f} MB exceeds limit of {self.MAX_FILE_SIZE_MB} MB"
            )

    def save_audio_file(
        self,
        session_id: str,
        audio_content: bytes,
        file_extension: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Save audio file to storage.

        Args:
            session_id: Session identifier
            audio_content: Raw audio bytes
            file_extension: File extension (without dot)
            metadata: Optional additional metadata

        Returns:
            Metadata dict with file_path, file_hash, ttl_seconds, etc.

        Raises:
            IOError: If file storage fails
        """
        try:
            result = save_audio_file(
                session_id=session_id,
                audio_content=audio_content,
                file_extension=file_extension,
                metadata=metadata or {},
            )
            logger.info(
                f"AUDIO_FILE_SAVED: session_id={session_id}, file_path={result['file_path']}, size={len(audio_content)}"
            )
            return result
        except OSError as e:
            logger.error(f"AUDIO_FILE_SAVE_FAILED: session_id={session_id}, error={str(e)}")
            raise

    def convert_to_wav(self, audio_path: Path, wav_path: Path) -> bool:
        """Convert audio file to WAV format.

        Args:
            audio_path: Path to source audio file
            wav_path: Path to target WAV file

        Returns:
            True if conversion successful, False otherwise
        """
        try:
            success = convert_audio_to_wav(audio_path, wav_path)
            if success:
                logger.info(f"AUDIO_CONVERSION_SUCCESS: {audio_path} -> {wav_path}")
            else:
                logger.warning(f"AUDIO_CONVERSION_FAILED: {audio_path}")
            return success
        except Exception as e:
            logger.error(f"AUDIO_CONVERSION_ERROR: {str(e)}")
            return False

    def transcribe(
        self,
        audio_path: Path,
        language: str = "es",
        vad_filter: bool = True,
    ) -> dict[str, Any]:
        """Transcribe audio file using Whisper.

        Args:
            audio_path: Path to audio file
            language: Language code (default: "es" for Spanish)
            vad_filter: Enable voice activity detection filtering

        Returns:
            Transcription result with text, segments, language, duration, available status

        Raises:
            ValueError: If transcription fails
        """
        if not is_whisper_available():
            logger.warning("WHISPER_NOT_AVAILABLE: returning degraded result")
            return {
                "text": "(Transcription unavailable - Whisper not installed)",
                "segments": [],
                "language": language,
                "duration": 0.0,
                "available": False,
            }

        try:
            result = transcribe_audio(
                audio_path=audio_path,
                language=language,
                vad_filter=vad_filter,
            )
            logger.info(
                f"TRANSCRIPTION_SUCCESS: path={audio_path}, text_length={len(result.get('text', ''))}, segments={len(result.get('segments', []))}"
            )
            return result
        except Exception as e:
            logger.error(f"TRANSCRIPTION_FAILED: file_path={audio_path}, error={str(e)}")
            raise ValueError(f"Transcription failed: {str(e)}") from e

    def process_transcription(
        self,
        session_id: str,
        audio_content: bytes,
        filename: str,
        content_type: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Process audio file and generate transcription.

        High-level orchestration method that handles:
        1. Session validation
        2. File validation
        3. File storage
        4. Format conversion (to WAV if needed)
        5. Transcription
        6. Result assembly

        Args:
            session_id: Session identifier
            audio_content: Raw audio bytes
            filename: Original filename
            content_type: MIME type
            metadata: Optional additional metadata

        Returns:
            Result dict with text, segments, language, duration, available, audio_file

        Raises:
            ValueError: If validation or processing fails
            IOError: If storage fails
        """
        # Validate session ID
        if not self.validate_session_id(session_id):
            raise ValueError(f"Invalid session_id format: {session_id}")

        # Validate audio file
        self.validate_audio_file(
            filename=filename,
            content_type=content_type,
            file_size=len(audio_content),
        )

        # Save audio file
        file_extension = Path(filename or "").suffix.lower().lstrip(".")
        audio_metadata = self.save_audio_file(
            session_id=session_id,
            audio_content=audio_content,
            file_extension=file_extension,
            metadata=metadata or {},
        )

        # Get absolute path to audio file
        from backend.audio_storage import AUDIO_STORAGE_DIR

        audio_path = AUDIO_STORAGE_DIR.parent / audio_metadata["file_path"]

        # Convert to WAV if needed (Whisper works best with WAV)
        transcription_path = audio_path
        if file_extension != "wav" and is_whisper_available():
            wav_path = audio_path.with_suffix(".wav")
            if self.convert_to_wav(audio_path, wav_path):
                transcription_path = wav_path

        # Transcribe (auto-detect language)
        transcription_result = self.transcribe(
            audio_path=transcription_path,
            language=None,  # Auto-detect language (no forcing)
            vad_filter=True,
        )

        # Assemble response
        return {
            "text": transcription_result["text"],
            "segments": transcription_result["segments"],
            "language": transcription_result["language"],
            "duration": transcription_result["duration"],
            "available": transcription_result["available"],
            "audio_file": audio_metadata,
        }

    def health_check(self) -> dict[str, Any]:
        """Check transcription service health.

        Returns:
            Health status dict with whisper_available flag
        """
        return {
            "status": "healthy",
            "whisper_available": is_whisper_available(),
        }
