"""
Text-to-Speech Service - Azure OpenAI TTS

Provides high-quality speech synthesis for demo mode and accessibility features.

Endpoint: https://csp-westus3-uat-aoai1.openai.azure.com/openai/deployments/tts-hd/audio/speech?api-version=2025-03-01-preview
Model: tts-hd (HD quality)
Voices: alloy, echo, fable, onyx, nova, shimmer

Created: 2025-11-17
"""

import os
from typing import Literal, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

# Azure OpenAI TTS configuration
AZURE_TTS_ENDPOINT = os.getenv(
    "AZURE_TTS_ENDPOINT",
    "https://csp-westus3-uat-aoai1.openai.azure.com/openai/deployments/tts-hd/audio/speech",
)
AZURE_TTS_API_KEY = os.getenv("AZURE_TTS_API_KEY", "")
AZURE_TTS_API_VERSION = os.getenv("AZURE_TTS_API_VERSION", "2025-03-01-preview")

VoiceType = Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
OutputFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]
SpeedType = float  # 0.25 to 4.0


class TTSService:
    """Azure OpenAI Text-to-Speech service"""

    def __init__(
        self,
        endpoint: str = AZURE_TTS_ENDPOINT,
        api_key: str = AZURE_TTS_API_KEY,
        api_version: str = AZURE_TTS_API_VERSION,
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.api_version = api_version

        if not self.api_key:
            logger.warning("AZURE_TTS_API_KEY not configured - TTS will fail")

    async def synthesize(
        self,
        text: str,
        voice: VoiceType = "nova",
        response_format: OutputFormat = "mp3",
        speed: SpeedType = 1.0,
    ) -> bytes:
        """
        Synthesize speech from text using Azure OpenAI TTS.

        Args:
            text: Text to synthesize (max 4096 characters)
            voice: Voice to use (nova = female, default for medical context)
            response_format: Audio format (mp3 default for web compatibility)
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
            raise RuntimeError("Azure TTS API key not configured")

        url = f"{self.endpoint}?api-version={self.api_version}"

        logger.info(
            "tts.synthesize",
            text_length=len(text),
            voice=voice,
            format=response_format,
            speed=speed,
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "api-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "input": text,
                    "voice": voice,
                    "response_format": response_format,
                    "speed": speed,
                },
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(
                    "tts.error",
                    status=response.status_code,
                    error=error_text,
                )
                raise httpx.HTTPError(f"Azure TTS failed ({response.status_code}): {error_text}")

            audio_bytes = response.content
            logger.info(
                "tts.success",
                audio_size_kb=len(audio_bytes) / 1024,
                format=response_format,
            )

            return audio_bytes


# Global singleton instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get or create the global TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
