"""Free Intelligence - Speaker Diarization Provider Abstraction

Provides unified interface for speaker identification (who speaks when):
- Pyannote (local, offline, free)
- AWS Transcribe (cloud, high accuracy)
- Google Speech-to-Text (cloud, multilingual)
- Deepgram (cloud, fast, low cost)

Philosophy: Provider-agnostic design matching LLM/STT patterns.

For medical consultations (doctor + patient), diarization separates voices
to enable speaker-specific SOAP note generation and quality metrics.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Union

from backend.logger import get_logger

logger = get_logger(__name__)


class DiarizationProviderType(Enum):
    """Supported diarization providers"""

    PYANNOTE = "pyannote"
    AWS_TRANSCRIBE = "aws_transcribe"
    GOOGLE_SPEECH = "google_speech"
    DEEPGRAM = "deepgram"


@dataclass
class Speaker:
    """Speaker information"""

    speaker_id: str  # "Speaker 1", "SPEAKER_01", etc.
    name: str | None = None  # "Doctor" or "Patient" (if known)
    confidence: float = 0.0  # 0-1, confidence in assignment


@dataclass
class DiarizationSegment:
    """A segment of speech from one speaker"""

    start_time: float  # Seconds from start
    end_time: float  # Seconds from start
    speaker: Speaker  # Who is speaking
    confidence: float  # 0-1, confidence in speaker assignment
    text: str | None = None  # Transcript (if available)
    improved_text: str | None = None  # GPT-4 enhanced text (grammar, punctuation, medical terms)
    duration: float = 0.0  # end_time - start_time


@dataclass
class DiarizationResponse:
    """Unified response from diarization provider"""

    segments: list[DiarizationSegment]  # Ordered list of speaker segments
    speakers: dict[str, Speaker]  # Map of speaker_id -> Speaker info
    num_speakers: int  # Number of unique speakers detected
    duration: float  # Total audio duration
    confidence: float  # Overall confidence (0-1)
    provider: str  # Provider name
    latency_ms: float | None = None
    metadata: dict[str, Any] | None = None


class DiarizationProvider(ABC):
    """Abstract base class for diarization providers"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def diarize(
        self, audio_path: Union[str, Path], num_speakers: int | None = None
    ) -> DiarizationResponse:
        """
        Identify speakers in audio file.

        Args:
            audio_path: Path to audio file
            num_speakers: Expected number of speakers (optional, can be auto-detected)

        Returns:
            DiarizationResponse with speaker segments and metadata
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider name"""
        pass


