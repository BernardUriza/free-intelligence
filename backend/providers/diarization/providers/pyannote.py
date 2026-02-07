"""Pyannote speaker diarization provider.

Local, offline speaker diarization using Pyannote.
Requires HuggingFace token for model access.

Author: Bernard Uriza Orozco
Created: 2026-02-03 (SOLID refactor)
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from backend.config.secrets import get_secret
from backend.providers.diarization.base import DiarizationProvider
from backend.providers.diarization.models import (
    DiarizationResponse,
    DiarizationSegment,
    Speaker,
)


class PyannoteProvider(DiarizationProvider):
    """Pyannote - Local, offline speaker diarization."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self.model_name: str = str(
            self.config.get("model") or "pyannote/speaker-diarization-3.1"
        )
        self.device: str = str(self.config.get("device") or "cpu")

        # Lazy-load pipeline
        try:
            from pyannote.audio import Pipeline

            self._pipeline_cls = Pipeline
            self._pipeline_instance: Any = None
        except ImportError:
            raise ImportError(
                "pyannote.audio not installed. Install with: pip install pyannote.audio"
            ) from None

        self.logger.info(
            "PYANNOTE_PROVIDER_INITIALIZED",
            model=self.model_name,
            device=self.device,
        )

    def _get_pipeline(self) -> Any:
        """Get or create Pyannote pipeline singleton."""
        if self._pipeline_instance is None:
            self.logger.info("PYANNOTE_LOADING_MODEL", model=self.model_name)

            hf_token = get_secret("HF_TOKEN")
            try:
                self._pipeline_instance = self._pipeline_cls.from_pretrained(
                    self.model_name,
                    use_auth_token=hf_token,
                )
            except Exception as e:
                self.logger.warning(
                    "PYANNOTE_MODEL_LOAD_FAILED",
                    error=str(e),
                    hint="Set HF_TOKEN or accept model terms at https://hf.co/pyannote/speaker-diarization-3.1",
                )
                raise RuntimeError(f"Failed to load Pyannote model: {e}") from e

            if self.device != "cpu" and self._pipeline_instance is not None:
                self._pipeline_instance = self._pipeline_instance.to(self.device)

        return self._pipeline_instance

    def diarize(
        self,
        audio_path: str | Path,
        num_speakers: int | None = None,
    ) -> DiarizationResponse:
        """Diarize audio using Pyannote."""
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
            diarization = pipeline(str(audio_path), num_speakers=num_speakers)

            # Parse results
            segments: list[DiarizationSegment] = []
            speaker_dict: dict[str, Speaker] = {}

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                if speaker not in speaker_dict:
                    speaker_dict[speaker] = Speaker(
                        speaker_id=speaker,
                        name=None,
                        confidence=0.95,
                    )

                segments.append(
                    DiarizationSegment(
                        start_time=turn.start,
                        end_time=turn.end,
                        speaker=speaker_dict[speaker],
                        confidence=0.95,
                        duration=turn.end - turn.start,
                    )
                )

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
            self.logger.exception(
                "PYANNOTE_DIARIZATION_FAILED",
                extra={"audio_path": str(audio_path), "error": str(e)},
            )
            raise RuntimeError(f"Pyannote diarization failed: {e}") from e

    def get_provider_name(self) -> str:
        return "pyannote"
