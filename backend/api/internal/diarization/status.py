"""Diarization job status endpoint - INTERNAL layer.

Provides real-time status of diarization jobs for frontend polling.

Reads metadata from HDF5 DIARIZATION task to show:
- Current status (pending, in_progress, completed, failed)
- Progress percentage
- Segment count
- Transcription sources (triple vision)

Author: Bernard Uriza Orozco
Created: 2025-11-14
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.storage.task_repository import get_task_metadata

logger = get_logger(__name__)

router = APIRouter(tags=["internal-diarization"])


# ============================================================================
# Response Models
# ============================================================================


class DiarizationStatusResponse(BaseModel):
    """Real-time diarization job status."""

    job_id: str = Field(..., description="Celery task ID")
    session_id: str = Field(..., description="Session identifier")
    status: str = Field(..., description="pending, in_progress, completed, failed")
    progress: int = Field(default=0, description="Progress percentage (0-100)")
    segment_count: int = Field(default=0, description="Number of diarized segments")
    transcription_sources: Optional[dict[str, Any]] = Field(
        default=None, description="Triple vision transcription sources"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/jobs/{job_id}",
    response_model=DiarizationStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_diarization_status(job_id: str) -> DiarizationStatusResponse:
    """Get real-time status of diarization job.

    Frontend polls this endpoint every 2s to update progress modal.

    Flow:
    1. Use job_id as session_id (since we use session_id as job identifier now)
    2. Read DIARIZATION task metadata from HDF5
    3. Return status

    Args:
        job_id: Session ID (job_id is now the session_id)

    Returns:
        DiarizationStatusResponse with current status and progress

    Raises:
        404: Job not found
        500: Internal error
    """
    try:
        logger.info("DIARIZATION_STATUS_REQUEST", job_id=job_id)

        # Now job_id is the session_id (since we removed Celery)
        session_id = job_id
        task_status = "pending"
        task_progress = 0

        # Read DIARIZATION task metadata from HDF5
        segment_count = 0
        transcription_sources = None
        error_message = None

        try:
            # Read DIARIZATION task metadata from HDF5
            diarization_metadata = get_task_metadata(session_id, TaskType.DIARIZATION)

            if diarization_metadata:
                # Update status from HDF5
                task_status = diarization_metadata.get("status", "pending")
                task_progress = diarization_metadata.get("progress_percent", 0)
                segment_count = diarization_metadata.get("segment_count", 0)

                logger.info(
                    "DIARIZATION_STATUS_FROM_HDF5",
                    job_id=job_id,
                    session_id=session_id,
                    status=task_status,
                    progress=task_progress,
                    segments=segment_count,
                )

            # Try to get transcription sources (triple vision)
            import h5py

            from backend.storage.task_repository import CORPUS_PATH

            with h5py.File(CORPUS_PATH, "r") as f:
                trans_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION"
                if trans_path in f:
                    trans_group = f[trans_path]
                    sources = {}

                    # Check for webspeech_final
                    if "webspeech_final" in trans_group:
                        import json

                        ws_data = trans_group["webspeech_final"][()]
                        ws_json = bytes(ws_data).decode("utf-8")
                        sources["webspeech_final"] = json.loads(ws_json)

                    # Check for full_transcription
                    if "full_transcription" in trans_group:
                        full_data = trans_group["full_transcription"][()]
                        sources["full_transcription"] = bytes(full_data).decode("utf-8")

                    # Count chunks
                    if "chunks" in trans_group:
                        sources["transcription_per_chunks"] = list(trans_group["chunks"].keys())

                    if sources:
                        transcription_sources = sources

        except Exception as hdf5_err:
            logger.warning(
                "DIARIZATION_STATUS_HDF5_FAILED",
                job_id=job_id,
                session_id=session_id,
                error=str(hdf5_err),
            )
            # Continue with whatever status we have

        return DiarizationStatusResponse(
            job_id=job_id,
            session_id=session_id,
            status=task_status,
            progress=task_progress,
            segment_count=segment_count,
            transcription_sources=transcription_sources,
            error=error_message,
        )

    except Exception as e:
        logger.error("DIARIZATION_STATUS_FAILED", job_id=job_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get diarization status: {e!s}",
        ) from e
