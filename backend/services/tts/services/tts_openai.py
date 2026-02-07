"""
OpenAI TTS Service - High-quality natural voices

Provides OpenAI's advanced text-to-speech with natural-sounding voices.
More expressive and human-like than Azure Speech Services.

OpenAI Voices (11 total):
- alloy (neutral, versatile)
- ash (new 2025)
- ballad (new 2025)
- coral (new 2025)
- echo (male)
- fable (male, British)
- nova (female, warm)
- onyx (male, deep)
- sage (new 2025)
- shimmer (female, clear)
- verse (new 2025)

Model: gpt-4o-mini-tts (2025, supports tone/emotion control)

Created: 2025-12-08
References:
- https://platform.openai.com/docs/api-reference/audio/createSpeech
- https://www.videosdk.live/developer-hub/ai/openai-text-to-speech
"""

from __future__ import annotations

from typing import Literal

import httpx
import os
import structlog

from backend.config.secrets import get_secret

logger = structlog.get_logger(__name__)

# OpenAI configuration
OPENAI_API_KEY = get_secret("OPENAI_API_KEY", "")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1-hd")  # tts-1 or tts-1-hd

# OpenAI voice types (11 voices as of 2025)
OpenAIVoiceType = Literal[
    "alloy",  # Neutral, versatile
    "ash",  # New 2025
    "ballad",  # New 2025
    "coral",  # New 2025
    "echo",  # Male
    "fable",  # Male, British
    "nova",  # Female, warm (default for medical)
    "onyx",  # Male, deep
    "sage",  # New 2025
    "shimmer",  # Female, clear
    "verse",  # New 2025
]

OutputFormat = Literal["mp3", "opus", "aac", "flac"]
SpeedType = float  # 0.25 to 4.0


class OpenAITTSService:
    """OpenAI Text-to-Speech service with natural voices"""

    def __init__(self, api_key: str = OPENAI_API_KEY, model: str = OPENAI_TTS_MODEL):
        self.api_key = api_key
        self.model = model

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not configured - TTS will fail")

    async def synthesize(
        self,
        text: str,
        voice: OpenAIVoiceType = "nova",
        response_format: OutputFormat = "mp3",
        speed: SpeedType = 1.0,
    ) -> bytes:
        """
        Synthesize speech from text using OpenAI TTS.

        Args:
            text: Text to synthesize (max 4096 characters)
            voice: OpenAI voice name (nova = female, default)
            response_format: Audio format (mp3, opus, aac, flac)
            speed: Speech speed (0.25 to 4.0, default 1.0)

        Returns:
            Audio bytes in specified format

        Raises:
            ValueError: If text is empty or too long
            httpx.HTTPError: If API request fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if len(text) > 4096:
            raise ValueError(f"Text too long ({len(text)} chars, max 4096)")

        if not self.api_key:
            raise RuntimeError("OpenAI API key not configured")

        url = "https://api.openai.com/v1/audio/speech"

        logger.info(
            "openai_tts.synthesize",
            text_length=len(text),
            voice=voice,
            format=response_format,
            speed=speed,
            model=self.model,
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": text,
                    "voice": voice,
                    "response_format": response_format,
                    "speed": speed,
                },
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(
                    "openai_tts.error",
                    status=response.status_code,
                    error=error_text,
                )
                raise httpx.HTTPError(f"OpenAI TTS failed ({response.status_code}): {error_text}")

            audio_bytes = response.content
            logger.info(
                "openai_tts.success",
                audio_size_kb=len(audio_bytes) / 1024,
                format=response_format,
            )

            return audio_bytes


# Global singleton instance
_openai_tts_service: OpenAITTSService | None = None


def get_openai_tts_service() -> OpenAITTSService:
    """Get or create the global OpenAI TTS service instance"""
    global _openai_tts_service
    if _openai_tts_service is None:
        _openai_tts_service = OpenAITTSService()
    return _openai_tts_service
