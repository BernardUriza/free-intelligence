"""Azure GPT-4 text-based diarization provider.

LLM-powered diarization that analyzes transcripts rather than audio.
Uses Azure OpenAI GPT-4 with optional preset support for prompt engineering.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor)
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

import requests

from backend.config.secrets import get_secret
from backend.providers.diarization.base import TextBasedDiarizationProvider
from backend.providers.diarization.models import (
    DiarizationResponse,
    DiarizationSegment,
    Speaker,
)

if TYPE_CHECKING:
    from backend.schemas.llm.interfaces.ipreset_loader import IPresetLoader


class AzureGPT4Provider(TextBasedDiarizationProvider):
    """Azure GPT-4 - Text-based diarization using LLM.

    Analyzes transcript text to identify speaker turns.
    Supports preset-based prompt configuration via IPresetLoader.
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        preset_loader: IPresetLoader | None = None,
    ) -> None:
        """Initialize Azure GPT-4 diarization provider.

        Args:
            config: Provider configuration dict
            preset_loader: IPresetLoader instance for preset-based prompts.
                          If None, uses legacy hardcoded prompt.
        """
        super().__init__(config)

        self.endpoint = get_secret("AZURE_OPENAI_ENDPOINT")
        self.api_key = get_secret("AZURE_OPENAI_KEY")
        self.deployment = "gpt-4"
        self.api_version = "2024-02-15-preview"

        if not self.endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
        if not self.api_key:
            raise ValueError("AZURE_OPENAI_KEY environment variable not set")

        # Load diarization preset (optional)
        self.preset = None
        if preset_loader is not None:
            try:
                self.preset = preset_loader.load_preset("diarization_analyst")
                self.logger.info(
                    "DIARIZATION_PRESET_LOADED",
                    preset_id=self.preset.preset_id,
                    version=self.preset.version,
                    temperature=self.preset.temperature,
                )
            except Exception as e:
                self.logger.critical(
                    "DIARIZATION_PRESET_LOAD_FAILED_FATAL",
                    error=str(e),
                    message="Cannot initialize AzureGPT4Provider - preset loading failed",
                )
                raise ValueError(
                    f"AzureGPT4Provider preset loading failed: {e}. "
                    "Fix diarization_analyst preset or pass preset_loader=None for legacy mode."
                ) from e
        else:
            self.logger.debug(
                "AZURE_GPT4_LEGACY_MODE",
                hint="No preset_loader - using hardcoded prompt",
            )

        self.logger.info("AZURE_GPT4_DIARIZATION_PROVIDER_INITIALIZED")

    def diarize_text(
        self,
        transcript: str,
        num_speakers: int = 2,
        chunks: list[dict[str, Any]] | None = None,
        webspeech_final: list[str] | None = None,
    ) -> DiarizationResponse:
        """Text-based diarization using Azure GPT-4."""
        if not transcript:
            raise ValueError("Azure GPT-4 provider requires transcript text")

        start_time = time.time()

        # Build context sections
        webspeech_section = self._build_webspeech_section(webspeech_final)
        chunks_timeline = self._build_chunks_timeline(chunks)

        # Build prompt and call API
        messages, temperature, max_tokens = self._build_prompt(
            transcript, webspeech_section, chunks_timeline
        )

        url = (
            f"{self.endpoint}openai/deployments/{self.deployment}/"
            f"chat/completions?api-version={self.api_version}"
        )
        headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()

            # Parse GPT-4 response
            gpt_text = result["choices"][0]["message"]["content"]
            diarization_data = self._parse_gpt_response(gpt_text)

            # Convert to DiarizationResponse format
            segments, speakers_dict, final_time = self._build_response_data(
                diarization_data
            )

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
                duration=final_time,
                confidence=0.95,
                provider="azure_gpt4",
                latency_ms=latency_ms,
                metadata={"model": result.get("model"), "deployment": self.deployment},
            )

        except Exception as e:
            self.logger.exception(
                "AZURE_GPT4_DIARIZATION_FAILED",
                extra={"error": str(e)},
            )
            raise

    def _build_webspeech_section(self, webspeech_final: list[str] | None) -> str:
        """Build webspeech section for prompt."""
        if not webspeech_final:
            return ""

        section = "\n\nWEBSPEECH FINAL (captura instantanea, mas completa):\n"
        for i, text in enumerate(webspeech_final):
            section += f"[{i}] {text}\n"
        return section

    def _build_chunks_timeline(self, chunks: list[dict[str, Any]] | None) -> str:
        """Build chunks timeline for prompt."""
        if not chunks:
            return ""

        timeline = "\n\nCHUNKS TIMELINE (con timestamps REALES del ASR):\n"
        for chunk in chunks:
            chunk_idx = chunk.get("chunk_idx", chunk.get("idx", "?"))
            ts_start = chunk.get("timestamp_start", 0.0)
            ts_end = chunk.get("timestamp_end", 0.0)
            chunk_text = chunk.get("transcript", "")
            timeline += (
                f'Chunk {chunk_idx}: [{ts_start:.1f}s -> {ts_end:.1f}s] '
                f'"{chunk_text[:80]}..."\n'
            )
        return timeline

    def _build_prompt(
        self,
        transcript: str,
        webspeech_section: str,
        chunks_timeline: str,
    ) -> tuple[list[dict[str, str]], float, int]:
        """Build prompt messages and parameters."""
        if self.preset:
            return self._build_preset_prompt(
                transcript, webspeech_section, chunks_timeline
            )
        return self._build_legacy_prompt(
            transcript, webspeech_section, chunks_timeline
        )

    def _build_preset_prompt(
        self,
        transcript: str,
        webspeech_section: str,
        chunks_timeline: str,
    ) -> tuple[list[dict[str, str]], float, int]:
        """Build prompt using preset configuration."""
        assert self.preset is not None  # Guarded by _build_prompt
        system_prompt = self.preset.system_prompt
        user_prompt = f"""TRIPLE VISION - 3 FUENTES DE TRANSCRIPCION:

1. TRANSCRIPT COMPLETO (texto limpio):
{transcript}
{webspeech_section}
{chunks_timeline}

TASK ADICIONAL:
- USA LOS TIMESTAMPS REALES de los chunks para ubicar cada segmento en el timeline
- Infiere la ubicacion temporal comparando el texto del segmento con los chunks
- Para cada segmento, genera DOS versiones del texto:
  * "text": Texto original exacto de la transcripcion (sin cambios)
  * "improved_text": Version mejorada con gramatica correcta, puntuacion, acentos,
    capitalizacion y terminologia medica apropiada

OUTPUT FORMAT (JSON):
{{
  "segments": [
    {{
      "speaker": "DOCTOR",
      "text": "hola maria pasa",
      "improved_text": "Hola Maria, pasa.",
      "chunk_idx": 0,
      "start": 0.0,
      "end": 13.0,
      "confidence": 0.95,
      "reasoning": "Greeting + professional tone"
    }}
  ]
}}

REGLAS:
- "speaker": DOCTOR | PATIENT | OTHER (usa mayusculas)
- "text": Manten el texto EXACTO de la transcripcion original
- "improved_text": Mejora gramatica, puntuacion, acentos, capitalizacion, terminos medicos
- "chunk_idx": Indice del chunk donde aparece el segmento
- "start" y "end": Usa los timestamps del chunk correspondiente
- "confidence": Score 0.0-1.0
- "reasoning": Breve explicacion de clasificacion

Responde SOLO con el JSON, sin explicaciones adicionales."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return messages, self.preset.temperature, self.preset.max_tokens

    def _build_legacy_prompt(
        self,
        transcript: str,
        webspeech_section: str,
        chunks_timeline: str,
    ) -> tuple[list[dict[str, str]], float, int]:
        """Build legacy hardcoded prompt."""
        prompt = f"""Eres un asistente medico experto en identificar speakers en
