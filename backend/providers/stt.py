"""Free Intelligence - STT Provider Abstraction

Provides a unified interface for speech-to-text (STT) services, supporting:
- Azure Whisper (cloud, faster, requires API key)
- Deepgram (cloud, very fast, requires API key)

Philosophy: Provider-agnostic design, same pattern as LLM providers.
Note: faster-whisper removed (CTranslate2 compilation issues with Python 3.14)
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from dotenv import load_dotenv

from backend.logger import get_logger

load_dotenv()

logger = get_logger(__name__)


class STTProviderType(Enum):
    """Supported STT providers"""

    AZURE_WHISPER = "azure_whisper"
    DEEPGRAM = "deepgram"


@dataclass
class STTResponse:
    """Unified response format from any STT provider"""

    text: str  # Full transcription
    segments: list[dict[str, Any]]  # [{start, end, text}, ...]
    language: str  # Detected language (es, en, etc.)
    duration: float  # Audio duration in seconds
    confidence: float  # Overall confidence (0-1)
    provider: str  # Provider name
    latency_ms: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None


class STTProvider(ABC):
    """Abstract base class for STT providers"""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self.config: dict[str, Any] = config or {}
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def transcribe(
        self, audio_path: Union[str, Path], language: Optional[str] = None
    ) -> STTResponse:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file
            language: Optional language code (es, en, etc.)

        Returns:
            STTResponse with text, segments, language, etc.
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name"""
        pass


class AzureWhisperProvider(STTProvider):
    """Azure Whisper STT provider (cloud-based, faster)"""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_KEY")
        self.api_version: str = str(self.config.get("api_version") or "2024-02-15-preview")

        if not self.endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
        if not self.api_key:
            raise ValueError("AZURE_OPENAI_KEY environment variable not set")

        self.timeout: int = int(self.config.get("timeout_seconds") or 30)

        self.logger.info(
            "AZURE_WHISPER_PROVIDER_INITIALIZED",
            endpoint=self.endpoint,
        )

    def transcribe(
        self, audio_path: Union[str, Path], language: Optional[str] = None
    ) -> STTResponse:
        """Transcribe using Azure Whisper API"""
        import asyncio
        import time

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        start_time = time.time()

        try:
            self.logger.info(
                "AZURE_WHISPER_TRANSCRIPTION_START",
                audio_path=str(audio_path),
                language=language,
            )

            # Read audio file
            audio_bytes = audio_path.read_bytes()

            # Call Azure API asynchronously
            # Use get_event_loop() instead of asyncio.run() to avoid nested loop error
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We're already in an async context, run in thread pool
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._transcribe_async(audio_bytes=audio_bytes, language=language),
                    )
                    result = future.result()
            else:
                # No event loop running, safe to use asyncio.run()
                result = asyncio.run(
                    self._transcribe_async(audio_bytes=audio_bytes, language=language)
                )

            latency_ms = (time.time() - start_time) * 1000

            self.logger.info(
                "AZURE_WHISPER_TRANSCRIPTION_COMPLETE",
                audio_path=str(audio_path),
                text_length=len(result["text"]),
                latency_ms=round(latency_ms, 2),
            )

            return STTResponse(
                text=result["text"],
                segments=result["segments"],
                language=result["language"],
                duration=result["duration"],
                confidence=result["confidence"],
                provider="azure_whisper",
                latency_ms=latency_ms,
                metadata={"endpoint": self.endpoint},
            )

        except Exception as e:
            self.logger.error(
                "AZURE_WHISPER_TRANSCRIPTION_FAILED",
                audio_path=str(audio_path),
                error=str(e),
            )
            raise

    async def _transcribe_async(
        self, audio_bytes: bytes, language: Optional[str] = None
    ) -> dict[str, Any]:
        """Async call to Azure Whisper API with exponential backoff retry"""
        import asyncio

        import aiohttp

        # Rate limit: Azure Whisper allows 3 requests per minute
        from backend.utils.rate_limiter import azure_whisper_rate_limiter

        azure_whisper_rate_limiter.wait_if_needed()

        url = f"{self.endpoint}openai/deployments/whisper/audio/transcriptions?api-version={self.api_version}"

        headers = {"api-key": self.api_key}

        # Retry configuration for rate limiting
        max_retries = 3
        base_delay = 15  # Azure asks for 15s retry delay

        for attempt in range(max_retries + 1):
            # Use form data for file upload
            data = aiohttp.FormData()
            data.add_field("file", audio_bytes, filename="audio.webm", content_type="audio/webm")
            data.add_field("model", "whisper-1")
            if language:
                data.add_field("language", language)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    if resp.status == 200:
                        api_response = await resp.json()

                        # Parse response
                        text = api_response.get("text", "")
                        detected_language = api_response.get("language", language or "unknown")

                        # Create segments from text (no timing info from Azure)
                        segments = [
                            {
                                "start": 0.0,
                                "end": 0.0,
                                "text": text,
                            }
                        ]

                        return {
                            "text": text,
                            "segments": segments,
                            "language": detected_language,
                            "duration": 0.0,  # Azure doesn't return duration
                            "confidence": 0.9,  # Default confidence
                        }

                    elif resp.status == 429:  # Rate limit
                        error_text = await resp.text()
                        retry_delay = base_delay * (
                            2**attempt
                        )  # Exponential backoff: 15s, 30s, 60s

                        if attempt < max_retries:
                            self.logger.warning(
                                "AZURE_RATE_LIMIT_HIT",
                                attempt=attempt + 1,
                                max_retries=max_retries,
                                retry_after_seconds=retry_delay,
                                error=error_text,
                            )
                            await asyncio.sleep(retry_delay)
                            continue  # Retry
                        else:
                            self.logger.error(
                                "AZURE_RATE_LIMIT_EXHAUSTED",
                                attempts=max_retries + 1,
                                error=error_text,
                            )
                            raise Exception(
                                f"Azure API rate limit exceeded after {max_retries + 1} attempts: {error_text}"
                            )

                    else:
                        error_text = await resp.text()
                        raise Exception(f"Azure API error {resp.status}: {error_text}")

    def get_provider_name(self) -> str:
        return "azure_whisper"