class PyannoteProvider(DiarizationProvider):
    """Pyannote - Local, offline speaker diarization"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.model_name: str = str(self.config.get("model") or "pyannote/speaker-diarization-3.1")
        self.device: str = str(self.config.get("device") or "cpu")

        # Check if pyannote is available
        try:
            from pyannote.audio import Pipeline

            self.pipeline_cls = Pipeline
            self._pipeline_instance = None
        except ImportError:
            raise ImportError(
                "pyannote.audio not installed. Install with: pip install pyannote.audio"
            )

        self.logger.info(
            "PYANNOTE_PROVIDER_INITIALIZED",
            model=self.model_name,
            device=self.device,
        )

    def _get_pipeline(self) -> Any:
        """Get or create Pyannote pipeline singleton"""
        if self._pipeline_instance is None:
            import os

            self.logger.info("PYANNOTE_LOADING_MODEL", model=self.model_name)

            # Try to load with HF_TOKEN from environment
            hf_token = os.getenv("HF_TOKEN")
            try:
                self._pipeline_instance = self.pipeline_cls.from_pretrained(
                    self.model_name,
                    use_auth_token=hf_token,
                )
            except Exception as e:
                self.logger.warning(
                    "PYANNOTE_MODEL_LOAD_FAILED",
                    error=str(e),
                    hint="Set HF_TOKEN environment variable or accept model terms at https://hf.co/pyannote/speaker-diarization-3.1",
                )
                raise RuntimeError(f"Failed to load Pyannote model: {e}") from e

            if self.device != "cpu":
                if self._pipeline_instance is not None:
                    self._pipeline_instance = self._pipeline_instance.to(self.device)
        return self._pipeline_instance

    def diarize(
        self, audio_path: Union[str, Path], num_speakers: int | None = None
    ) -> DiarizationResponse:
        """Diarize audio using Pyannote"""
        import time

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        start_time = time.time()

        try:
            self.logger.info(
                "PYANNOTE_DIARIZATION_START",
                audio_path=str(audio_path),
                num_speakers=num_speakers,
            )

            pipeline = self._get_pipeline()

            # Run diarization
            diarization = pipeline(str(audio_path), num_speakers=num_speakers)

            # Parse results
            segments: list[DiarizationSegment] = []
            speaker_dict: dict[str, Speaker] = {}

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                if speaker not in speaker_dict:
                    speaker_dict[speaker] = Speaker(
                        speaker_id=speaker,
                        name=None,
                        confidence=0.95,  # Pyannote default confidence
                    )

                segments.append(
                    DiarizationSegment(
                        start_time=turn.start,
                        end_time=turn.end,
                        speaker=speaker_dict[speaker],
                        confidence=0.95,  # Pyannote doesn't provide per-segment confidence
                        duration=turn.end - turn.start,
                    )
                )

            # Get duration
            duration = max((s.end_time for s in segments), default=0.0)

            latency_ms = (time.time() - start_time) * 1000

            self.logger.info(
                "PYANNOTE_DIARIZATION_COMPLETE",
                audio_path=str(audio_path),
                num_segments=len(segments),
                num_speakers=len(speaker_dict),
                duration=duration,
                latency_ms=round(latency_ms, 2),
            )

            return DiarizationResponse(
                segments=segments,
                speakers=speaker_dict,
                num_speakers=len(speaker_dict),
                duration=duration,
                confidence=0.95,
                provider="pyannote",
                latency_ms=latency_ms,
            )

        except Exception as e:
            self.logger.error(
                "PYANNOTE_DIARIZATION_FAILED",
                audio_path=str(audio_path),
                error=str(e),
            )
            raise RuntimeError(f"Pyannote diarization failed: {e}") from e

    def get_provider_name(self) -> str:
        return "pyannote"


class AWSTranscribeProvider(DiarizationProvider):
    """AWS Transcribe - Cloud speaker diarization"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        import os

        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.s3_bucket = self.config.get("s3_bucket") or os.getenv("AWS_S3_BUCKET")
        self.timeout = int(self.config.get("timeout_seconds") or 300)

        # Check if boto3 is available
        try:
            import boto3

            self.boto3 = boto3
        except ImportError:
            raise ImportError("boto3 not installed. Install with: pip install boto3")

        self.logger.info(
            "AWS_TRANSCRIBE_PROVIDER_INITIALIZED",
            region=self.region,
            bucket=self.s3_bucket,
        )

    def diarize(
        self, audio_path: Union[str, Path], num_speakers: int | None = None
    ) -> DiarizationResponse:
        """Diarize audio using AWS Transcribe"""
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            self.logger.info(
                "AWS_TRANSCRIBE_DIARIZATION_START",
                audio_path=str(audio_path),
                num_speakers=num_speakers,
            )

            # Implementation would upload to S3, call AWS Transcribe, parse results
            # This is a template - full implementation requires S3 setup
            raise NotImplementedError(
                "AWS Transcribe provider requires S3 bucket setup and credentials"
            )

        except NotImplementedError:
            raise
        except Exception as e:
            self.logger.error(
                "AWS_TRANSCRIBE_DIARIZATION_FAILED",
                audio_path=str(audio_path),
                error=str(e),
            )
            raise RuntimeError(f"AWS Transcribe diarization failed: {e}") from e

    def get_provider_name(self) -> str:
        return "aws_transcribe"


