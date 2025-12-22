"""
Text-to-Speech Service - Azure Speech Services TTS

Provides high-quality speech synthesis for demo mode and accessibility features.

Uses Azure Speech Services for Spanish (Mexico) neural voices.

Available Voices (17 total):

Female (9):
- es-MX-DaliaNeural - Female (default, recommended for medical)
- es-MX-BeatrizNeural - Female
- es-MX-CandelaNeural - Female (child voice)
- es-MX-CarlotaNeural - Female
- es-MX-DaliaMultilingualNeural - Female (multilingual, es/en)
- es-MX-LarissaNeural - Female
- es-MX-MarinaNeural - Female
- es-MX-NuriaNeural - Female
- es-MX-RenataNeural - Female

Male (8):
- es-MX-JorgeNeural - Male
- es-MX-CecilioNeural - Male
- es-MX-GerardoNeural - Male
- es-MX-JorgeMultilingualNeural - Male (multilingual, es/en)
- es-MX-LibertoNeural - Male
- es-MX-LucianoNeural - Male
- es-MX-PelayoNeural - Male
- es-MX-YagoNeural - Male

Created: 2025-11-17
Updated: 2025-12-08 (Migrated from OpenAI to Azure Speech Services)
"""

from __future__ import annotations

from typing import Literal

import httpx
import os
import structlog

logger = structlog.get_logger(__name__)

# Azure Speech Services configuration (reuse from STT)
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "westus")

# Azure Speech Services voice names (all available es-MX Neural voices)
VoiceType = Literal[
    "es-MX-DaliaNeural",  # Female (default)
    "es-MX-JorgeNeural",  # Male
    "es-MX-BeatrizNeural",  # Female
    "es-MX-CandelaNeural",  # Female (child)
    "es-MX-CarlotaNeural",  # Female
    "es-MX-CecilioNeural",  # Male
    "es-MX-DaliaMultilingualNeural",  # Female (multilingüe)
    "es-MX-GerardoNeural",  # Male
    "es-MX-JorgeMultilingualNeural",  # Male (multilingüe)
    "es-MX-LarissaNeural",  # Female
    "es-MX-LibertoNeural",  # Male
    "es-MX-LucianoNeural",  # Male
    "es-MX-MarinaNeural",  # Female
    "es-MX-NuriaNeural",  # Female
    "es-MX-PelayoNeural",  # Male
    "es-MX-RenataNeural",  # Female
    "es-MX-YagoNeural",  # Male
]
OutputFormat = Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]
SpeedType = float  # 0.25 to 4.0


class TTSService:
    """Azure Speech Services Text-to-Speech service"""

    def __init__(
        self,
        region: str = AZURE_SPEECH_REGION,
        api_key: str = AZURE_SPEECH_KEY,
    ):
        self.region = region
        self.api_key = api_key

        if not self.api_key:
            logger.warning("AZURE_SPEECH_KEY not configured - TTS will fail")

    async def synthesize(
        self,
        text: str,
        voice: VoiceType = "es-MX-DaliaNeural",
        response_format: OutputFormat = "mp3",
        speed: SpeedType = 1.0,
    ) -> bytes:
        """
        Synthesize speech from text using Azure Speech Services TTS.

        Args:
            text: Text to synthesize (max 4096 characters)
            voice: Azure voice name (es-MX-DaliaNeural = female, default)
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
            raise RuntimeError("Azure Speech Services API key not configured")

        # Use Azure voice name directly
        azure_voice = voice

        # Build SSML for speech synthesis with rate control
        # Rate: speed 1.0 = "medium", 0.5 = "x-slow", 2.0 = "x-fast"
        rate_map = {
            (0.0, 0.5): "x-slow",
            (0.5, 0.75): "slow",
            (0.75, 1.25): "medium",
            (1.25, 1.75): "fast",
            (1.75, 5.0): "x-fast",
        }
        rate = next((v for (low, high), v in rate_map.items() if low <= speed < high), "medium")

        ssml = f"""<speak version='1.0' xml:lang='es-MX'>
            <voice name='{azure_voice}'>
                <prosody rate='{rate}'>
                    {text}
                </prosody>
            </voice>
        </speak>"""

        url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"

        logger.info(
            "tts.synthesize",
            text_length=len(text),
            voice=voice,
            azure_voice=azure_voice,
            format=response_format,
            speed=speed,
            rate=rate,
        )

        # Audio format mapping
        audio_format_map = {
            "mp3": "audio-24khz-48kbitrate-mono-mp3",
            "opus": "ogg-24khz-16bit-mono-opus",
            "wav": "riff-24khz-16bit-mono-pcm",
            "pcm": "raw-24khz-16bit-mono-pcm",
        }
        audio_output_format = audio_format_map.get(
            response_format, "audio-24khz-48kbitrate-mono-mp3"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Ocp-Apim-Subscription-Key": self.api_key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": audio_output_format,
                },
                content=ssml,
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(
                    "tts.error",
                    status=response.status_code,
                    error=error_text,
                )
                raise httpx.HTTPError(
                    f"Azure Speech TTS failed ({response.status_code}): {error_text}"
                )

            audio_bytes = response.content
            logger.info(
                "tts.success",
                audio_size_kb=len(audio_bytes) / 1024,
                format=response_format,
            )

            return audio_bytes


# Global singleton instance
_tts_service: TTSService | None = None


def get_tts_service() -> TTSService:
    """Get or create the global TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