class DeepgramProvider(STTProvider):
    """Deepgram STT provider (cloud-based, very fast)"""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self.api_key = os.getenv("DEEPGRAM_API_KEY")

        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable not set")

        self.timeout: int = int(self.config.get("timeout_seconds") or 30)

        self.logger.info("DEEPGRAM_PROVIDER_INITIALIZED")

    def transcribe(
        self, audio_path: Union[str, Path], language: Optional[str] = None
    ) -> STTResponse:
        """Transcribe using Deepgram API"""
        import time

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        start_time = time.time()

        try:
            import requests

            self.logger.info(
                "DEEPGRAM_TRANSCRIPTION_START",
                audio_path=str(audio_path),
                language=language,
            )

            # Read audio
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            # Detect MIME type from file extension
            extension = audio_path.suffix.lower()
            mime_types = {
                ".mp3": "audio/mpeg",
                ".webm": "audio/webm",
                ".wav": "audio/wav",
                ".m4a": "audio/mp4",
                ".ogg": "audio/ogg",
                ".flac": "audio/flac",
            }
            content_type = mime_types.get(extension, "audio/webm")

            # Call Deepgram API
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": content_type,
            }

            url = "https://api.deepgram.com/v1/listen"
            params = {
                "model": "nova-2",
                "language": language or "es",
            }

            response = requests.post(
                url,
                headers=headers,
                params=params,
                data=audio_bytes,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                raise Exception(f"Deepgram API error {response.status_code}: {response.text}")

            api_response = response.json()

            # Log raw response for debugging
            self.logger.debug(
                "DEEPGRAM_RAW_RESPONSE",
                response_keys=list(api_response.keys()),
                results=api_response.get("results", {}),
            )

            # Parse Deepgram response
            transcript = (
                api_response.get("results", {})
                .get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("transcript", "")
            )
            duration = api_response.get("metadata", {}).get("duration", 0.0)

            # Extract segments
            segments = []
            for alt in (
                api_response.get("results", {}).get("channels", [{}])[0].get("alternatives", [])
            ):
                for word_obj in alt.get("words", []):
                    segments.append(
                        {
                            "start": word_obj.get("start", 0.0),
                            "end": word_obj.get("end", 0.0),
                            "text": word_obj.get("punctuated_word", word_obj.get("word", "")),
                        }
                    )

            # Confidence from Deepgram
            confidence = (
                api_response.get("results", {})
                .get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("confidence", 0.9)
            )

            latency_ms = (time.time() - start_time) * 1000

            self.logger.info(
                "DEEPGRAM_TRANSCRIPTION_COMPLETE",
                audio_path=str(audio_path),
                text_length=len(transcript),
                duration=duration,
                latency_ms=round(latency_ms, 2),
            )

            return STTResponse(
                text=transcript,
                segments=segments,
                language=language or "es",
                duration=duration,
                confidence=confidence,
                provider="deepgram",
                latency_ms=latency_ms,
            )

        except Exception as e:
            self.logger.error(
                "DEEPGRAM_TRANSCRIPTION_FAILED",
                audio_path=str(audio_path),
                error=str(e),
            )
            raise

    def get_provider_name(self) -> str:
        return "deepgram"


def get_stt_provider(provider_name: str, config: Optional[dict[str, Any]] = None) -> STTProvider:
    """
    Factory function to get STT provider instance.

    Args:
        provider_name: "azure_whisper" or "deepgram"
        config: Provider-specific configuration

    Returns:
        STTProvider instance

    Raises:
        ValueError: If provider not supported
    """
    provider_map = {
        "azure_whisper": AzureWhisperProvider,
        "deepgram": DeepgramProvider,
    }

    provider_class = provider_map.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown STT provider: {provider_name}. " f"Supported: {list(provider_map.keys())}"
        )

    return provider_class(config)