class GoogleSpeechProvider(DiarizationProvider):
    """Google Cloud Speech-to-Text - Cloud speaker diarization"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        import os

        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.language_code = str(self.config.get("language_code") or "es-ES")

        # Check if google-cloud-speech is available
        try:
            from google.cloud import speech_v1

            self.speech_client = speech_v1.SpeechClient()
        except ImportError:
            raise ImportError(
                "google-cloud-speech not installed. Install with: pip install google-cloud-speech"
            )

        self.logger.info(
            "GOOGLE_SPEECH_PROVIDER_INITIALIZED",
            language=self.language_code,
        )

    def diarize(
        self, audio_path: Union[str, Path], num_speakers: int | None = None
    ) -> DiarizationResponse:
        """Diarize audio using Google Cloud Speech"""
        raise NotImplementedError(
            "Google Speech provider requires credentials and full implementation"
        )

    def get_provider_name(self) -> str:
        return "google_speech"


class DeepgramProvider(DiarizationProvider):
    """Deepgram - Cloud speaker diarization"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        import os

        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable not set")

        self.model = str(self.config.get("model") or "nova-2")
        self.timeout = int(self.config.get("timeout_seconds") or 30)

        try:
            import requests

            self.requests = requests
        except ImportError:
            raise ImportError("requests not installed. Install with: pip install requests")

        self.logger.info(
            "DEEPGRAM_DIARIZATION_PROVIDER_INITIALIZED",
            model=self.model,
        )

    def diarize(
        self, audio_path: Union[str, Path], num_speakers: int | None = None
    ) -> DiarizationResponse:
        """Diarize audio using Deepgram"""
        import time

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        start_time = time.time()

        try:
            self.logger.info(
                "DEEPGRAM_DIARIZATION_START",
                audio_path=str(audio_path),
                num_speakers=num_speakers,
            )

            # Read audio file
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()

            # Call Deepgram API with diarization enabled
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/webm",
            }

            url = "https://api.deepgram.com/v1/listen"
            params = {
                "model": self.model,
                "diarize": "true",  # Enable speaker diarization
                "language": "es",
            }

            response = self.requests.post(
                url,
                headers=headers,
                params=params,
                data=audio_bytes,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                raise Exception(f"Deepgram API error {response.status_code}: {response.text}")

            api_response = response.json()

            # Parse Deepgram diarization response
            segments: list[DiarizationSegment] = []
            speaker_dict: dict[str, Speaker] = {}

            for result in (
                api_response.get("results", {}).get("channels", [{}])[0].get("alternatives", [])
            ):
                for word_obj in result.get("words", []):
                    speaker_id = str(word_obj.get("speaker", "unknown"))

                    if speaker_id not in speaker_dict:
                        speaker_dict[speaker_id] = Speaker(
                            speaker_id=speaker_id,
                            name=None,
                            confidence=0.95,
                        )

                    segments.append(
                        DiarizationSegment(
                            start_time=word_obj.get("start", 0.0),
                            end_time=word_obj.get("end", 0.0),
                            speaker=speaker_dict[speaker_id],
                            confidence=word_obj.get("confidence", 0.95),
                            text=word_obj.get("punctuated_word", word_obj.get("word", "")),
                            duration=word_obj.get("end", 0.0) - word_obj.get("start", 0.0),
                        )
                    )

            duration = api_response.get("metadata", {}).get("duration", 0.0)
            latency_ms = (time.time() - start_time) * 1000

            self.logger.info(
                "DEEPGRAM_DIARIZATION_COMPLETE",
                audio_path=str(audio_path),
                num_segments=len(segments),
                num_speakers=len(speaker_dict),
                duration=duration,
                latency_ms=round(latency_ms, 2),
            )

            return DiarizationResponse(
                segments=segments,
                speakers=speaker_dict,
                num_speakers=len(speaker_dict),
                duration=duration,
                confidence=0.95,
                provider="deepgram",
                latency_ms=latency_ms,
            )

        except Exception as e:
            self.logger.error(
                "DEEPGRAM_DIARIZATION_FAILED",
                audio_path=str(audio_path),
                error=str(e),
            )
            raise RuntimeError(f"Deepgram diarization failed: {e}") from e

    def get_provider_name(self) -> str:
        return "deepgram"


def get_diarization_provider(
    provider_name: str, config: dict[str, Any] | None = None
) -> DiarizationProvider:
    """
    Factory function to get diarization provider instance.

    Args:
        provider_name: "pyannote", "aws_transcribe", "google_speech", or "deepgram"
        config: Provider-specific configuration

    Returns:
        DiarizationProvider instance

    Raises:
        ValueError: If provider not supported
    """
    provider_map = {
        "pyannote": PyannoteProvider,
        "aws_transcribe": AWSTranscribeProvider,
        "google_speech": GoogleSpeechProvider,
        "deepgram": DeepgramProvider,
        "azure_gpt4": AzureGPT4Provider,
    }

    provider_class = provider_map.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown diarization provider: {provider_name}. Supported: {list(provider_map.keys())}"
        )

    return provider_class(config)


