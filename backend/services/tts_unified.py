"""
Unified TTS Service - Multi-provider text-to-speech

Supports both Azure Speech Services and OpenAI TTS with automatic provider selection.

Provider Selection Strategy:
1. OpenAI TTS (default) - Natural, expressive voices
   - Best for: Demo mode, user-facing applications, natural conversations
   - Voices: alloy, nova, shimmer, etc. (11 total)
   - Model: gpt-4o-mini-tts (2025)

2. Azure Speech Services - High-quality neural voices
   - Best for: Spanish (Mexico) content, medical terminology
   - Voices: es-MX-DaliaNeural, es-MX-JorgeNeural, etc. (17 total)
   - Locale: Spanish Mexico (es-MX)

Usage:
    tts = get_unified_tts_service()
    audio = await tts.synthesize(
        text="Hello world",
        voice="nova",           # OpenAI voice
        provider="openai"       # or "azure"
    )

Created: 2025-12-08
"""

from __future__ import annotations

from typing import Literal

import structlog

from backend.services.tts_openai import get_openai_tts_service
from backend.services.tts_service import get_tts_service

logger = structlog.get_logger(__name__)

ProviderType = Literal["openai", "azure"]
OutputFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]


class UnifiedTTSService:
    """Unified TTS service supporting multiple providers"""

    def __init__(self):
        self.openai_service = get_openai_tts_service()
        self.azure_service = get_tts_service()

    async def synthesize(
        self,
        text: str,
        voice: str = "nova",  # Can be OpenAI or Azure voice
        provider: ProviderType | None = None,  # Auto-detect if None
        response_format: OutputFormat = "mp3",
        speed: float = 1.0,
    ) -> bytes:
        """
        Synthesize speech using the specified or auto-detected provider.

        Args:
            text: Text to synthesize (max 4096 characters)
            voice: Voice name (OpenAI: nova, alloy, etc. | Azure: es-MX-DaliaNeural, etc.)
            provider: Force specific provider ("openai" or "azure"), or None for auto-detect
            response_format: Audio format (mp3, opus, aac, flac, wav, pcm)
            speed: Speech speed (0.25 to 4.0)

        Returns:
            Audio bytes in specified format
        """
        # Auto-detect provider based on voice name if not specified
        if provider is None:
            if voice.startswith("es-MX-"):
                provider = "azure"
                logger.info("tts.auto_provider", provider="azure", reason="es-MX voice")
            else:
                provider = "openai"
                logger.info("tts.auto_provider", provider="openai", reason="default")

        # Route to appropriate provider
        if provider == "openai":
            logger.info(
                "tts.synthesize",
                provider="openai",
                voice=voice,
                text_length=len(text),
            )
            return await self.openai_service.synthesize(
                text=text,
                voice=voice,  # type: ignore - will validate in service
                response_format=response_format if response_format != "wav" else "mp3",
                speed=speed,
            )
        else:  # azure
            logger.info(
                "tts.synthesize",
                provider="azure",
                voice=voice,
                text_length=len(text),
            )
            return await self.azure_service.synthesize(
                text=text,
                voice=voice,  # type: ignore - will validate in service
                response_format=response_format if response_format != "flac" else "mp3",
                speed=speed,
            )


# Global singleton instance
_unified_tts_service: UnifiedTTSService | None = None


def get_unified_tts_service() -> UnifiedTTSService:
    """Get or create the global unified TTS service instance"""
    global _unified_tts_service
    if _unified_tts_service is None:
        _unified_tts_service = UnifiedTTSService()
    return _unified_tts_service
