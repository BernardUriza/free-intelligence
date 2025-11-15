"""Free Intelligence - STT Provider Abstraction

Provides a unified interface for speech-to-text (STT) services, supporting:
- Azure Whisper (cloud, faster, requires API key)
- Deepgram (cloud, very fast, requires API key)
- Faster-Whisper (local, offline, free but slower)

Philosophy: Provider-agnostic design, same pattern as LLM providers.
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
    FASTER_WHISPER = "faster_whisper"


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
            result = asyncio.run(self._transcribe_async(audio_bytes=audio_bytes, language=language))

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
        """Async call to Azure Whisper API"""
        import aiohttp

        url = f"{self.endpoint}openai/deployments/whisper-1/audio/transcriptions?api-version={self.api_version}"

        headers = {"api-key": self.api_key}

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
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"Azure API error {resp.status}: {error_text}")

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

            # Call Deepgram API
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/webm",
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


class FasterWhisperProvider(STTProvider):
    """Faster-Whisper provider (local, offline)"""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        super().__init__(config)
        self.model_size: str = str(self.config.get("model_size") or "small")
        self.compute_type: str = str(self.config.get("compute_type") or "int8")
        self.device: str = str(self.config.get("device") or "cpu")

        # Check if faster-whisper is available
        try:
            from faster_whisper import WhisperModel

            self.whisper_model_cls = WhisperModel
            self._model_instance = None
        except ImportError:
            raise ImportError(
                "faster-whisper not installed. Install with: pip install faster-whisper"
            )

        self.logger.info(
            "FASTER_WHISPER_PROVIDER_INITIALIZED",
            model_size=self.model_size,
            compute_type=self.compute_type,
            device=self.device,
        )

    def _get_model(self):
        """Get or create WhisperModel singleton"""
        if self._model_instance is None:
            self.logger.info("FASTER_WHISPER_LOADING_MODEL", model_size=self.model_size)
            self._model_instance = self.whisper_model_cls(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model_instance

    def transcribe(
        self, audio_path: Union[str, Path], language: Optional[str] = None
    ) -> STTResponse:
        """Transcribe using faster-whisper"""
        import time

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        start_time = time.time()

        try:
            self.logger.info(
                "FASTER_WHISPER_TRANSCRIPTION_START",
                audio_path=str(audio_path),
                language=language,
            )

            model = self._get_model()

            # Transcribe
            segments_iter, info = model.transcribe(
                str(audio_path),
                language=language,
                vad_filter=True,
            )

            # Collect segments
            segments_list = []
            text_parts = []

            for segment in segments_iter:
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                }
                segments_list.append(segment_dict)
                text_parts.append(segment.text.strip())

            full_text = " ".join(text_parts)
            latency_ms = (time.time() - start_time) * 1000

            self.logger.info(
                "FASTER_WHISPER_TRANSCRIPTION_COMPLETE",
                audio_path=str(audio_path),
                text_length=len(full_text),
                segments_count=len(segments_list),
                duration=info.duration,
                latency_ms=round(latency_ms, 2),
            )

            return STTResponse(
                text=full_text,
                segments=segments_list,
                language=info.language,
                duration=info.duration,
                confidence=0.95,  # Whisper doesn't provide confidence per-file
                provider="faster_whisper",
                latency_ms=latency_ms,
                metadata={"segments_count": len(segments_list)},
            )

        except Exception as e:
            self.logger.error(
                "FASTER_WHISPER_TRANSCRIPTION_FAILED",
                audio_path=str(audio_path),
                error=str(e),
            )
            raise

    def get_provider_name(self) -> str:
        return "faster_whisper"


def get_stt_provider(provider_name: str, config: Optional[dict[str, Any]] = None) -> STTProvider:
    """
    Factory function to get STT provider instance.

    Args:
        provider_name: "azure_whisper", "deepgram", or "faster_whisper"
        config: Provider-specific configuration

    Returns:
        STTProvider instance

    Raises:
        ValueError: If provider not supported
    """
    provider_map = {
        "azure_whisper": AzureWhisperProvider,
        "deepgram": DeepgramProvider,
        "faster_whisper": FasterWhisperProvider,
    }

    provider_class = provider_map.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown STT provider: {provider_name}. " f"Supported: {list(provider_map.keys())}"
        )

    return provider_class(config)