class AzureGPT4Provider(DiarizationProvider):
    """Azure GPT-4 - Text-based diarization using LLM"""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        import os

        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_KEY")
        self.deployment = "gpt-4"
        self.api_version = "2024-02-15-preview"

        if not self.endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
        if not self.api_key:
            raise ValueError("AZURE_OPENAI_KEY environment variable not set")

        self.logger.info("AZURE_GPT4_DIARIZATION_PROVIDER_INITIALIZED")

    def diarize(  # type: ignore[override]  # Text-based provider has different signature than audio-based providers
        self,
        audio_path: Union[str, Path] | None = None,
        transcript: str | None = None,
        num_speakers: int = 2,
        chunks: list[dict[str, Any]] | None = None,
        webspeech_final: list[str] | None = None,
    ) -> DiarizationResponse:
        """Text-based diarization using Azure GPT-4 with TRIPLE VISION timeline inference"""
        import json
        import time

        import requests

        if not transcript:
            raise ValueError("Azure GPT-4 provider requires transcript text")

        start_time = time.time()

        # Build webspeech section (if available)
        webspeech_section = ""
        if webspeech_final:
            webspeech_section = "\n\nWEBSPEECH FINAL (captura instantánea, más completa):\n"
            for i, text in enumerate(webspeech_final):
                webspeech_section += f"[{i}] {text}\n"

        # Build chunks timeline for prompt (if available)
        chunks_timeline = ""
        if chunks:
            chunks_timeline = "\n\nCHUNKS TIMELINE (con timestamps REALES del ASR):\n"
            for chunk in chunks:
                chunk_idx = chunk.get("chunk_idx", chunk.get("idx", "?"))
                ts_start = chunk.get("timestamp_start", 0.0)
                ts_end = chunk.get("timestamp_end", 0.0)
                chunk_text = chunk.get("transcript", "")
                chunks_timeline += (
                    f'Chunk {chunk_idx}: [{ts_start:.1f}s → {ts_end:.1f}s] "{chunk_text[:80]}..."\n'
                )

        # Prompt for diarization with TRIPLE VISION (full text + webspeech + chunks with timestamps)
        prompt = f"""Eres un asistente médico experto en identificar speakers en transcripciones de consultas médicas.

TRIPLE VISION - 3 FUENTES DE TRANSCRIPCIÓN:

1. TRANSCRIPT COMPLETO (texto limpio):
{transcript}
{webspeech_section}
{chunks_timeline}

TASK: Identifica quién dijo qué en la transcripción. En una consulta médica típica hay 2 speakers:
- Doctor/Doctora (hace preguntas médicas, examina, diagnostica)
- Paciente (describe síntomas, responde preguntas)

IMPORTANTE:
- Divide el texto en segmentos naturales (cambios de speaker)
- Asigna cada segmento a "Doctor" o "Paciente"
- USA LOS TIMESTAMPS REALES de los chunks para ubicar cada segmento en el timeline
- Infiere la ubicación temporal comparando el texto del segmento con los chunks
- Para cada segmento, genera DOS versiones del texto:
  * "text": Texto original exacto de la transcripción (sin cambios)
  * "improved_text": Versión mejorada con gramática correcta, puntuación, acentos, capitalización y terminología médica apropiada

OUTPUT FORMAT (JSON):
{{
  "segments": [
    {{
      "speaker": "Doctor",
      "text": "hola maria pasa",
      "improved_text": "Hola María, pasa.",
      "chunk_idx": 0,
      "start": 0.0,
      "end": 13.0
    }},
    {{
      "speaker": "Paciente",
      "text": "...",
      "improved_text": "...",
      "chunk_idx": 1,
      "start": 13.0,
      "end": 26.0
    }}
  ]
}}

REGLAS:
- "text": Mantén el texto EXACTO de la transcripción original (no lo cambies)
- "improved_text": Mejora gramática, puntuación, acentos, capitalización, términos médicos
- "chunk_idx": Índice del chunk donde aparece el segmento (infiere comparando textos)
- "start" y "end": Usa los timestamps del chunk correspondiente
- Si un segmento abarca múltiples chunks, usa el rango completo

Responde SOLO con el JSON, sin explicaciones adicionales."""

        url = f"{self.endpoint}openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "temperature": 0.1,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()

            # Parse GPT-4 response
            gpt_text = result["choices"][0]["message"]["content"]

            # Extract JSON from response (might have markdown code blocks)
            if "```json" in gpt_text:
                json_text = gpt_text.split("```json")[1].split("```")[0].strip()
            elif "```" in gpt_text:
                json_text = gpt_text.split("```")[1].split("```")[0].strip()
            else:
                json_text = gpt_text.strip()

            diarization_data = json.loads(json_text)

            # Convert to DiarizationResponse format
            segments = []
            speakers_dict = {}
            current_time = 0.0

            for seg in diarization_data.get("segments", []):
                speaker_name = seg["speaker"]
                speaker_id = speaker_name.lower()

                if speaker_id not in speakers_dict:
                    speakers_dict[speaker_id] = Speaker(
                        speaker_id=speaker_id, name=speaker_name, confidence=0.95
                    )

                segment = DiarizationSegment(
                    start_time=seg.get("start", current_time),
                    end_time=seg.get("end", current_time + 5.0),
                    speaker=speakers_dict[speaker_id],
                    confidence=0.95,
                    text=seg["text"],
                    improved_text=seg.get("improved_text"),  # GPT-4 enhanced text
                    duration=seg.get("end", current_time + 5.0) - seg.get("start", current_time),
                )
                segments.append(segment)
                current_time = segment.end_time

            latency_ms = (time.time() - start_time) * 1000

            self.logger.info(
                "AZURE_GPT4_DIARIZATION_COMPLETE",
                num_segments=len(segments),
                num_speakers=len(speakers_dict),
                latency_ms=round(latency_ms, 2),
            )

            return DiarizationResponse(
                segments=segments,
                speakers=speakers_dict,
                num_speakers=len(speakers_dict),
                duration=current_time,
                confidence=0.95,
                provider="azure_gpt4",
                latency_ms=latency_ms,
                metadata={"model": result.get("model"), "deployment": self.deployment},
            )

        except Exception as e:
            self.logger.error("AZURE_GPT4_DIARIZATION_FAILED", error=str(e))
            raise

    def get_provider_name(self) -> str:
        return "azure_gpt4"
