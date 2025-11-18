"""
Public TTS Router - Text-to-Speech API

Provides Azure OpenAI TTS endpoint for demo mode and accessibility.

Endpoints:
- POST /api/tts/synthesize - Generate speech from text

Created: 2025-11-17
"""

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.services.tts_service import OutputFormat, VoiceType, get_tts_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/tts", tags=["TTS"])


class TTSRequest(BaseModel):
    """Request model for TTS synthesis"""

    text: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Text to synthesize (max 4096 characters)",
        examples=["Buenos días, ¿cómo se encuentra hoy?"],
    )
    voice: VoiceType = Field(
        default="nova",
        description="Voice to use (nova = female, alloy = neutral male)",
    )
    response_format: OutputFormat = Field(
        default="mp3",
        description="Audio output format (mp3 recommended for web)",
    )
    speed: float = Field(
        default=1.0,
        ge=0.25,
        le=4.0,
        description="Speech speed (0.25 to 4.0)",
    )


@router.post(
    "/synthesize",
    response_class=Response,
    summary="Synthesize Speech",
    description="""
    Generate speech audio from text using Azure OpenAI TTS.

    **Use Cases:**
    - Demo mode consultation audio
    - Accessibility features (text-to-speech)
    - Training materials

    **Voices:**
    - `nova` - Female (default, medical context)
    - `alloy` - Neutral male
    - `echo` - Male
    - `fable` - British male
    - `onyx` - Deep male
    - `shimmer` - Female

    **Formats:**
    - `mp3` - Web-compatible (default)
    - `opus` - High compression
    - `aac` - Apple devices
    - `flac` - Lossless
    - `wav` - Uncompressed
    - `pcm` - Raw audio

    **Response:**
    Binary audio data with appropriate Content-Type header.
    """,
    responses={
        200: {
            "description": "Audio file generated successfully",
            "content": {
                "audio/mpeg": {"example": "<binary audio data>"},
            },
        },
        400: {
            "description": "Invalid request (text too long, empty, etc.)",
        },
        500: {
            "description": "Azure TTS service error",
        },
    },
)
async def synthesize_speech(request: TTSRequest) -> Response:
    """
    Synthesize speech from text.

    Returns audio file in specified format.
    """
    try:
        tts_service = get_tts_service()

        audio_bytes = await tts_service.synthesize(
            text=request.text,
            voice=request.voice,
            response_format=request.response_format,
            speed=request.speed,
        )

        # Determine Content-Type based on format
        content_types = {
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "aac": "audio/aac",
            "flac": "audio/flac",
            "wav": "audio/wav",
            "pcm": "audio/pcm",
        }

        content_type = content_types.get(request.response_format, "audio/mpeg")

        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="speech.{request.response_format}"',
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            },
        )

    except ValueError as e:
        logger.warning("tts.invalid_request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e

    except Exception as e:
        logger.error("tts.synthesis_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis failed: {e!s}",
        ) from e
