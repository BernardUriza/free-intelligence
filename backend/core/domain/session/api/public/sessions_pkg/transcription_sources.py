from __future__ import annotations

import json

import h5py
from backend.utils.common.api.public.models import TranscriptionSourcesModel
from backend.utils.common.logging.logger import get_logger
from backend.validators import validate_session_id
from fastapi import APIRouter, HTTPException, status

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/sessions/{session_id}/transcription-sources",
    status_code=status.HTTP_200_OK,
)
async def get_transcription_sources_workflow(session_id: str) -> TranscriptionSourcesModel:
    """Get all 3 transcription sources for a saved session (PUBLIC endpoint)."""
    from backend.models.task_type import TaskType
    from backend.core.infrastructure.storage.infrastructure.hdf5.task_repository import (
        CORPUS_PATH,
        get_task_chunks,
    )

    validate_session_id(session_id)

    try:
        logger.info("TRANSCRIPTION_SOURCES_GET_STARTED", session_id=session_id)

        webspeech_final: list[str] = []
        transcription_per_chunks: list[dict] = []
        full_transcription: str = ""

        # Load webspeech_final from HDF5 (if exists)
        with h5py.File(CORPUS_PATH, "r") as f:
            webspeech_path = f"/sessions/{session_id}/tasks/{TaskType.TRANSCRIPTION.name.lower()}/webspeech_final"
            if webspeech_path in f:
                webspeech_data = f[webspeech_path][()]
                webspeech_json = bytes(webspeech_data).decode("utf-8")
                webspeech_final = json.loads(webspeech_json)
                logger.info("WEBSPEECH_LOADED", session_id=session_id, count=len(webspeech_final))
            else:
                logger.warning(
                    "WEBSPEECH_NOT_FOUND",
                    session_id=session_id,
                    hint="Session may not have webspeech data (normal for old sessions)",
                )

        # Build transcription_per_chunks and full_transcription
        try:
            chunks = get_task_chunks(session_id=session_id, task_type=TaskType.TRANSCRIPTION)

            transcripts_list = []
            for chunk in chunks:
                chunk_dict = {
                    "chunk_number": chunk.get("chunk_number", 0),
                    "transcript": chunk.get("transcript", ""),
                    "timestamp_start": chunk.get("timestamp_start", 0.0),
                    "timestamp_end": chunk.get("timestamp_end", 0.0),
                    "duration": chunk.get("duration", 0.0),
                    "provider": chunk.get("provider", "unknown"),
                    "confidence": chunk.get("confidence", 0.0),
                    "resolution_time_seconds": chunk.get("resolution_time_seconds", 0.0),
                    "retry_attempts": chunk.get("retry_attempts", 0),
                    "polling_attempts": chunk.get("polling_attempts", 0),
                }
                transcription_per_chunks.append(chunk_dict)

                transcript = chunk.get("transcript", "")
                if transcript:
                    transcripts_list.append(transcript)

            full_transcription = " ".join(transcripts_list)

            logger.info(
                "CHUNKS_LOADED",
                session_id=session_id,
                chunk_count=len(chunks),
                full_text_length=len(full_transcription),
            )

        except ValueError as e:
            logger.warning("NO_TRANSCRIPTION_CHUNKS", session_id=session_id, error=str(e))

        logger.info(
            "TRANSCRIPTION_SOURCES_GET_SUCCESS",
            session_id=session_id,
            webspeech_count=len(webspeech_final),
            chunks_count=len(transcription_per_chunks),
            full_length=len(full_transcription),
        )

        return TranscriptionSourcesModel(
            webspeech_final=webspeech_final,
            transcription_per_chunks=transcription_per_chunks,
            full_transcription=full_transcription,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "TRANSCRIPTION_SOURCES_GET_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transcription sources: {e!s}",
        ) from e
