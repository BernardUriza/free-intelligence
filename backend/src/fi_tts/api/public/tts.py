"""
Public TTS Router - Text-to-Speech API

Provides TTS endpoint for demo mode and accessibility.

Provider:
- Azure OpenAI TTS (OpenAI models: nova, alloy, shimmer deployed on Azure)

Endpoints:
- POST /api/tts/synthesize - Generate speech from text

Created: 2025-11-17
Updated: 2025-12-24 (Removed OpenAI direct, Azure-only configuration)
"""

from typing import Literal

import structlog
from backend.src.fi_tts.services.tts_unified import get_unified_tts_service
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/tts", tags=["TTS"])


@router.get("/providers", summary="List configured TTS providers")
async def list_providers():
    """Return which TTS providers are configured on this backend."""
    import os

    # Azure OpenAI TTS (unified resource - shared endpoint with STT/Whisper)
    # Supports both new unified var names and legacy var names
    azure_openai_key = (
        os.getenv("AZURE_OPENAI_API_KEY")
        or os.getenv("AZURE_OPENAI_TTS_API_KEY")
        or os.getenv("AZURE_TTS_API_KEY")
    )
    azure_openai_endpoint = (
        os.getenv("AZURE_OPENAI_ENDPOINT")
        or os.getenv("AZURE_OPENAI_TTS_ENDPOINT")
        or os.getenv("AZURE_TTS_ENDPOINT")
    )
    has_azure_openai = bool(azure_openai_key and azure_openai_endpoint)

    providers = {
        "azure-openai": has_azure_openai,
    }

    return {"providers": providers}


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
        description="Voice name (nova, alloy, shimmer)",
    )
    provider: Literal["azure-openai"] | None = Field(
        default="azure-openai",
        description="TTS provider (Azure OpenAI TTS only)",
    )
    accent: str | None = Field(
        default=None,
        description="Accent instruction (auto-detected from text language)",
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
    Generate speech audio from text using OpenAI TTS with multiple provider options.

    **Use Cases:**
    - Demo mode consultation audio
    - Accessibility features (text-to-speech)
    - Training materials
    - Multilingual content with accent control

    **Provider Selection (Auto-detect):**
    - Spanish text + steerable voice (alloy/echo/shimmer) → `openai-steerable` (Mexican accent)
    - With explicit provider → use specified provider

    **Manual Override:**
    Set `provider` to "openai", "openai-steerable", or "azure-openai"

    **🎯 OpenAI Steerable TTS (Accent Control - BEST FOR SPANISH):**
    - `alloy` ⭐ - Neutral, versatile (supports Mexican Spanish accent)
    - `echo` - Male (supports Mexican Spanish accent)
    - `shimmer` - Female, clear (supports Mexican Spanish accent)

    Use with `accent="Mexican Spanish"` for natural Mexican accent!

    **🎙️ OpenAI TTS Standard (All Languages):**
    - `nova` - Female, warm (default, used in medical context)
    - `alloy` - Neutral, versatile
    - `shimmer` - Female, clear
    - `ash`, `ballad`, `coral`, `sage`, `verse` - New 2025
    - `fable` - Male, British
    - `onyx` - Male, deep

    **🌐 Azure OpenAI TTS (OpenAI via Azure):**
    Same voices as OpenAI TTS (nova, alloy, shimmer) deployed on Azure infrastructure.

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
        # Structured 400 response for validation / config errors
        logger.warning("tts.invalid_request", error=str(e))
        raise HTTPException(
            status_code=400,
            detail={
                "code": "TTS_INVALID_REQUEST",
                "message": str(e),
            },
        ) from e

    except Exception as e:
        # Structured 500 response
        logger.error("tts.synthesis_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "code": "TTS_SYNTHESIS_FAILED",
                "message": "TTS synthesis failed",
                "details": str(e),
            },
        ) from e
