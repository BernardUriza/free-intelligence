"""Deepgram Speech-to-Text Service.

Replaces local Whisper with cloud-based Deepgram API for:
- Fast, accurate transcription
- Language detection
- Confidence scores
- No GPU/model management needed

Usage:
    service = DeepgramService(api_key="...")
    result = await service.transcribe(audio_bytes, language="es")
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

import aiohttp
from pydantic import BaseModel, Field

from backend.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TranscriptionResult:
    """Deepgram transcription result."""

    transcript: str
    confidence: float
    language: str
    duration: float
    is_final: bool


class DeepgramTranscript(BaseModel):
    """Deepgram API response transcript."""

    transcript: str = Field(default="", description="Transcribed text")
    confidence: float = Field(default=0.0, description="Confidence score 0-1")
    words: list[dict] = Field(default_factory=list, description="Word-level details")


class DeepgramResult(BaseModel):
    """Deepgram API response."""

    result: dict = Field(default_factory=dict, description="Result metadata")
    results: dict = Field(default_factory=dict, description="Recognition results")


class DeepgramService:
    """Deepgram speech-to-text service."""

    BASE_URL = "https://api.deepgram.com/v1"

    def __init__(self, api_key: str):
        """Initialize Deepgram service.

        Args:
            api_key: Deepgram API key from environment
        """
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable not set")

        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.session:
            await self.session.close()

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "es",
        model: str = "nova-2",
    ) -> TranscriptionResult:
        """Transcribe audio using Deepgram.

        Args:
            audio_bytes: Raw audio data (WAV, WebM, MP3, etc.)
            language: Language code (es, en, fr, etc.)
            model: Deepgram model (nova-2 is fastest/best)

        Returns:
            TranscriptionResult with transcript and metadata

        Raises:
            ValueError: If audio is empty
            aiohttp.ClientError: If API request fails
        """
        if not audio_bytes or len(audio_bytes) == 0:
            raise ValueError("Audio data cannot be empty")

        if not self.session:
            self.session = aiohttp.ClientSession()

        audio_hash = hashlib.sha256(audio_bytes).hexdigest()[:16]

        # Deepgram API endpoint with parameters
        url = f"{self.BASE_URL}/listen"
        params = {
            "model": model,
            "language": language,
            "detect_language": "false",  # Must be string, not bool
            "punctuate": "true",
            "diarize": "false",  # Can enable for speaker separation if needed
            "smart_format": "true",
            "filler_words": "false",
        }

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/wav",  # Deepgram auto-detects, but hint WAV
        }

        try:
            logger.info(
                "DEEPGRAM_REQUEST_STARTED",
                audio_hash=audio_hash,
                audio_size=len(audio_bytes),
                language=language,
                model=model,
            )

            async with self.session.post(
                url,
                params=params,
                headers=headers,
                data=audio_bytes,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        "DEEPGRAM_API_ERROR",
                        status=response.status,
                        error=error_text,
                        audio_hash=audio_hash,
                    )
                    raise ValueError(f"Deepgram API error: {response.status} - {error_text}")

                response_data = await response.json()

                # Extract transcript from Deepgram response
                # Structure: {results: {channels: [{alternatives: [{transcript, confidence}]}]}}
                transcript = ""
                confidence = 0.0
                detected_language = language

                try:
                    channels = response_data.get("results", {}).get("channels", [])
                    if channels:
                        alternatives = channels[0].get("alternatives", [])
                        if alternatives:
                            transcript = alternatives[0].get("transcript", "")
                            confidence = alternatives[0].get("confidence", 0.0)

                    # Get metadata if available
                    metadata = response_data.get("metadata", {})
                    duration = metadata.get("duration", 0.0)
                except (KeyError, IndexError, TypeError) as e:
                    logger.warning(
                        "DEEPGRAM_RESPONSE_PARSE_ERROR",
                        error=str(e),
                        audio_hash=audio_hash,
                    )
                    duration = 0.0

                logger.info(
                    "DEEPGRAM_TRANSCRIPTION_SUCCESS",
                    audio_hash=audio_hash,
                    transcript_length=len(transcript),
                    confidence=confidence,
                    duration=duration,
                    language=detected_language,
                )

                return TranscriptionResult(
                    transcript=transcript,
                    confidence=confidence,
                    language=detected_language,
                    duration=duration,
                    is_final=True,
                )

        except aiohttp.ClientError as e:
            logger.error(
                "DEEPGRAM_REQUEST_FAILED",
                error=str(e),
                audio_hash=audio_hash,
            )
            raise ValueError(f"Failed to transcribe with Deepgram: {e}") from e

    async def get_usage(self) -> dict:
        """Get API usage statistics.

        Returns:
            dict with requests_count, balance, etc.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.BASE_URL}/usage"
        headers = {"Authorization": f"Token {self.api_key}"}

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(
                        "DEEPGRAM_USAGE_FETCH_FAILED",
                        status=response.status,
                    )
                    return {}
        except Exception as e:
            logger.error("DEEPGRAM_USAGE_ERROR", error=str(e))
            return {}
