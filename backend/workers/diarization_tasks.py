"""Celery tasks for diarization (speaker separation + text improvement).

Tasks:
- diarize_session_task: Process session with provider-agnostic diarization (Triple Vision)

Architecture:
  PUBLIC/INTERNAL → dispatch task → WORKER (this file) → DiarizationProvider

Diarization Strategy:
  1. Use TRIPLE VISION: full_transcription + chunks + webspeech_final
  2. If using LLM provider (Ollama/Claude): Intelligent segmentation via LLM
  3. If using audio provider (Pyannote/Deepgram): Direct audio diarization
  4. Store speaker segments with timestamps and confidence

Author: Bernard Uriza Orozco
Created: 2025-11-14
Updated: 2025-11-15 (Made provider-agnostic, added audio provider option)
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from backend.logger import get_logger
from backend.models import SessionStatus
from backend.models.task_type import TaskStatus, TaskType
from backend.policy.policy_loader import get_policy_loader
from backend.providers.diarization import get_diarization_provider
from backend.repositories.session_repository import SessionRepository
from backend.services.diarization.diarization_service import DiarizationService
from backend.storage.task_repository import (
    ensure_task_exists,
    get_task_chunks,
    get_task_metadata,
    save_diarization_segments,
    update_task_metadata,
)
from backend.workers.celery_app import celery_app

logger = get_logger(__name__)

# Initialize repositories
session_repo = SessionRepository(
    "/Users/bernardurizaorozco/Documents/free-intelligence/storage/corpus.h5"
)


@celery_app.task(name="diarize_session", bind=True, max_retries=3)
def diarize_session_task(
    self, session_id: str, diarization_provider: str | None = None
) -> dict[str, Any]:
    """Diarize all transcribed chunks from a session using Triple Vision.

    Uses provider-agnostic diarization:
    - TRIPLE VISION: full_transcription + chunks + webspeech_final
    - LLM provider (Ollama/Claude): Intelligent segmentation
    - Audio provider (Pyannote/Deepgram): Direct audio diarization

    Args:
        session_id: Session identifier
        diarization_provider: Provider name (pyannote, deepgram, ollama, claude)
                             If None, uses policy primary provider

    Returns:
        dict with diarization results (segments, confidence, model)
    """
    start_time = time.time()
    logger.info(
        "DIARIZATION_SESSION_STARTED",
        session_id=session_id,
        provider=diarization_provider,
        task_id=self.request.id,
    )

    # Update Celery task state with session_id so status endpoint can retrieve it
    self.update_state(state="STARTED", meta={"session_id": session_id, "progress": 10})

    try:
        # 1. Load session metadata (contains 3 transcription sources)
        session_data = session_repo.read(session_id)
        transcription_sources = (
            session_data.get("metadata", {}).get("transcription_sources", {})
            if session_data
            else {}
        )

        if transcription_sources:
            logger.info(
                "3_SOURCES_LOADED",
                session_id=session_id,
                webspeech_count=len(transcription_sources.get("webspeech_final", [])),
                chunks_count=len(transcription_sources.get("transcription_per_chunks", [])),
                full_length=len(transcription_sources.get("full_transcription", "")),
            )
        else:
            logger.warning("NO_TRANSCRIPTION_SOURCES", session_id=session_id)

        # 2. Load transcription task metadata
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION)

        if not task_metadata:
            logger.error("DIARIZATION_NO_TRANSCRIPTION", session_id=session_id)
            return {
                "status": "failed",
                "error": f"No transcription task found for session {session_id}",
            }

        # 3. Load TRIPLE VISION from HDF5: full_transcription + chunks + webspeech_final
        import h5py

        from backend.storage.task_repository import CORPUS_PATH

        full_transcription = None
        webspeech_final = None

        with h5py.File(CORPUS_PATH, "r") as f:
            # Load full_transcription
            full_text_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/full_transcription"
            if full_text_path in f:
                text_data = f[full_text_path][()]
                full_transcription = bytes(text_data).decode("utf-8")
                logger.info(
                    "FULL_TRANSCRIPTION_LOADED",
                    session_id=session_id,
                    text_length=len(full_transcription),
                )

            # Load webspeech_final
            webspeech_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/webspeech_final"
            if webspeech_path in f:
                import json

                ws_data = f[webspeech_path][()]
                webspeech_json = bytes(ws_data).decode("utf-8")
                webspeech_final = json.loads(webspeech_json)
                logger.info(
                    "WEBSPEECH_FINAL_LOADED",
                    session_id=session_id,
                    count=len(webspeech_final),
                )

        # Load transcription chunks (for timestamps and metadata)
        chunks = get_task_chunks(session_id, TaskType.TRANSCRIPTION)

        # If full_transcription is missing, build it from chunks
        if not full_transcription:
            logger.warning(
                "FULL_TRANSCRIPTION_MISSING_BUILDING_FROM_CHUNKS",
                session_id=session_id,
                chunks_count=len(chunks),
            )
            if chunks:
                # Build full_transcription by concatenating all chunk transcripts
                full_transcription = " ".join(
                    chunk.get("transcript", "") for chunk in chunks
                )
                logger.info(
                    "FULL_TRANSCRIPTION_BUILT_FROM_CHUNKS",
                    session_id=session_id,
                    text_length=len(full_transcription),
                    chunks_count=len(chunks),
                )
            else:
                logger.error("NO_CHUNKS_TO_BUILD_TRANSCRIPTION", session_id=session_id)
                return {
                    "status": "failed",
                    "error": "No transcription chunks found to build full_transcription",
                }

        logger.info(
            "TRANSCRIPTION_LOADED",
            session_id=session_id,
            total_chunks=task_metadata.get("total_chunks", 0),
            processed_chunks=task_metadata.get("processed_chunks", 0),
            chunks_loaded=len(chunks),
        )

        # 4. Calculate metadata from chunks (duration, language)
        total_duration = 0.0
        for chunk in chunks:
            end_time = chunk.get("timestamp_end", 0.0)
            total_duration = max(total_duration, end_time)

        # Get primary language from chunks (most common language)
        languages = [chunk.get("language", "unknown") for chunk in chunks if chunk.get("language")]
        primary_language = max(set(languages), key=languages.count) if languages else "en"

        logger.info(
            "METADATA_PREPARED",
            session_id=session_id,
            total_duration=total_duration,
            primary_language=primary_language,
        )

        # 5. Determine diarization provider (agnóstico)
        if not diarization_provider:
            policy_loader = get_policy_loader()
            diarization_provider = policy_loader.get_primary_diarization_provider()
            logger.info(
                "USING_PRIMARY_PROVIDER",
                provider=diarization_provider,
                session_id=session_id,
            )

        # Check if provider is audio-based (pyannote, deepgram) or LLM-based
        is_audio_provider = diarization_provider in ["pyannote", "deepgram", "aws_transcribe", "google_speech"]
        is_llm_provider = diarization_provider in ["ollama", "claude"]

        logger.info(
            "PROVIDER_DETERMINED",
            provider=diarization_provider,
            is_audio=is_audio_provider,
            is_llm=is_llm_provider,
            session_id=session_id,
        )

        # Calculate audio hash (dummy for now, as we don't have audio file path)
        audio_hash = hashlib.sha256(f"{session_id}-audio".encode()).hexdigest()

        # 5b. Route to appropriate diarization method
        diarization_result = None

        if is_llm_provider:
            # ===== LLM Provider Path: TRIPLE VISION with Claude/Ollama =====
            logger.info(
                "🚀 [WORKER] LLM Provider: Calling diarize_full_text with TRIPLE VISION",
                session_id=session_id,
                provider=diarization_provider,
                full_text_length=len(full_transcription),
                chunks_count=len(chunks),
                webspeech_count=len(webspeech_final) if webspeech_final else 0,
                duration_sec=total_duration,
                language=primary_language,
            )

            logger.info(
                "⏳ [WORKER] LLM will intelligently segment using 3 sources (10-60 seconds)...",
                session_id=session_id,
            )

            try:
                diarization_result = diarization_service.diarize_full_text(
                    session_id=session_id,
                    full_text=full_transcription,
                    chunks=chunks,
                    webspeech_final=webspeech_final,
                    audio_file_path=f"storage/audio/{session_id}/full.webm",
                    audio_file_hash=audio_hash,
                    duration_sec=total_duration,
                    language=primary_language,
                )
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "DIARIZATION_LLM_ERROR",
                    session_id=session_id,
                    provider=diarization_provider,
                    error=str(e),
                    exc_info=True,
                )
                return {
                    "status": "failed",
                    "error": f"LLM diarization failed: {str(e)}",
                }

            logger.info(
                "✅ [WORKER] LLM DIARIZATION_COMPLETED",
                session_id=session_id,
                provider=diarization_provider,
                segment_count=len(diarization_result.segments),
                processing_time=diarization_result.processing_time_sec,
            )

        elif is_audio_provider:
            # ===== Audio Provider Path: TRIPLE VISION + Direct Audio Diarization =====
            logger.info(
                "🎤 [WORKER] Audio Provider: Using TRIPLE VISION + audio diarization",
                session_id=session_id,
                provider=diarization_provider,
                full_text_length=len(full_transcription),
                chunks_count=len(chunks),
            )

            try:
                # Get provider config and instance
                policy_loader = get_policy_loader()
                provider_config = policy_loader.get_diarization_provider_config(diarization_provider)
                provider = get_diarization_provider(diarization_provider, provider_config)

                logger.info(
                    "AUDIO_PROVIDER_INITIALIZED",
                    provider=diarization_provider,
                    session_id=session_id,
                )

                # Load full audio file from storage
                from pathlib import Path as PathlibPath

                audio_file_path = PathlibPath(f"storage/audio/{session_id}/full.webm")
                if not audio_file_path.exists():
                    logger.warning(
                        "AUDIO_FILE_NOT_FOUND",
                        path=str(audio_file_path),
                        session_id=session_id,
                    )
                    # Try alternate path
                    audio_file_path = PathlibPath(f"storage/audio/{session_id}.webm")

                if audio_file_path.exists():
                    logger.info(
                        "AUDIO_FILE_FOUND",
                        path=str(audio_file_path),
                        size_bytes=audio_file_path.stat().st_size,
                    )

                    # Run audio provider diarization
                    logger.info(
                        "RUNNING_AUDIO_DIARIZATION",
                        provider=diarization_provider,
                        audio_path=str(audio_file_path),
                    )

                    provider_response = provider.diarize(str(audio_file_path), num_speakers=2)

                    logger.info(
                        "AUDIO_DIARIZATION_COMPLETE",
                        provider=diarization_provider,
                        num_speakers=provider_response.num_speakers,
                        num_segments=len(provider_response.segments),
                        latency_ms=provider_response.latency_ms,
                    )

                    # Convert provider response to DiarizationResult format
                    # For compatibility with existing save_diarization_segments
                    from backend.services.diarization.diarization_service import DiarizationResult

                    diarization_result = DiarizationResult(
                        segments=provider_response.segments,
                        model_llm=diarization_provider,
                        processing_time_sec=(time.time() - start_time),
                        created_at=__import__("datetime").datetime.now(
                            __import__("datetime").timezone.utc
                        ).isoformat(),
                    )
                else:
                    logger.error(
                        "NO_AUDIO_FILE_FOR_PROVIDER",
                        session_id=session_id,
                        provider=diarization_provider,
                    )
                    # Fallback: Use LLM service if available
                    logger.warning("FALLING_BACK_TO_LLM", session_id=session_id)
                    diarization_service = DiarizationService()
                    diarization_result = diarization_service.diarize_full_text(
                        session_id=session_id,
                        full_text=full_transcription,
                        chunks=chunks,
                        webspeech_final=webspeech_final,
                        audio_file_path=f"storage/audio/{session_id}/full.webm",
                        audio_file_hash=audio_hash,
                        duration_sec=total_duration,
                        language=primary_language,
                    )

            except Exception as e:  # noqa: BLE001
                logger.error(
                    "DIARIZATION_AUDIO_PROVIDER_ERROR",
                    session_id=session_id,
                    provider=diarization_provider,
                    error=str(e),
                    exc_info=True,
                )
                return {
                    "status": "failed",
                    "error": f"Audio provider diarization failed: {str(e)}",
                }

        else:
            logger.error(
                "UNKNOWN_DIARIZATION_PROVIDER",
                provider=diarization_provider,
                session_id=session_id,
            )
            return {
                "status": "failed",
                "error": f"Unknown diarization provider: {diarization_provider}",
            }

        if not diarization_result:
            logger.error("DIARIZATION_RESULT_EMPTY", session_id=session_id)
            return {
                "status": "failed",
                "error": "Diarization produced no results",
            }

        # 4. Save diarization result to DIARIZATION task
        ensure_task_exists(session_id, TaskType.DIARIZATION, allow_existing=True)

        # 5. Save segments to HDF5
        save_diarization_segments(
            session_id=session_id,
            segments=diarization_result.segments,
            task_type=TaskType.DIARIZATION,
        )

        diarization_metadata = {
            "job_id": self.request.id,
            "status": TaskStatus.COMPLETED.value,
            "progress_percent": 100,
            "segment_count": len(diarization_result.segments),
            "processing_time_sec": diarization_result.processing_time_sec,
            "model_llm": diarization_result.model_llm,
            "language": primary_language,
            "audio_hash": audio_hash,
            "duration_sec": total_duration,
        }

        update_task_metadata(session_id, TaskType.DIARIZATION, diarization_metadata)

        logger.info(
            "DIARIZATION_TASK_SAVED",
            session_id=session_id,
            path=f"/sessions/{session_id}/tasks/DIARIZATION",
        )

        # 5. Update Session status to DIARIZED
        session_data = session_repo.read(session_id)
        if session_data:
            session_repo.update(
                session_id,
                {
                    "status": SessionStatus.DIARIZED.value,
                    "metadata": {
                        **session_data.get("metadata", {}),
                        "diarization_completed_at": diarization_result.created_at,
                        "diarization_segment_count": len(diarization_result.segments),
                        "diarization_model": diarization_result.model_llm,
                    },
                },
            )
            logger.info(
                "SESSION_MARKED_DIARIZED",
                session_id=session_id,
                status=SessionStatus.DIARIZED.value,
            )
        else:
            logger.warning(
                "SESSION_NOT_FOUND_FOR_UPDATE",
                session_id=session_id,
            )

        processing_time = time.time() - start_time

        return {
            "status": "completed",
            "session_id": session_id,
            "segment_count": len(diarization_result.segments),
            "processing_time_sec": processing_time,
            "model_llm": diarization_result.model_llm,
        }

    except Exception as e:
        logger.error(
            "DIARIZATION_TASK_FAILED",
            session_id=session_id,
            task_id=self.request.id,
            error=str(e),
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": str(e),
        }
