"""Free Intelligence - STT Provider Abstraction

Provides a unified interface for speech-to-text (STT) services.
Currently uses Azure OpenAI Whisper (cloud-based, high accuracy).

Philosophy: Provider-agnostic design, same pattern as LLM providers.

History:
- faster-whisper: Removed (CTranslate2 compilation issues with Python 3.14)
- Deepgram: Removed (consolidating to single provider)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

import os
from backend.src.fi_common.logging.logger import get_logger
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

logger = get_logger(__name__)


class STTProviderType(Enum):
    """Supported STT providers"""

    AZURE_WHISPER = "azure_whisper"


class STTResponse:
    """Unified response format from any STT provider"""

    __slots__ = (
        "confidence",
        "duration",
        "language",
        "latency_ms",
        "metadata",
        "provider",
        "segments",
        "text",
    )

    def __init__(
        self,
        *,
        text: str,
        segments: list[dict[str, Any]],
        language: str,
        duration: float,
        confidence: float,
        provider: str,
        latency_ms: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.text = text
        self.segments = segments
        self.language = language
        self.duration = duration
        self.confidence = confidence
        self.provider = provider
        self.latency_ms = latency_ms
        self.metadata = metadata


class STTProvider(ABC):
    """Abstract base class for STT providers"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def transcribe(self, audio_path: str | Path, language: str | None = None) -> STTResponse:
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
    """Azure OpenAI Whisper STT provider

    Transcribes audio using OpenAI's Whisper model deployed on Azure OpenAI Service.
    Supports all languages for transcription and translation to English.

    Environment Variables:
    - AZURE_OPENAI_ENDPOINT: Azure OpenAI resource endpoint
    - AZURE_OPENAI_API_KEY: API key for Azure OpenAI
    - AZURE_OPENAI_WHISPER_DEPLOYMENT: Deployment name (default: "whisper")
    - AZURE_OPENAI_WHISPER_API_VERSION: API version (default: "2024-02-01")

    Limitations:
    - File size limit: 25 MB
    - For larger files, use batch transcription API
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = str(
            self.config.get("deployment") or os.getenv("AZURE_OPENAI_WHISPER_DEPLOYMENT", "whisper")
        )
        self.api_version: str = str(
            self.config.get("api_version")
            or os.getenv("AZURE_OPENAI_WHISPER_API_VERSION", "2024-02-01")
        )

        if not self.endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
        if not self.api_key:
            raise ValueError("AZURE_OPENAI_API_KEY environment variable not set")

        self.timeout: int = int(self.config.get("timeout_seconds") or 30)

        self.logger.info(
            "AZURE_WHISPER_PROVIDER_INITIALIZED",
            endpoint=self.endpoint,
            deployment=self.deployment,
            api_version=self.api_version,
        )

    def transcribe(self, audio_path: str | Path, language: str | None = None) -> STTResponse:
        """Transcribe using Azure Whisper API"""
        import asyncio
        import subprocess
        import tempfile
        import time

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        start_time = time.time()
        converted_file = None  # Track temp file for cleanup

        try:
            self.logger.info(
                "AZURE_WHISPER_TRANSCRIPTION_START",
                audio_path=str(audio_path),
                language=language,
            )

            # Convert WebM to WAV if needed (Azure doesn't decode WebM well)
            if audio_path.suffix.lower() == ".webm":
                converted_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                converted_path = Path(converted_file.name)
                converted_file.close()

                self.logger.info(
                    "CONVERTING_WEBM_TO_WAV",
                    source=str(audio_path),
                    target=str(converted_path),
                )

                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(audio_path),
                        "-ar",
                        "16000",  # 16kHz sample rate (optimal for Whisper)
                        "-ac",
                        "1",  # Mono
                        "-f",
                        "wav",
                        str(converted_path),
                    ],
                    capture_output=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()}")

                audio_bytes = converted_path.read_bytes()
                self.logger.info("WEBM_CONVERTED_TO_WAV", size_bytes=len(audio_bytes))
            else:
                # Read audio file directly
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

        finally:
            # Cleanup temporary WAV file if created
            if converted_file is not None:
                try:
                    Path(converted_file.name).unlink(missing_ok=True)
                except Exception:
                    pass  # Ignore cleanup errors

    async def _transcribe_async(
        self, audio_bytes: bytes, language: str | None = None
    ) -> dict[str, Any]:
        """Async call to Azure Whisper API with exponential backoff retry"""
        import asyncio

        import aiohttp

        # Rate limit: Azure Whisper allows 3 requests per minute
        from backend.utils.rate_limiter import azure_whisper_rate_limiter

        azure_whisper_rate_limiter.wait_if_needed()

        url = f"{self.endpoint}openai/deployments/{self.deployment}/audio/transcriptions?api-version={self.api_version}"

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

        # If we reach here, all retries exhausted without success
        raise Exception(f"Azure API transcription failed after {max_retries + 1} attempts")

    def get_provider_name(self) -> str:
        return "azure_whisper"


def get_stt_provider(provider_name: str = "azure_whisper", config: dict[str, Any] | None = None) -> STTProvider:
    """
    Factory function to get STT provider instance.

    Args:
        provider_name: "azure_whisper" (default and only supported)
        config: Provider-specific configuration

    Returns:
        STTProvider instance

    Raises:
        ValueError: If provider not supported
    """
    provider_name_lower = provider_name.lower()

    # Handle legacy deepgram requests
    if provider_name_lower == "deepgram":
        logger.warning(
            "DEEPGRAM_REMOVED",
            message="Deepgram provider removed. Falling back to azure_whisper.",
        )
        provider_name_lower = "azure_whisper"

    provider_map = {
        "azure_whisper": AzureWhisperProvider,
    }

    provider_class = provider_map.get(provider_name_lower)
    if not provider_class:
        raise ValueError(
            f"Unknown STT provider: {provider_name}. Supported: {list(provider_map.keys())}"
        )

    return provider_class(config)
