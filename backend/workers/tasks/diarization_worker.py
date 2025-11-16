"""Diarization worker - Speaker separation."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from backend.logger import get_logger
from backend.models.task_type import TaskStatus, TaskType
from backend.policy.policy_loader import get_policy_loader
from backend.providers.diarization import get_diarization_provider
from backend.storage.task_repository import (
    get_task_chunks,
    save_diarization_segments,
    task_exists,
    update_task_metadata,
)
from backend.workers.tasks.base_worker import WorkerResult, measure_time

logger = get_logger(__name__)


@measure_time
def diarize_session_worker(
    session_id: str,
    diarization_provider: str | None = None,
) -> dict[str, Any]:
    """Synchronous diarization (speaker separation).

    Args:
        session_id: Session identifier
        diarization_provider: Provider (azure_gpt4, ollama, etc)

    Returns:
        WorkerResult with segments, speakers, confidence
    """
    try:
        start_time = time.time()
        logger.info(
            "DIARIZE_SESSION_START",
            session_id=session_id,
            provider=diarization_provider,
        )

        # Check DIARIZATION task exists
        if not task_exists(session_id, TaskType.DIARIZATION):
            raise ValueError(f"DIARIZATION task not found for {session_id}. Must finalize first.")

        # Get provider
        if not diarization_provider:
            policy_loader = get_policy_loader()
            diarization_config = policy_loader.get_diarization_config()
            diarization_provider = diarization_config.get("primary_provider", "azure_gpt4")

        # Get transcription sources (Triple Vision: webspeech > full_text > chunks)
        chunks_data = get_task_chunks(session_id, TaskType.TRANSCRIPTION)
        if not chunks_data:
            raise ValueError(f"No TRANSCRIPTION chunks for {session_id}")

        # Try to load webspeech_final from HDF5 (most complete source)
        webspeech_final = None
        full_text = None

        import json

        import h5py

        from backend.storage.task_repository import CORPUS_PATH

        try:
            with h5py.File(CORPUS_PATH, "r") as f:
                # Load webspeech_final (priority source)
                webspeech_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/webspeech_final"
                if webspeech_path in f:
                    webspeech_data = f[webspeech_path][()]
                    webspeech_json = bytes(webspeech_data).decode("utf-8")
                    webspeech_final = json.loads(webspeech_json)
                    logger.info(
                        "WEBSPEECH_LOADED",
                        session_id=session_id,
                        count=len(webspeech_final),
                    )
                else:
                    logger.warning(
                        "WEBSPEECH_NOT_FOUND",
                        session_id=session_id,
                        hint="Frontend may not have sent webspeech_final",
                    )

                # Load full_transcription (fallback)
                full_text_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/full_transcription"
                if full_text_path in f:
                    full_text_data = f[full_text_path][()]
                    full_text = bytes(full_text_data).decode("utf-8")
                    logger.info(
                        "FULL_TRANSCRIPTION_LOADED",
                        session_id=session_id,
                        length=len(full_text),
                    )
        except Exception as e:
            logger.warning(
                "TRIPLE_VISION_LOAD_FAILED",
                session_id=session_id,
                error=str(e),
            )

        # Use best available source (priority: webspeech > full_text > chunks)
        if webspeech_final:
            full_text = " ".join(webspeech_final)
            logger.info(
                "USING_WEBSPEECH_SOURCE",
                session_id=session_id,
                count=len(webspeech_final),
                text_length=len(full_text),
            )
        elif full_text:
            logger.info(
                "USING_FULL_TRANSCRIPTION_SOURCE",
                session_id=session_id,
                text_length=len(full_text),
            )
        else:
            # Fallback: build from chunks
            full_text = " ".join(chunk.get("transcript", "") for chunk in chunks_data)
            logger.info(
                "USING_CHUNKS_FALLBACK",
                session_id=session_id,
                chunk_count=len(chunks_data),
                text_length=len(full_text),
            )

        # Estimate duration based on text length (empirical: ~0.3s per 100 words)
        word_count = len(full_text.split())
        estimated_duration = max(5, int(word_count / 100 * 0.3))  # Min 5 seconds

        # Update metadata: IN_PROGRESS with progress 10% (started)
        update_task_metadata(
            session_id,
            TaskType.DIARIZATION,
            {
                "status": TaskStatus.IN_PROGRESS,
                "provider": diarization_provider,
                "progress_percent": 10,
                "estimated_duration_seconds": estimated_duration,
                "started_at": datetime.now(UTC).isoformat(),
                "word_count": word_count,
            },
        )
        logger.info(
            "DIARIZATION_PROGRESS",
            session_id=session_id,
            progress=10,
            estimated_duration=estimated_duration,
        )

        # Update progress: 30% (text loaded, calling provider)
        update_task_metadata(
            session_id,
            TaskType.DIARIZATION,
            {
                "progress_percent": 30,
                "status_message": "Calling Azure GPT-4 for speaker separation...",
            },
        )

        # Diarize with TRIPLE VISION (this is the slow part - Azure API call)
        provider = get_diarization_provider(diarization_provider)
        response = provider.diarize(
            audio_path=None,
            transcript=full_text,
            num_speakers=2,
            chunks=chunks_data,  # Pass chunks with real timestamps
            webspeech_final=webspeech_final,  # Pass webspeech for completeness
        )

        # Update progress: 80% (diarization complete, processing results)
        update_task_metadata(
            session_id,
            TaskType.DIARIZATION,
            {"progress_percent": 80, "status_message": "Processing diarization results..."},
        )

        result = {
            "segments": response.segments,
            "num_speakers": response.num_speakers,
            "confidence": response.confidence,
            "provider": response.provider,
        }

        elapsed_time = time.time() - start_time

        # Save segments to HDF5 (following task-based pattern)
        save_diarization_segments(session_id, response.segments)
        logger.info(
            "DIARIZATION_SEGMENTS_PERSISTED",
            session_id=session_id,
            segment_count=len(response.segments),
        )

        # Update metadata: COMPLETED with progress 100%
        update_task_metadata(
            session_id,
            TaskType.DIARIZATION,
            {
                "status": TaskStatus.COMPLETED,
                "provider": diarization_provider,
                "segment_count": len(result["segments"]),
                "progress_percent": 100,
                "completed_at": datetime.now(UTC).isoformat(),
                "duration_seconds": round(elapsed_time, 2),
                "status_message": f"Completed: {len(result['segments'])} segments identified",
            },
        )

        logger.info(
            "DIARIZE_SESSION_SUCCESS",
            session_id=session_id,
            segments=len(result["segments"]),
            duration_seconds=round(elapsed_time, 2),
        )

        return WorkerResult(session_id=session_id, result=result)

    except Exception as e:
        logger.error(
            "DIARIZE_SESSION_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )

        # Update metadata with FAILED status
        try:
            update_task_metadata(
                session_id,
                TaskType.DIARIZATION,
                {
                    "status": TaskStatus.FAILED,
                    "progress_percent": 0,
                    "error": str(e),
                    "failed_at": datetime.now(UTC).isoformat(),
                },
            )
        except Exception as meta_error:
            logger.error(
                "FAILED_TO_UPDATE_ERROR_METADATA",
                session_id=session_id,
                error=str(meta_error),
            )

        raise
