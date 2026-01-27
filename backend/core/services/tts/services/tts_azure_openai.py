"""
Azure OpenAI TTS Service - OpenAI deployed on Azure infrastructure

Provides OpenAI's TTS API via Azure deployment.
Identical voices to OpenAI standard, but hosted on Azure infrastructure.

This is different from:
- OpenAI Standard TTS: api.openai.com
- Azure Speech Services: Azure-native Spanish (es-MX) voices
- Azure OpenAI TTS: OpenAI models deployed in your Azure subscription

Azure OpenAI Voices (aligned with Aurity):
- alloy (neutral, versatile)
- nova (female, warm - default for medical)
- shimmer (female, clear)

Model: gpt-4o-mini-tts (2025, supports tone/emotion control)

Endpoint Structure:
  {AZURE_OPENAI_TTS_ENDPOINT}/openai/deployments/{deployment}/audio/speech?api-version={version}

Created: 2025-12-23
Reference: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#audio
"""

from __future__ import annotations

from typing import Literal

import httpx
import os
import structlog

logger = structlog.get_logger(__name__)

# Azure OpenAI TTS configuration
# Supports unified resource (AZURE_OPENAI_*) and legacy specific TTS vars
AZURE_OPENAI_TTS_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",  # Unified resource endpoint (shared with STT)
    os.getenv(
        "AZURE_OPENAI_TTS_ENDPOINT",
        os.getenv("AZURE_TTS_ENDPOINT", ""),  # Legacy var names
    ),
)
AZURE_OPENAI_TTS_API_KEY = os.getenv(
    "AZURE_OPENAI_API_KEY",  # Unified resource API key (shared with STT)
    os.getenv(
        "AZURE_OPENAI_TTS_API_KEY",
        os.getenv("AZURE_TTS_API_KEY", ""),  # Legacy var names
    ),
)
AZURE_OPENAI_TTS_API_VERSION = os.getenv(
    "AZURE_OPENAI_TTS_API_VERSION",
    os.getenv("AZURE_TTS_API_VERSION", "2025-03-01-preview"),  # Backward compat
)
AZURE_OPENAI_TTS_DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_TTS_DEPLOYMENT",
    "tts-hd",  # Default deployment name in Azure
)

# OpenAI voice types (aligned with Aurity offering)
# Only include voices that are currently offered in Aurity
OpenAIVoiceType = Literal[
    "alloy",  # Neutral, versatile (used in Aurity)
    "nova",  # Female, warm (default for medical, used in Aurity)
    "shimmer",  # Female, clear (used in Aurity)
]

OutputFormat = Literal["mp3", "opus", "aac", "flac"]
SpeedType = float  # 0.25 to 4.0


class AzureOpenAITTSService:
    """Azure OpenAI Text-to-Speech service"""

    def __init__(
        self,
        endpoint: str = AZURE_OPENAI_TTS_ENDPOINT,
        api_key: str = AZURE_OPENAI_TTS_API_KEY,
        api_version: str = AZURE_OPENAI_TTS_API_VERSION,
        deployment: str = AZURE_OPENAI_TTS_DEPLOYMENT,
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.api_version = api_version
        self.deployment = deployment

        if not self.api_key:
            logger.warning("AZURE_OPENAI_TTS_API_KEY not configured - Azure OpenAI TTS will fail")

        if not self.endpoint:
            logger.warning("AZURE_OPENAI_TTS_ENDPOINT not configured - Azure OpenAI TTS will fail")

    async def synthesize(
        self,
        text: str,
        voice: OpenAIVoiceType = "nova",
        response_format: OutputFormat = "mp3",
        speed: SpeedType = 1.0,
    ) -> bytes:
        """
        Synthesize speech from text using Azure OpenAI TTS.

        Args:
            text: Text to synthesize (max 4096 characters)
            voice: OpenAI voice name - alloy (neutral), nova (female, default), shimmer (female)
            response_format: Audio format (mp3, opus, aac, flac)
            speed: Speech speed (0.25 to 4.0, default 1.0)

        Returns:
            Audio bytes in specified format

        Raises:
            ValueError: If text is empty or too long
            httpx.HTTPError: If API request fails
            RuntimeError: If credentials not configured
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if len(text) > 4096:
            raise ValueError(f"Text too long ({len(text)} chars, max 4096)")

        if not self.api_key:
            raise RuntimeError("Azure OpenAI API key not configured")

        if not self.endpoint:
            raise RuntimeError("Azure OpenAI endpoint not configured")

        # Build Azure OpenAI endpoint URL
        # Format: {endpoint}/openai/deployments/{deployment}/audio/speech?api-version={version}
        url = (
            f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment}"
            f"/audio/speech?api-version={self.api_version}"
        )

        logger.info(
            "azure_openai_tts.synthesize",
            text_length=len(text),
            voice=voice,
            format=response_format,
            speed=speed,
            endpoint=self.endpoint,
            deployment=self.deployment,
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "api-key": self.api_key,  # Azure uses 'api-key', not 'Authorization: Bearer'
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.deployment,  # Azure expects deployment name as model
                    "input": text,
                    "voice": voice,
                    "response_format": response_format,
                    "speed": speed,
                },
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(
                    "azure_openai_tts.error",
                    status=response.status_code,
                    error=error_text,
                    endpoint=self.endpoint,
                )
                raise httpx.HTTPError(
                    f"Azure OpenAI TTS failed ({response.status_code}): {error_text}"
                )

            audio_bytes = response.content
            logger.info(
                "azure_openai_tts.success",
                audio_size_kb=len(audio_bytes) / 1024,
                format=response_format,
            )

            return audio_bytes


# Global singleton instance
_azure_openai_tts_service: AzureOpenAITTSService | None = None


def get_azure_openai_tts_service() -> AzureOpenAITTSService:
    """Get or create the global Azure OpenAI TTS service instance"""
    global _azure_openai_tts_service
    if _azure_openai_tts_service is None:
        _azure_openai_tts_service = AzureOpenAITTSService()
    return _azure_openai_tts_service
