"""Diarization Service - Speaker identification and text improvement (post-processing only).

This service applies speaker classification and text improvement to already-transcribed segments.
It does NOT transcribe audio - that's TranscriptionService's job.

Input: Pre-transcribed segments (from TranscriptionService or corpus.h5)
Processing: ONLY applies Ollama for:
  - Speaker classification (PACIENTE, MEDICO, DESCONOCIDO)
  - Text improvement (ortografía, gramática)
Output: Same segments with speaker labels and improved text

Card: FI-BACKEND-FEAT-004 (refactored 2025-11-05)
Created: 2025-10-30
Refactored: 2025-11-05 (separated from transcription)
"""

from __future__ import annotations

import time
from datetime import UTC
from typing import Any, Optional

from backend.logger import get_logger
from backend.services.diarization.jobs import create_job, get_job, update_job
from backend.services.diarization.models import (
    DiarizationJob,
    DiarizationResult,
    DiarizationSegment,
)
from backend.services.diarization.ollama import (
    classify_speaker,
    improve_text,
    is_ollama_available,
)

logger = get_logger(__name__)


class DiarizationService:
    """Service layer for speaker identification and text improvement.

    Encapsulates diarization pipeline:
    1. Accept pre-transcribed segments
    2. Classify speaker for each segment using Ollama
    3. Improve text (ortografía, gramática) using Ollama
    4. Merge consecutive segments from same speaker
    5. Return enriched segments

    Does NOT transcribe - that's TranscriptionService's responsibility.
    """

    def __init__(self) -> None:
        """Initialize DiarizationService."""
        logger.info("DiarizationService initialized (post-processing only)")

    def health_check(self) -> dict[str, Any]:
        """Check health of diarization components.

        Returns:
            Dict with status and component health info
        """
        return {
            "status": "healthy" if is_ollama_available() else "degraded",
            "components": {
                "ollama": {
                    "available": is_ollama_available(),
                },
            },
            "note": "DiarizationService requires pre-transcribed segments",
        }

    def diarize_segments(
        self,
        session_id: str,
        segments: list[DiarizationSegment],
        audio_file_path: str,
        audio_file_hash: str,
        duration_sec: float,
        language: str = "es",
    ) -> DiarizationResult:
        """Apply speaker identification and text improvement to transcribed segments.

        Args:
            session_id: Session identifier
            segments: List of pre-transcribed DiarizationSegment objects
            audio_file_path: Path to original audio file
            audio_file_hash: SHA256 hash of audio file
            duration_sec: Total audio duration in seconds
            language: Language code (default: es)

        Returns:
            DiarizationResult with enriched segments
        """
        start_time = time.time()

        logger.info(
            "DIARIZATION_START",
            session_id=session_id,
            segment_count=len(segments),
            duration=duration_sec,
            language=language,
        )

        if not segments:
            logger.warning("DIARIZATION_NO_SEGMENTS", session_id=session_id)
            return DiarizationResult(
                session_id=session_id,
                audio_file_path=str(audio_file_path),
                audio_file_hash=audio_file_hash,
                duration_sec=duration_sec,
                language=language,
                segments=[],
                processing_time_sec=0.0,
                created_at="",
            )

        # Process segments: classify speaker + improve text
        enriched_segments = []
        for i, segment in enumerate(segments):
            # Get context from adjacent segments
            context_before = enriched_segments[-1].text if enriched_segments else ""
            context_after = segments[i + 1].text if i + 1 < len(segments) else ""

            # Step 1: Classify speaker
            speaker = classify_speaker(segment.text, context_before, context_after)

            # Step 2: Improve text
            improved_text = improve_text(segment.text, speaker)

            # Create enriched segment
            enriched_segment = DiarizationSegment(
                start_time=segment.start_time,
                end_time=segment.end_time,
                speaker=speaker,
                text=segment.text,
                improved_text=improved_text,
            )
            enriched_segments.append(enriched_segment)

            logger.info(
                "SEGMENT_DIARIZED",
                segment_index=i,
                speaker=speaker,
                text_len=len(segment.text),
                improved_len=len(improved_text),
            )

        # Step 3: Merge consecutive segments from same speaker
        merged_segments = self._merge_consecutive_segments(enriched_segments)

        # Step 4: Create result
        processing_time = time.time() - start_time
        from datetime import datetime

        result = DiarizationResult(
            session_id=session_id,
            audio_file_path=str(audio_file_path),
            audio_file_hash=audio_file_hash,
            duration_sec=duration_sec,
            language=language,
            segments=merged_segments,
            processing_time_sec=processing_time,
            created_at=datetime.now(UTC).isoformat(),
        )

        logger.info(
            "DIARIZATION_COMPLETE",
            session_id=session_id,
            final_segment_count=len(merged_segments),
            processing_time=processing_time,
        )

        return result

    @staticmethod
    def _merge_consecutive_segments(
        segments: list[DiarizationSegment],
    ) -> list[DiarizationSegment]:
        """Merge consecutive segments from same speaker.

        Args:
            segments: List of segments

        Returns:
            List with consecutive segments from same speaker merged
        """
        if not segments:
            return []

        merged = []
        current = segments[0]

        for segment in segments[1:]:
            if segment.speaker == current.speaker:
                # Merge: combine text and update end time
                current.text = f"{current.text} {segment.text}".strip()
                current.improved_text = (
                    f"{current.improved_text} {segment.improved_text}".strip()
                    if current.improved_text and segment.improved_text
                    else current.improved_text or segment.improved_text
                )
                current.end_time = segment.end_time
            else:
                # Different speaker: save current and start new
                merged.append(current)
                current = segment

        # Add last segment
        merged.append(current)

        logger.info("SEGMENTS_MERGED", original=len(segments), merged=len(merged))
        return merged

    def create_job(self, session_id: str, audio_file_path: str, audio_file_size: int) -> str:
        """Create a diarization job.

        Args:
            session_id: Session identifier
            audio_file_path: Path to audio file
            audio_file_size: File size in bytes

        Returns:
            Job ID (UUID)
        """
        return create_job(session_id, audio_file_path, audio_file_size)

    def get_job(self, job_id: str) -> Optional[DiarizationJob]:
        """Get job status.

        Args:
            job_id: Job identifier

        Returns:
            DiarizationJob or None if not found
        """
        return get_job(job_id)

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress_percent: Optional[int] = None,
        processed_chunks: Optional[int] = None,
        total_chunks: Optional[int] = None,
        error_message: Optional[str] = None,
        result_path: Optional[str] = None,
        result_data: Optional[dict[str, Any]] = None,
    ) -> Optional[DiarizationJob]:
        """Update job status.

        Args:
            job_id: Job identifier
            status: New status
            progress_percent: Progress percentage
            processed_chunks: Chunks processed
            total_chunks: Total chunks
            error_message: Error message if failed
            result_path: Path to result
            result_data: Result data cache

        Returns:
            Updated DiarizationJob or None if not found
        """
        return update_job(
            job_id,
            status=status,
            progress_percent=progress_percent,
            processed_chunks=processed_chunks,
            total_chunks=total_chunks,
            error_message=error_message,
            result_path=result_path,
            result_data=result_data,
        )
