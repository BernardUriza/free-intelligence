"""Deepgram speaker diarization provider.

Cloud-based, fast speaker diarization via Deepgram API.
Requires DEEPGRAM_API_KEY environment variable.

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


class DeepgramProvider(DiarizationProvider):
    """Deepgram - Cloud speaker diarization."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)

        self.api_key = get_secret("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY environment variable not set")

        self.model = str(self.config.get("model") or "nova-2")
        self.timeout = int(self.config.get("timeout_seconds") or 30)

        try:
            import requests

            self._requests = requests
        except ImportError:
            raise ImportError(
                "requests not installed. Install with: pip install requests"
            ) from None

        self.logger.info(
            "DEEPGRAM_DIARIZATION_PROVIDER_INITIALIZED",
            model=self.model,
        )

    def diarize(
        self,
        audio_path: str | Path,
        num_speakers: int | None = None,
    ) -> DiarizationResponse:
        """Diarize audio using Deepgram."""
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
            params: dict[str, Any] = {
                "model": self.model,
                "diarize": "true",
                "language": "es",
            }

            response = self._requests.post(
                url,
                headers=headers,
                params=params,
                data=audio_bytes,
                timeout=self.timeout,
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Deepgram API error {response.status_code}: {response.text}"
                )

            api_response = response.json()

            # Parse Deepgram diarization response
            segments: list[DiarizationSegment] = []
            speaker_dict: dict[str, Speaker] = {}

            for result in (
                api_response.get("results", {})
                .get("channels", [{}])[0]
                .get("alternatives", [])
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
                            text=word_obj.get(
                                "punctuated_word", word_obj.get("word", "")
                            ),
                            duration=word_obj.get("end", 0.0)
                            - word_obj.get("start", 0.0),
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
            self.logger.exception(
                "DEEPGRAM_DIARIZATION_FAILED",
                extra={"audio_path": str(audio_path), "error": str(e)},
            )
            raise RuntimeError(f"Deepgram diarization failed: {e}") from e

    def get_provider_name(self) -> str:
        return "deepgram"
