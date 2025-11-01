from __future__ import annotations

"""
Transcription API Router
Cards: FI-BACKEND-FEAT-003, FI-UI-FEAT-210

Endpoints:
  POST /api/transcribe - Upload audio and get transcription

Features:
- Audio upload with multipart/form-data
- Max file size: 100 MB
- Supported formats: webm, wav, mp3, m4a, ogg
- Session-based storage with TTL (7 days)
- SHA256 manifest for integrity
- Whisper transcription (Spanish)
- Graceful degradation if Whisper unavailable

File: backend/api/transcribe.py
Created: 2025-10-30
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from backend.audio_storage import save_audio_file, validate_session_id
from backend.logger import get_logger
from backend.whisper_service import (
    convert_audio_to_wav,
    is_whisper_available,
    transcribe_audio,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/transcribe")

# File size limit (100 MB)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_AUDIO_FILE_SIZE_MB", "100"))
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


class TranscriptionResponse(BaseModel):
    """Response model for transcription endpoint."""

    text: str = Field(..., description="Full transcription text")
    segments: list[dict] = Field(default_factory=list, description="Segment-level transcription")
    language: str = Field(..., description="Detected or forced language")
    duration: float = Field(..., description="Audio duration in seconds")
    available: bool = Field(..., description="Whether transcription succeeded")
    audio_file: dict = Field(..., description="Stored audio file metadata")


def validate_audio_file(file: UploadFile) -> None:
    """
    Validate uploaded audio file.

    Args:
        file: FastAPI UploadFile

    Raises:
        HTTPException 400: If file invalid (type, size, extension)
    """
    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid audio format. Allowed MIME types: {', '.join(ALLOWED_MIME_TYPES)}",
        )

    # Validate file extension
    file_extension = Path(file.filename or "").suffix.lower().lstrip(".")
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension: .{file_extension}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )


@router.post("", response_model=TranscriptionResponse, status_code=status.HTTP_200_OK)
async def transcribe_audio_endpoint(
    request: Request,
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> TranscriptionResponse:
    """
    Upload audio file and get transcription.

    **Request:**
    - Method: POST
    - Content-Type: multipart/form-data
    - Header: X-Session-ID (required, UUID4 format)
    - Body: audio file (max 100 MB, formats: webm, wav, mp3, m4a, ogg)

    **Response:**
    - text: Full transcription (joined segments)
    - segments: List of segments with start/end timestamps
    - language: Detected or forced language (default: "es")
    - duration: Audio duration in seconds
    - available: Whether transcription succeeded (false if Whisper unavailable)
    - audio_file: Stored file metadata (path, hash, TTL)

    **Errors:**
    - 400: Invalid session_id, file type, or file size
    - 500: Transcription or storage failure

    **Notes:**
    - Audio stored in: storage/audio/{session_id}/{timestamp_ms}.{ext}
    - TTL: 7 days (auto-delete after expiration)
    - If faster-whisper not installed, returns placeholder text with available=false
    """
    # Validate session_id
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required header: X-Session-ID",
        )

    if not validate_session_id(x_session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid session_id format: {x_session_id} (must be UUID4)",
        )

    # Validate audio file
    validate_audio_file(audio)

    try:
        # Read file content
        logger.info(
            "AUDIO_UPLOAD_START",
            session_id=x_session_id,
            filename=audio.filename,
            content_type=audio.content_type,
        )

        audio_content = await audio.read()
        file_size = len(audio_content)

        # Check file size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size {file_size / 1024 / 1024:.1f} MB exceeds limit of {MAX_FILE_SIZE_MB} MB",
            )

        # Get file extension
        file_extension = Path(audio.filename or "").suffix.lower().lstrip(".")

        # Save audio file
        audio_metadata = save_audio_file(
            session_id=x_session_id,
            audio_content=audio_content,
            file_extension=file_extension,
            metadata={
                "original_filename": audio.filename,
                "content_type": audio.content_type,
                "file_size": file_size,
            },
        )

        logger.info(
            "AUDIO_UPLOAD_COMPLETE",
            session_id=x_session_id,
            file_path=audio_metadata["file_path"],
            file_size=file_size,
            file_hash=audio_metadata["file_hash"],
        )

        # Transcribe audio
        # Get absolute path to audio file
        from backend.audio_storage import AUDIO_STORAGE_DIR

        audio_path = AUDIO_STORAGE_DIR.parent / audio_metadata["file_path"]

        # Convert to WAV if needed (Whisper works best with WAV)
        if file_extension != "wav" and is_whisper_available():
            wav_path = audio_path.with_suffix(".wav")
            conversion_ok = convert_audio_to_wav(audio_path, wav_path)
            if conversion_ok:
                transcription_path = wav_path
            else:
                # Fallback to original file
                transcription_path = audio_path
        else:
            transcription_path = audio_path

        # Transcribe
        transcription_result = transcribe_audio(
            audio_path=transcription_path,
            language="es",  # Force Spanish
            vad_filter=True,  # Enable VAD filtering
        )

        logger.info(
            "TRANSCRIPTION_COMPLETE",
            session_id=x_session_id,
            text_length=len(transcription_result["text"]),
            segments_count=len(transcription_result["segments"]),
            available=transcription_result["available"],
        )

        return TranscriptionResponse(
            text=transcription_result["text"],
            segments=transcription_result["segments"],
            language=transcription_result["language"],
            duration=transcription_result["duration"],
            available=transcription_result["available"],
            audio_file=audio_metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "TRANSCRIPTION_REQUEST_FAILED",
            session_id=x_session_id,
            filename=audio.filename,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription failed. Please try again.",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def transcribe_health_check():
    """
    Health check for transcription service.

    Returns:
        Dict with whisper availability status
    """
    whisper_ok = is_whisper_available()

    return {
        "status": "operational" if whisper_ok else "degraded",
        "whisper_available": whisper_ok,
        "message": "Transcription ready"
        if whisper_ok
        else "Whisper not available (install faster-whisper)",
    }
