"""
Public TTS Router - Text-to-Speech API

Provides multi-provider TTS endpoint for demo mode and accessibility.

Supports:
- OpenAI TTS (natural, expressive voices) - DEFAULT
- Azure Speech Services (Spanish Mexico neural voices)

Endpoints:
- POST /api/tts/synthesize - Generate speech from text

Created: 2025-11-17
Updated: 2025-12-08 (Added OpenAI TTS support)
"""

from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.src.fi_tts.services.tts_unified import get_unified_tts_service

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
    voice: str = Field(
        default="nova",
        description="Voice name (OpenAI: nova, alloy, etc. | Azure: es-MX-DaliaNeural, etc.)",
    )
    provider: Literal["openai", "openai-steerable", "azure"] | None = Field(
        default=None,
        description="TTS provider (auto-detect: Spanish + steerable voice = openai-steerable)",
    )
    accent: str | None = Field(
        default=None,
        description="Accent for steerable TTS (e.g., 'Mexican Spanish', 'neutral Spanish')",
    )
    response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = Field(
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
    summary="Synthesize Speech (Multi-Provider with Accent Control)",
    description="""
    Generate speech audio from text using OpenAI TTS, OpenAI Steerable TTS, or Azure Speech Services.

    **Use Cases:**
    - Demo mode consultation audio
    - Accessibility features (text-to-speech)
    - Training materials
    - Multilingual content with accent control

    **Provider Selection (Auto-detect):**
    - Spanish text + steerable voice (alloy/echo/shimmer) → `openai-steerable` (Mexican accent)
    - Azure voice (es-MX-*) → `azure`
    - Other voices → `openai`

    **Manual Override:**
    Set `provider` to "openai", "openai-steerable", or "azure"

    **🎯 OpenAI Steerable TTS (Accent Control - BEST FOR SPANISH):**
    - `alloy` ⭐ - Neutral, versatile (supports Mexican Spanish accent)
    - `echo` - Male (supports Mexican Spanish accent)
    - `shimmer` - Female, clear (supports Mexican Spanish accent)

    Use with `accent="Mexican Spanish"` for natural Mexican accent!

    **🎙️ OpenAI TTS Standard (English/General):**
    - `nova` - Female, warm
    - `ash`, `ballad`, `coral`, `sage`, `verse` - New 2025
    - `fable` - Male, British
    - `onyx` - Male, deep

    **🌍 Azure Speech Services (Native Spanish Mexico):**

    Female:
    - `es-MX-DaliaNeural` - Female (medical context)
    - `es-MX-BeatrizNeural`, `es-MX-CandelaNeural` (child)
    - `es-MX-CarlotaNeural`, `es-MX-DaliaMultilingualNeural`
    - `es-MX-LarissaNeural`, `es-MX-MarinaNeural`
    - `es-MX-NuriaNeural`, `es-MX-RenataNeural`

    Male:
    - `es-MX-JorgeNeural`, `es-MX-CecilioNeural`
    - `es-MX-GerardoNeural`, `es-MX-JorgeMultilingualNeural`
    - `es-MX-LibertoNeural`, `es-MX-LucianoNeural`
    - `es-MX-PelayoNeural`, `es-MX-YagoNeural`

    **Formats:**
    - `mp3` - Web-compatible (default)
    - `opus`, `aac` - Compressed
    - `flac` - Lossless
    - `wav`, `pcm` - Uncompressed

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
    Synthesize speech from text using OpenAI, OpenAI Steerable, or Azure TTS.

    Returns audio file in specified format.
    """
    try:
        tts_service = get_unified_tts_service()

        audio_bytes = await tts_service.synthesize(
            text=request.text,
            voice=request.voice,
            provider=request.provider,
            accent=request.accent,
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
