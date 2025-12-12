"""
OpenAI Steerable TTS Service - Accent Control via System Prompts

Uses gpt-4o-audio-preview model with Chat Completions API
to enable accent control through natural language instructions.

Key difference from tts_openai.py:
- Uses /v1/chat/completions (not /v1/audio/speech)
- Supports system prompts for accent control
- Model: gpt-4o-audio-preview (not tts-1-hd)

Example accents:
- Mexican Spanish: "Speak in a Mexican Spanish accent"
- Castilian Spanish: "Speak in a Castilian Spanish accent"
- Argentine Spanish: "Speak in an Argentine Spanish accent"

References:
- OpenAI Cookbook: https://cookbook.openai.com/examples/voice_solutions/steering_tts
- API Docs: https://platform.openai.com/docs/api-reference/chat

Created: 2025-12-08
"""

from __future__ import annotations

import base64
import os
from typing import Literal

import httpx
import structlog

logger = structlog.get_logger(__name__)

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Steerable voices (gpt-4o-audio-preview supports these)
SteerableVoiceType = Literal["alloy", "echo", "shimmer"]
OutputFormat = Literal["mp3", "opus", "flac", "wav", "pcm"]


class SteerableTTSService:
    """OpenAI Steerable TTS with accent control"""

    def __init__(self, api_key: str = OPENAI_API_KEY):
        self.api_key = api_key

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not configured - TTS will fail")

    async def synthesize(
        self,
        text: str,
        voice: SteerableVoiceType = "alloy",
        accent: str = "Mexican Spanish",
        response_format: OutputFormat = "mp3",
        speed: float = 1.0,
    ) -> bytes:
        """
        Synthesize speech with accent control.

        Args:
            text: Text to synthesize
            voice: Voice to use (alloy, echo, shimmer)
            accent: Accent instruction (e.g., "Mexican Spanish", "neutral Spanish")
            response_format: Audio format
            speed: Speech speed (slower/faster instructions in system prompt)

        Returns:
            Audio bytes
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if not self.api_key:
            raise RuntimeError("OpenAI API key not configured")

        # Build system prompt with accent instructions
        speed_instruction = ""
        if speed < 0.9:
            speed_instruction = " Speak slowly and clearly."
        elif speed > 1.1:
            speed_instruction = " Speak faster than normal."

        system_prompt = (
            f"You are a helpful assistant that generates audio from text. "
            f"Speak with a natural {accent} accent.{speed_instruction}"
        )

        url = "https://api.openai.com/v1/chat/completions"

        logger.info(
            "steerable_tts.synthesize",
            text_length=len(text),
            voice=voice,
            accent=accent,
            format=response_format,
            speed=speed,
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-audio-preview",
                    "modalities": ["text", "audio"],
                    "audio": {"voice": voice, "format": response_format},
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                },
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(
                    "steerable_tts.error",
                    status=response.status_code,
                    error=error_text,
                )
                raise httpx.HTTPError(
                    f"OpenAI Steerable TTS failed ({response.status_code}): {error_text}"
                )

            # Extract audio from response
            result = response.json()

            # Audio is in choices[0].message.audio.data (base64 encoded)
            try:
                audio_b64 = result["choices"][0]["message"]["audio"]["data"]
                audio_bytes = base64.b64decode(audio_b64)

                logger.info(
                    "steerable_tts.success",
                    audio_size_kb=len(audio_bytes) / 1024,
                    format=response_format,
                    accent=accent,
                )

                return audio_bytes
            except (KeyError, IndexError) as e:
                logger.error("steerable_tts.parse_error", error=str(e), response=result)
                raise ValueError(f"Failed to extract audio from response: {e}") from e


# Global singleton instance
_steerable_tts_service: SteerableTTSService | None = None


def get_steerable_tts_service() -> SteerableTTSService:
    """Get or create the global steerable TTS service instance"""
    global _steerable_tts_service
    if _steerable_tts_service is None:
        _steerable_tts_service = SteerableTTSService()
    return _steerable_tts_service
