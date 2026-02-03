"""Unified transcription service with integrated Whisper and audio processing.

Handles all aspects of audio transcription:
  - Audio file validation (MIME type, extension, size)
  - Session ID validation
  - Audio file storage with metadata
  - Whisper model management (lazy loading, singleton)
  - Audio format conversion (to WAV)
  - Speech recognition and result assembly

The service encapsulates all transcription concerns in one cohesive class.

Card: FI-BACKEND-FEAT-003
Created: 2025-10-30
Refactored: 2025-11-05 (consolidated whisper_utils)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from backend.services.transcription.services.whisper import (
    CPU_THREADS,
    NUM_WORKERS,
    WHISPER_BEAM_SIZE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    WHISPER_LANGUAGE,
    WHISPER_MODEL_SIZE,
)
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

# Check if faster-whisper is available (from whisper module)
try:
    from faster_whisper import WhisperModel

    _WHISPER_AVAILABLE = True  # pyright: ignore[reportConstantRedefinition]
except ImportError:
    _WHISPER_AVAILABLE = False  # pyright: ignore[reportConstantRedefinition]
    WhisperModel = None


class TranscriptionService:
    """Unified service for all transcription operations.

    Encapsulates:
        - Audio file validation (MIME type, extension, size)
        - Session ID validation
        - Audio file storage with metadata
        - Whisper model management (lazy loading, singleton)
        - Audio format conversion (to WAV)
        - Transcription and result assembly

    The service is self-contained with all dependencies managed internally.
    Think of it as a complete kitchen station with all equipment needed.

    Example:
        >>> service = TranscriptionService()
        >>> result = service.process_transcription(
        ...     session_id="550e8400-e29b-41d4-a716-446655440000",
        ...     audio_content=b"...",
        ...     filename="recording.webm",
        ...     content_type="audio/webm"
        ... )
        >>> print(result["text"])
        "Hola, esto es una prueba."
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
        """Initialize TranscriptionService.

        Sets up internal state including:
          - Singleton Whisper model instance (lazy-loaded)
          - Whisper availability flag
        """
        self._whisper_model_instance: Any | None = None
        self._whisper_available = _WHISPER_AVAILABLE
        logger.info(
            "TranscriptionService initialized",
            extra={"whisper_available": self._whisper_available},
        )

    # ─────────────────────────────────────────────────────────────────────
    # Whisper Model Management (Internal)
    # ─────────────────────────────────────────────────────────────────────

    def _get_whisper_model(self) -> Any | None:
        """Get singleton WhisperModel instance (lazy loading).

        Returns:
            WhisperModel instance or None if not available.

        Notes:
            - First call will download model (~3GB for large-v3)
            - Subsequent calls return cached instance
            - Returns None if faster-whisper not installed
        """
        if not self._whisper_available:
            return None

        if self._whisper_model_instance is None:
            try:
                assert WhisperModel is not None, "WhisperModel not imported"

                # Log cold start
                logger.warning(
                    "WHISPER_MODEL_COLD_START: First transcription will be slow (~10-30s)",
                    extra={
                        "model_size": WHISPER_MODEL_SIZE,
                        "device": WHISPER_DEVICE,
                        "compute_type": WHISPER_COMPUTE_TYPE,
                    },
                )

                self._whisper_model_instance = WhisperModel(
                    WHISPER_MODEL_SIZE,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE_TYPE,
                    cpu_threads=CPU_THREADS,
                    num_workers=NUM_WORKERS,
                    download_root=os.getenv("WHISPER_CACHE_DIR") or None,
                )

                logger.info("WHISPER_MODEL_LOADED: Model ready for transcription")
            except Exception as e:
                logger.error(
                    f"WHISPER_MODEL_LOAD_FAILED: {e!s}",
                    extra={"model_size": WHISPER_MODEL_SIZE, "error": str(e)},
                )
                return None

        return self._whisper_model_instance

    def _is_whisper_available(self) -> bool:
        """Check if Whisper transcription is available.

        Returns:
            True if faster-whisper is installed and can be used.
        """
        return self._whisper_available

    # ─────────────────────────────────────────────────────────────────────
    # Audio Format Conversion (Internal)
    # ─────────────────────────────────────────────────────────────────────

    def _convert_audio_to_wav(self, input_path: Path, output_path: Path) -> bool:
        """Convert audio file to WAV format using ffmpeg.

        Args:
            input_path: Path to source audio file.
            output_path: Path to target WAV file.

        Returns:
            True if conversion succeeded, False otherwise.

        Notes:
            - Target: 16kHz mono for Whisper optimization
            - Requires ffmpeg binary and ffmpeg-python package
            - Returns False gracefully if dependencies missing
        """
        try:
            import ffmpeg

            logger.info(
                "AUDIO_CONVERSION_START",
                extra={
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                },
            )

            # Convert to WAV (16kHz mono for Whisper optimization)
            stream = ffmpeg.input(str(input_path))
            stream = ffmpeg.output(stream, str(output_path), ar=16000, ac=1)
            ffmpeg.run(
                stream,
                overwrite_output=True,
                capture_stdout=True,
                capture_stderr=True,
            )

            logger.info(
                "AUDIO_CONVERSION_COMPLETE",
                extra={
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                },
            )
            return True

        except ImportError:
            logger.warning(
                "AUDIO_CONVERSION_SKIPPED: ffmpeg-python not installed. "
                "Install with: pip install ffmpeg-python && brew install ffmpeg"
            )
            return False
        except Exception as e:
            logger.error(
                f"AUDIO_CONVERSION_FAILED: {e!s}",
                extra={
                    "input_path": str(input_path),
                    "output_path": str(output_path),
                    "error": str(e),
                },
            )
            return False

    # ─────────────────────────────────────────────────────────────────────
    # Transcription (Internal)
    # ─────────────────────────────────────────────────────────────────────

    def _transcribe_with_whisper(
        self,
        audio_path: Path,
        language: str | None = None,
        vad_filter: bool = True,
    ) -> dict[str, Any]:
        """Transcribe audio file using internal Whisper model.

        Args:
            audio_path: Path to audio file (WAV, MP3, M4A, WEBM supported).
            language: Language code (default: None for auto-detect).
                Examples: "es", "en", "fr".
            vad_filter: Enable Voice Activity Detection filtering (default: True).

        Returns:
            Dict with:
                - text: Full transcription (joined segments)
                - segments: List of segments with timestamps
                - language: Detected or forced language
                - duration: Audio duration in seconds
                - available: Whether transcription succeeded

        Raises:
            ValueError: If transcription fails due to file not found or read error.
        """
        if language is None:
            language = WHISPER_LANGUAGE

        # Check if Whisper is available
        if not self._is_whisper_available():
            logger.warning(
                "WHISPER_TRANSCRIPTION_SKIPPED: faster-whisper not available",
                extra={"audio_path": str(audio_path)},
            )
            return {
                "text": "(Transcription unavailable - Whisper not installed)",
                "segments": [],
                "language": language,
                "duration": 0.0,
                "available": False,
            }

        # Get model
        model = self._get_whisper_model()
        if model is None:
            logger.error(
                "WHISPER_MODEL_NOT_LOADED",
                extra={"audio_path": str(audio_path)},
            )
            return {
                "text": "(Transcription failed - model not loaded)",
                "segments": [],
                "language": language,
                "duration": 0.0,
                "available": False,
            }

        try:
            logger.info(
                "WHISPER_TRANSCRIPTION_START",
                extra={
                    "audio_path": str(audio_path),
                    "language": language,
                    "vad_filter": vad_filter,
                },
            )

            # Transcribe
            segments_iter, info = model.transcribe(
                str(audio_path),
                language=language,
                vad_filter=vad_filter,
                beam_size=WHISPER_BEAM_SIZE,
            )

            # Collect segments
            segments_list: list[dict[str, Any]] = []
            full_text_parts: list[str] = []

            for segment in segments_iter:
                segment_dict: dict[str, Any] = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
                segments_list.append(segment_dict)
                full_text_parts.append(segment.text.strip())

            # Join all segments
            full_text = " ".join(full_text_parts)

            logger.info(
                "WHISPER_TRANSCRIPTION_COMPLETE",
                extra={
                    "audio_path": str(audio_path),
                    "language": info.language,
                    "duration": info.duration,
                    "segments_count": len(segments_list),
                    "text_length": len(full_text),
                },
            )

            return {
                "text": full_text,
                "segments": segments_list,
                "language": info.language,
                "duration": info.duration,
                "available": True,
            }

        except FileNotFoundError as e:
            logger.error(
                f"WHISPER_TRANSCRIPTION_FAILED: File not found - {e!s}",
                extra={"audio_path": str(audio_path)},
            )
            raise ValueError(f"Audio file not found: {audio_path}") from e
        except Exception as e:
            logger.error(
                f"WHISPER_TRANSCRIPTION_FAILED: {e!s}",
                extra={"audio_path": str(audio_path), "error": str(e)},
            )
            raise ValueError(f"Transcription failed: {e!s}") from e

    # ─────────────────────────────────────────────────────────────────────
    # Public API Methods
    # ─────────────────────────────────────────────────────────────────────

    def validate_session_id(self, session_id: str) -> bool:
        """Validate session ID format.

        Args:
            session_id: Session identifier.

        Returns:
            True if valid UUID4 format, False otherwise.
        """
        # FIXME: validators.session.validate_session_id() raises HTTPException (doesn't return bool)
        # Signature mismatch - need to either:
        # 1. Import validators.session.validate_session_id and catch exception, return bool
        # 2. Implement validation logic here
        # For now, basic validation:
        import re
        if not session_id or len(session_id) < 10 or len(session_id) > 128:
            return False
        return bool(re.match(r"^[a-zA-Z0-9_-]+$", session_id))

    def validate_audio_file(self, filename: str, content_type: str, file_size: int) -> None:
        """Validate audio file attributes.

        Args:
            filename: Original filename.
            content_type: MIME type.
            file_size: File size in bytes.

        Raises:
            ValueError: If validation fails (invalid type, extension, or size).
        """
        # Validate MIME type
        if content_type not in self.ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Invalid audio format. Allowed MIME types: "
                f"{', '.join(sorted(self.ALLOWED_MIME_TYPES))}"
            )

        # Validate file extension
        file_extension = Path(filename or "").suffix.lower().lstrip(".")
        if file_extension not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Invalid file extension: .{file_extension}. "
                f"Allowed: {', '.join(sorted(self.ALLOWED_EXTENSIONS))}"
            )

        # Validate file size
        if file_size > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File size {file_size / 1024 / 1024:.1f} MB exceeds limit of "
                f"{self.MAX_FILE_SIZE_MB} MB"
            )

    def save_audio_file(
        self,
        session_id: str,
        audio_content: bytes,
        file_extension: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """[DEPRECATED] Save audio file to storage.

        DEPRECATED: This method is no longer used in production.
        Modern audio flow uses WebSocket streaming with chunk-based storage:
        - backend/infrastructure/common/services/medical_chunk_handler.py
        - backend/repositories/hdf5_audio_chunk_repository.py

        The new flow processes audio in real-time chunks via:
        POST /api/aurity/transcription/stream (streaming WebSocket)

        This method exists only for backward compatibility with tests.
        DO NOT call this in production code.

        Args:
            session_id: Session identifier.
            audio_content: Raw audio bytes.
            file_extension: File extension (without dot, e.g., "webm").
            metadata: Optional additional metadata dict.

        Raises:
            NotImplementedError: Always - use WebSocket streaming instead.
        """
        raise NotImplementedError(
            "DEPRECATED: save_audio_file is obsolete. "
            "Use WebSocket streaming at /api/aurity/transcription/stream instead. "
            "Audio is now processed in real-time chunks via medical_chunk_handler."
        )

    def transcribe(
        self,
        audio_path: Path,
        language: str | None = None,
        vad_filter: bool = True,
    ) -> dict[str, Any]:
        """Transcribe audio file using Whisper.

        Args:
            audio_path: Path to audio file.
            language: Language code (default: None for auto-detect).
                Examples: "es" (Spanish), "en" (English), "fr" (French).
            vad_filter: Enable voice activity detection filtering (default: True).

        Returns:
            Transcription result dict with text, segments, language, duration, available.

        Raises:
            ValueError: If transcription fails.
        """
        return self._transcribe_with_whisper(audio_path, language, vad_filter)

    def convert_to_wav(self, audio_path: Path, wav_path: Path) -> bool:
        """Convert audio file to WAV format.

        Args:
            audio_path: Path to source audio file.
            wav_path: Path to target WAV file.

        Returns:
            True if conversion successful, False otherwise.
        """
        try:
            success = self._convert_audio_to_wav(audio_path, wav_path)
            if success:
                logger.info(f"AUDIO_CONVERSION_SUCCESS: {audio_path} -> {wav_path}")
            else:
                logger.warning(f"AUDIO_CONVERSION_FAILED: {audio_path}")
            return success
        except Exception as e:
            logger.error(f"AUDIO_CONVERSION_ERROR: {e!s}")
            return False

    def process_transcription(
        self,
        session_id: str,
        audio_content: bytes,
        filename: str,
        content_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """[DEPRECATED] Process audio file and generate transcription.

        DEPRECATED: This method is no longer used in production.
        Modern transcription uses real-time WebSocket streaming:

        New Architecture:
        1. Client connects to /api/aurity/transcription/stream (WebSocket)
        2. Audio chunks sent in real-time via medical_chunk_handler
        3. Whisper processes chunks incrementally
        4. Results stored in HDF5 via hdf5_audio_chunk_repository

        This monolithic approach was replaced by the streaming architecture
        for better UX (real-time feedback) and memory efficiency (no full
        audio file in memory).

        Args:
            session_id: Session identifier (UUID4 format).
            audio_content: Raw audio bytes.
            filename: Original filename.
            content_type: MIME type (e.g., "audio/webm").
            metadata: Optional additional metadata dict.

        Raises:
            NotImplementedError: Always - use WebSocket streaming instead.
        """
        # Suppress unused argument warnings - method is deprecated
        _ = (session_id, audio_content, filename, content_type, metadata)

        raise NotImplementedError(
            "DEPRECATED: process_transcription is obsolete. "
            "Use WebSocket streaming at /api/aurity/transcription/stream instead. "
            "See backend/api/domains/aurity/transcription/streaming.py for the modern flow."
        )

    def health_check(self) -> dict[str, Any]:
        """Check transcription service health.

        Returns:
            Health status dict with whisper_available flag.
        """
        return {
            "status": "healthy",
            "whisper_available": self._is_whisper_available(),
        }
