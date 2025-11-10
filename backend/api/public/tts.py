"""Azure TTS (Text-to-Speech) API endpoint.

Card: FI-BACKEND-TTS-001

Simple endpoint for generating audio from text using Azure Cognitive Services.

Endpoints:
- POST /api/tts/synthesize - Generate audio from text

Environment variables required:
- AZURE_TTS_ENDPOINT: Azure TTS endpoint URL
- AZURE_TTS_KEY: Azure TTS subscription key

File: backend/api/public/tts.py
Created: 2025-11-09
"""

from __future__ import annotations

import os
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tts", tags=["tts"])


class TTSRequest(BaseModel):
    """Request model for TTS synthesis."""

    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    voice: Optional[str] = Field(
        "es-MX-DaliaNeural",
        description="Voice name (default: es-MX-DaliaNeural)",
    )
    rate: Optional[str] = Field("0%", description="Speech rate (-50% to +100%)")
    pitch: Optional[str] = Field("0%", description="Speech pitch (-50% to +50%)")


@router.post("/synthesize", response_class=Response)
async def synthesize_speech(request: TTSRequest) -> Response:
    """
    Synthesize speech from text using Azure TTS.

    **Args:**
    - text: Text to convert to speech (max 5000 chars)
    - voice: Voice name (e.g., es-MX-DaliaNeural, en-US-AriaNeural)
    - rate: Speech rate adjustment (-50% to +100%)
    - pitch: Pitch adjustment (-50% to +50%)

    **Returns:**
    - Audio file (audio/mpeg) - MP3 format

    **Errors:**
    - 400: Invalid request (text too long, invalid parameters)
    - 500: TTS generation failed
    - 503: Azure TTS credentials not configured

    **Example:**
    ```bash
    curl -X POST http://localhost:7001/api/tts/synthesize \\
      -H "Content-Type: application/json" \\
      -d '{"text": "Hola doctor, me duele la cabeza"}' \\
      --output test.mp3
    ```
    """
    # Get Azure credentials from environment
    endpoint = os.getenv("AZURE_TTS_ENDPOINT")
    api_key = os.getenv("AZURE_TTS_KEY")

    if not endpoint or not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure TTS not configured (missing AZURE_TTS_ENDPOINT or AZURE_TTS_KEY)",
        )

    try:
        # Azure OpenAI TTS uses JSON format (not SSML)
        payload = {
            "model": "tts-1-hd",
            "input": request.text,
            "voice": "alloy",  # Azure OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
            "speed": 1.0,
        }

        headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
        }

        logger.info(
            "TTS_SYNTHESIZE_START",
            text_length=len(request.text),
            voice=payload["voice"],
            endpoint=endpoint,
        )

        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)

        if response.status_code != 200:
            logger.error(
                "TTS_AZURE_ERROR",
                status_code=response.status_code,
                error=response.text,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Azure TTS error: {response.status_code}",
            )

        audio_content = response.content
        logger.info("TTS_SYNTHESIZE_SUCCESS", audio_size=len(audio_content))

        return Response(
            content=audio_content,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=synthesized.mp3",
            },
        )

    except requests.Timeout:
        logger.error("TTS_TIMEOUT")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Azure TTS timeout (30s)",
        )
    except Exception as e:
        logger.error("TTS_SYNTHESIS_FAILED", error=str(e), error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TTS synthesis failed",
        )


@router.get("/voices")
async def list_voices():
    """
    List common Azure TTS voices.

    **Returns:**
    - Dictionary of common voices by language
    """
    return {
        "es-MX": [
            {
                "name": "es-MX-DaliaNeural",
                "gender": "Female",
                "description": "Mexican Spanish - Dalia",
            },
            {
                "name": "es-MX-JorgeNeural",
                "gender": "Male",
                "description": "Mexican Spanish - Jorge",
            },
        ],
        "es-ES": [
            {
                "name": "es-ES-ElviraNeural",
                "gender": "Female",
                "description": "Spain Spanish - Elvira",
            },
            {
                "name": "es-ES-AlvaroNeural",
                "gender": "Male",
                "description": "Spain Spanish - Alvaro",
            },
        ],
        "en-US": [
            {"name": "en-US-AriaNeural", "gender": "Female", "description": "US English - Aria"},
            {"name": "en-US-GuyNeural", "gender": "Male", "description": "US English - Guy"},
        ],
    }