transcripciones de consultas medicas.

TRIPLE VISION - 3 FUENTES DE TRANSCRIPCION:

1. TRANSCRIPT COMPLETO (texto limpio):
{transcript}
{webspeech_section}
{chunks_timeline}

TASK: Identifica quien dijo que en la transcripcion. En una consulta medica tipica hay 2 speakers:
- Doctor/Doctora (hace preguntas medicas, examina, diagnostica)
- Paciente (describe sintomas, responde preguntas)

OUTPUT FORMAT (JSON):
{{
  "segments": [
    {{
      "speaker": "Doctor",
      "text": "hola maria pasa",
      "improved_text": "Hola Maria, pasa.",
      "chunk_idx": 0,
      "start": 0.0,
      "end": 13.0
    }}
  ]
}}

Responde SOLO con el JSON, sin explicaciones adicionales."""

        messages = [{"role": "user", "content": prompt}]
        return messages, 0.1, 4000

    def _parse_gpt_response(self, gpt_text: str) -> dict[str, Any]:
        """Parse GPT-4 JSON response."""
        # Extract JSON from response (might have markdown code blocks)
        if "```json" in gpt_text:
            json_text = gpt_text.split("```json")[1].split("```")[0].strip()
        elif "```" in gpt_text:
            json_text = gpt_text.split("```")[1].split("```")[0].strip()
        else:
            json_text = gpt_text.strip()

        return json.loads(json_text)

    def _build_response_data(
        self,
        diarization_data: dict[str, Any],
    ) -> tuple[list[DiarizationSegment], dict[str, Speaker], float]:
        """Build response objects from parsed data."""
        segments: list[DiarizationSegment] = []
        speakers_dict: dict[str, Speaker] = {}
        current_time = 0.0

        for seg in diarization_data.get("segments", []):
            speaker_name = seg["speaker"]
            speaker_id = speaker_name.lower()

            if speaker_id not in speakers_dict:
                speakers_dict[speaker_id] = Speaker(
                    speaker_id=speaker_id,
                    name=speaker_name,
                    confidence=0.95,
                )

            segment = DiarizationSegment(
                start_time=seg.get("start", current_time),
                end_time=seg.get("end", current_time + 5.0),
                speaker=speakers_dict[speaker_id],
                confidence=0.95,
                text=seg["text"],
                improved_text=seg.get("improved_text"),
                duration=seg.get("end", current_time + 5.0) - seg.get("start", current_time),
            )
            segments.append(segment)
            current_time = segment.end_time

        return segments, speakers_dict, current_time

    def get_provider_name(self) -> str:
        return "azure_gpt4"
