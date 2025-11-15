"""Celery tasks for diarization (speaker separation + text improvement).

Tasks:
- diarize_chunk_task: Process individual audio chunk with provider-agnostic diarization
- diarize_session_task: Process all chunks from a session with DiarizationService

Architecture:
  PUBLIC/INTERNAL → dispatch task → WORKER (this file) → DiarizationProvider/DiarizationService

Author: Bernard Uriza Orozco
Created: 2025-11-14
Updated: 2025-11-15 (Added provider-agnostic diarization)
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
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


@celery_app.task(name="diarize_chunk", bind=True, max_retries=3)
def diarize_chunk_task(
    self,
    session_id: str,
    chunk_number: int,
    diarization_provider: str | None = None,
) -> dict[str, Any]:
    """Diarize individual audio chunk using provider-agnostic diarization.

    Identifies speakers in a single audio chunk (who speaks when).
    Stores speaker segments with timestamps and confidence scores.

    Args:
        session_id: Session identifier
        chunk_number: Chunk index (e.g., 0, 1, 2, ...)
        diarization_provider: Provider name (pyannote, deepgram, aws_transcribe, google_speech)
                             If None, uses policy primary provider

    Returns:
        dict with diarization results (speaker count, segments, latency)
    """
    start_time = time.time()
    logger.info(
        "DIARIZATION_CHUNK_STARTED",
        session_id=session_id,
        chunk_number=chunk_number,
        provider=diarization_provider,
        task_id=self.request.id,
    )

    self.update_state(
        state="STARTED",
        meta={
            "session_id": session_id,
            "chunk_number": chunk_number,
            "progress": 10,
        },
    )

    try:
        # 1. Load policy and determine provider
        if not diarization_provider:
            policy_loader = get_policy_loader()
            diarization_provider = policy_loader.get_primary_diarization_provider()
            logger.info(
                "USING_PRIMARY_PROVIDER",
                provider=diarization_provider,
                chunk_number=chunk_number,
            )

        # 2. Get provider config from policy
        policy_loader = get_policy_loader()
        provider_config = policy_loader.get_diarization_provider_config(diarization_provider)

        # 3. Get diarization provider instance
        provider = get_diarization_provider(diarization_provider, provider_config)
        logger.info(
            "PROVIDER_INITIALIZED",
            provider=diarization_provider,
            chunk_number=chunk_number,
        )

        # 4. Load audio chunk from HDF5
        import h5py

        from backend.storage.task_repository import CORPUS_PATH

        chunk_data = None
        audio_path_str = None

        with h5py.File(CORPUS_PATH, "r") as f:
            chunk_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/chunks/chunk_{chunk_number}"
            if chunk_path in f:
                chunk_group = f[chunk_path]
                # Audio is stored as binary in 'audio_bytes' dataset
                if "audio_bytes" in chunk_group:
                    audio_bytes = chunk_group["audio_bytes"][()]
                    # Save to temporary file for diarization
                    temp_audio_path = Path(f"/tmp/diarization_{session_id}_{chunk_number}.webm")
                    with open(temp_audio_path, "wb") as audio_file:
                        audio_file.write(audio_bytes)
                    audio_path_str = str(temp_audio_path)
                    logger.info(
                        "AUDIO_CHUNK_LOADED",
                        session_id=session_id,
                        chunk_number=chunk_number,
                        audio_path=audio_path_str,
                        size_bytes=len(audio_bytes),
                    )
            else:
                logger.error(
                    "AUDIO_CHUNK_NOT_FOUND",
                    session_id=session_id,
                    chunk_number=chunk_number,
                    path=chunk_path,
                )
                return {
                    "status": "failed",
                    "error": f"Audio chunk {chunk_number} not found in HDF5",
                    "chunk_number": chunk_number,
                }

        # 5. Run diarization on chunk
        if not audio_path_str:
            return {
                "status": "failed",
                "error": "Failed to load audio path",
                "chunk_number": chunk_number,
            }

        logger.info(
            "DIARIZATION_STARTING",
            provider=diarization_provider,
            chunk_number=chunk_number,
        )

        diarization_response = provider.diarize(
            audio_path_str,
            num_speakers=2,  # Medical context: doctor + patient
        )

        latency_ms = diarization_response.latency_ms or (time.time() - start_time) * 1000

        logger.info(
            "DIARIZATION_CHUNK_COMPLETE",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=diarization_provider,
            num_speakers=diarization_response.num_speakers,
            num_segments=len(diarization_response.segments),
            latency_ms=round(latency_ms, 2),
            confidence=round(diarization_response.confidence, 2),
        )

        # 6. Store speaker segments in HDF5
        ensure_task_exists(session_id, TaskType.DIARIZATION, allow_existing=True)

        # Convert provider segments to standard format and save
        import h5py

        with h5py.File(CORPUS_PATH, "a") as f:
            chunk_diar_path = f"/sessions/{session_id}/tasks/DIARIZATION/chunks/chunk_{chunk_number}"

            # Create group if needed
            if chunk_diar_path not in f:
                f.create_group(chunk_diar_path)

            chunk_group = f[chunk_diar_path]

            # Store speaker segments as JSON
            import json

            segments_data = {
                "num_speakers": diarization_response.num_speakers,
                "duration_sec": diarization_response.duration,
                "confidence": diarization_response.confidence,
                "provider": diarization_response.provider,
                "segments": [
                    {
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "speaker_id": seg.speaker.speaker_id,
                        "speaker_name": seg.speaker.name,
                        "speaker_confidence": seg.speaker.confidence,
                        "segment_confidence": seg.confidence,
                        "text": seg.text,
                        "duration": seg.duration,
                    }
                    for seg in diarization_response.segments
                ],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            segments_json = json.dumps(segments_data)
            chunk_group["segments"] = segments_json.encode("utf-8")
            chunk_group["num_speakers"] = diarization_response.num_speakers
            chunk_group["latency_ms"] = latency_ms

            logger.info(
                "DIARIZATION_SEGMENTS_STORED",
                session_id=session_id,
                chunk_number=chunk_number,
                segments_count=len(diarization_response.segments),
                path=chunk_diar_path,
            )

        # Clean up temp audio file
        if audio_path_str:
            try:
                Path(audio_path_str).unlink(missing_ok=True)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "TEMP_AUDIO_CLEANUP_FAILED",
                    path=audio_path_str,
                    error=str(e),
                )

        processing_time = time.time() - start_time

        return {
            "status": "completed",
            "session_id": session_id,
            "chunk_number": chunk_number,
            "provider": diarization_provider,
            "num_speakers": diarization_response.num_speakers,
            "num_segments": len(diarization_response.segments),
            "confidence": round(diarization_response.confidence, 2),
            "latency_ms": round(latency_ms, 2),
            "processing_time_sec": round(processing_time, 2),
        }

    except Exception as e:  # noqa: BLE001
        logger.error(
            "DIARIZATION_CHUNK_FAILED",
            session_id=session_id,
            chunk_number=chunk_number,
            provider=diarization_provider,
            error=str(e),
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": str(e),
            "chunk_number": chunk_number,
        }


@celery_app.task(name="diarize_session", bind=True, max_retries=3)
def diarize_session_task(self, session_id: str) -> dict[str, Any]:
    """Diarize all transcribed chunks from a session.

    Reads TranscriptionJob, converts chunks to DiarizationSegments,
    applies speaker classification + text improvement with Ollama.

    Args:
        session_id: Session identifier

    Returns:
        dict with diarization results
    """
    start_time = time.time()
    logger.info("DIARIZATION_TASK_STARTED", session_id=session_id, task_id=self.request.id)

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

        # 5. Run DiarizationService with TRIPLE VISION (full_text + chunks + webspeech)
        logger.info("🔧 [WORKER] Initializing DiarizationService...", session_id=session_id)
        diarization_service = DiarizationService()

        # Calculate audio hash (dummy for now, as we don't have audio file path)
        audio_hash = hashlib.sha256(f"{session_id}-audio".encode()).hexdigest()

        logger.info(
            "🚀 [WORKER] Calling diarize_full_text with TRIPLE VISION",
            session_id=session_id,
            full_text_length=len(full_transcription),
            chunks_count=len(chunks),
            webspeech_count=len(webspeech_final) if webspeech_final else 0,
            duration_sec=total_duration,
            language=primary_language,
        )

        # NEW: Use diarize_full_text() with TRIPLE VISION
        # Qwen will intelligently segment and classify using 3 sources:
        # - chunks: Timestamps (every 13s) with mixed speakers
        # - full_transcription: Clean complete text
        # - webspeech_final: Instant transcriptions (for pause detection)
        logger.info(
            "⏳ [WORKER] This will call Claude API and may take 10-60 seconds...",
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
        except Exception as e:
            logger.error("DIARIZATION_SERVICE_ERROR", session_id=session_id, error=str(e), exc_info=True)
            return {
                "status": "failed",
                "error": f"Diarization service error: {str(e)}",
            }

        logger.info(
            "✅ [WORKER] DIARIZATION_COMPLETED",
            session_id=session_id,
            segment_count=len(diarization_result.segments),
            processing_time=diarization_result.processing_time_sec,
        )

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
