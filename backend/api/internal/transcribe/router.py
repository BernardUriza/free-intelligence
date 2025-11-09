"""Transcription API Router.

Audio transcription endpoints (internal)

File: backend/api/transcribe/router.py
Reorganized: 2025-11-08 (moved from backend/api/transcribe.py)
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from backend.container import get_container
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class TranscriptionResponse(BaseModel):
    """Response model for transcription endpoint."""

    text: str = Field(..., description="Full transcription text")
    segments: list[dict] = Field(default_factory=list, description="Segment-level transcription")
    language: str = Field(..., description="Detected or forced language")
    duration: float = Field(..., description="Audio duration in seconds")
    available: bool = Field(..., description="Whether transcription succeeded")
    audio_file: dict = Field(..., description="Stored audio file metadata")


@router.post("", response_model=TranscriptionResponse, status_code=status.HTTP_200_OK)
async def transcribe_audio_endpoint(
    request: Request,
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
) -> TranscriptionResponse:
    """
    Upload audio file and get transcription.

    **Clean Code Architecture:**
    - TranscriptionService handles audio validation, storage, and transcription
    - Uses DI container for dependency injection
    - AuditService logs all transcription operations

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
    # Validate session ID presence
    if not x_session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required header: X-Session-ID",
        )

    try:
        # Get services from DI container
        transcription_service = get_container().get_transcription_service()
        audit_service = get_container().get_audit_service()

        # Read audio content
        audio_content = await audio.read()

        # Delegate to service for processing
        result = transcription_service.process_transcription(
            session_id=x_session_id,
            audio_content=audio_content,
            filename=audio.filename or "audio",
            content_type=audio.content_type or "audio/wav",
            metadata={
                "client_ip": request.client.host if request.client else "unknown",
            },
        )

        # Log audit trail
        audit_service.log_action(
            action="transcription_completed",
            user_id="system",
            resource=f"session:{x_session_id}",
            result="success",
            details={
                "filename": audio.filename,
                "text_length": len(result["text"]),
                "segments_count": len(result["segments"]),
                "available": result["available"],
            },
        )

        logger.info(
            f"TRANSCRIPTION_SUCCESS: session_id={x_session_id}, text_length={len(result['text'])}, available={result['available']}"
        )

        return TranscriptionResponse(
            text=result["text"],
            segments=result["segments"],
            language=result["language"],
            duration=result["duration"],
            available=result["available"],
            audio_file=result["audio_file"],
        )

    except ValueError as e:
        logger.warning(f"TRANSCRIPTION_VALIDATION_FAILED: session_id={x_session_id}, error={e!s}")
        audit_service = get_container().get_audit_service()
        audit_service.log_action(
            action="transcription_failed",
            user_id="system",
            resource=f"session:{x_session_id}",
            result="failed",
            details={"error": str(e)},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"TRANSCRIPTION_FAILED: session_id={x_session_id}, filename={audio.filename}, error={e!s}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription failed. Please try again.",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def transcribe_health_check() -> dict[str, Any]:
    """
    Health check for transcription service.

    **Clean Code Architecture:**
    - TranscriptionService handles health check via DI container

    Returns:
        Dict with whisper availability status and service health
    """
    transcription_service = get_container().get_transcription_service()
    health = transcription_service.health_check()

    return {
        "status": "operational" if health["whisper_available"] else "degraded",
        "whisper_available": health["whisper_available"],
        "message": "Transcription ready"
        if health["whisper_available"]
        else "Whisper not available (install faster-whisper)",
    }
