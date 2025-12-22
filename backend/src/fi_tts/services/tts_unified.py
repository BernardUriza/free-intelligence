"""
Unified TTS Service - Multi-provider text-to-speech

Supports Azure Speech Services, OpenAI TTS, and OpenAI Steerable TTS with automatic provider selection.

Provider Selection Strategy:
1. OpenAI Steerable TTS - Natural voices with accent control
   - Best for: Spanish with Mexican accent, multilingual content
   - Voices: alloy, echo, shimmer (steerable subset)
   - Model: gpt-4o-audio-preview with accent control
   - Auto-enabled when text is Spanish and voice is OpenAI

2. OpenAI TTS (standard) - Natural, expressive voices
   - Best for: English content, general use
   - Voices: alloy, nova, shimmer, etc. (11 total)
   - Model: tts-1-hd (faster, no accent control)

3. Azure Speech Services - High-quality neural voices
   - Best for: Native Spanish (Mexico) voices, medical terminology
   - Voices: es-MX-DaliaNeural, es-MX-JorgeNeural, etc. (17 total)
   - Locale: Spanish Mexico (es-MX)

Usage:
    tts = get_unified_tts_service()
    audio = await tts.synthesize(
        text="Hola mundo",
        voice="alloy",              # OpenAI voice
        provider="openai-steerable", # Enable accent control
        accent="Mexican Spanish"    # Accent instruction
    )

Created: 2025-12-08
Updated: 2025-12-09 (Added steerable TTS support)
"""

from __future__ import annotations

import re
from typing import Literal

import structlog
from backend.src.fi_tts.services.tts_openai import get_openai_tts_service
from backend.src.fi_tts.services.tts_openai_steerable import get_steerable_tts_service
from backend.src.fi_tts.services.tts_service import get_tts_service

logger = structlog.get_logger(__name__)

ProviderType = Literal["openai", "openai-steerable", "azure"]
OutputFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]

# Steerable voices (subset of OpenAI voices that support accent control)
STEERABLE_VOICES = {"alloy", "echo", "shimmer"}


class UnifiedTTSService:
    """Unified TTS service supporting multiple providers"""

    def __init__(self):
        self.openai_service = get_openai_tts_service()
        self.steerable_service = get_steerable_tts_service()
        self.azure_service = get_tts_service()

    def _detect_language(self, text: str) -> str:
        """Detect if text is Spanish or English (simple heuristic)"""
        # Count Spanish-specific characters and common words
        spanish_chars = len(re.findall(r"[áéíóúñü¿¡]", text.lower()))
        spanish_words = len(
            re.findall(
                r"\b(el|la|de|que|es|en|y|a|los|se|del|un|por|con|no|una|su|para|al|"
                r"como|más|pero|hola|buenos|días|gracias|por favor)\b",
                text.lower(),
            )
        )

        # If we find Spanish indicators, classify as Spanish
        if spanish_chars > 0 or spanish_words > 2:
            return "es"
        return "en"

    async def synthesize(
        self,
        text: str,
        voice: str = "nova",  # Can be OpenAI or Azure voice
        provider: ProviderType | None = None,  # Auto-detect if None
        accent: str | None = None,  # Accent for steerable TTS
        response_format: OutputFormat = "mp3",
        speed: float = 1.0,
    ) -> bytes:
        """
        Synthesize speech using the specified or auto-detected provider.

        Args:
            text: Text to synthesize (max 4096 characters)
            voice: Voice name (OpenAI: nova, alloy, etc. | Azure: es-MX-DaliaNeural, etc.)
            provider: Force specific provider ("openai", "openai-steerable", "azure"), or None for auto-detect
            accent: Accent instruction for steerable TTS (e.g., "Mexican Spanish", "neutral Spanish")
            response_format: Audio format (mp3, opus, aac, flac, wav, pcm)
            speed: Speech speed (0.25 to 4.0)

        Returns:
            Audio bytes in specified format
        """
        # Auto-detect provider based on voice name and text if not specified
        if provider is None:
            if voice.startswith("es-MX-"):
                # Azure voice explicitly requested
                provider = "azure"
                logger.info("tts.auto_provider", provider="azure", reason="es-MX voice")
            elif voice in STEERABLE_VOICES and self._detect_language(text) == "es":
                # Spanish text + steerable voice = use steerable TTS for accent control
                provider = "openai-steerable"
                if accent is None:
                    accent = "Mexican Spanish"
                logger.info(
                    "tts.auto_provider",
                    provider="openai-steerable",
                    reason="spanish_text_steerable_voice",
                    accent=accent,
                )
            else:
                # Default to standard OpenAI TTS
                provider = "openai"
                logger.info("tts.auto_provider", provider="openai", reason="default")

        # Route to appropriate provider
        if provider == "openai-steerable":
            # Use steerable TTS with accent control
            if accent is None:
                accent = "neutral"  # Default accent
            logger.info(
                "tts.synthesize",
                provider="openai-steerable",
                voice=voice,
                accent=accent,
                text_length=len(text),
            )
            return await self.steerable_service.synthesize(
                text=text,
                voice=voice,  # type: ignore - will validate in service
                accent=accent,
                response_format=response_format if response_format not in {"wav", "pcm"} else "mp3",
                speed=speed,
            )
        elif provider == "openai":
            # Standard OpenAI TTS (no accent control)
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
            # Azure Speech Services
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
