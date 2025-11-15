"""Diarization job status endpoint - INTERNAL layer.

Provides real-time status of diarization jobs for frontend polling.

Reads metadata from HDF5 DIARIZATION task to show:
- Current status (pending, processing, completed, failed)
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
    status: str = Field(..., description="pending, processing, completed, failed")
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
    "/diarization/jobs/{job_id}",
    response_model=DiarizationStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_diarization_status(job_id: str) -> DiarizationStatusResponse:
    """Get real-time status of diarization job.

    Frontend polls this endpoint every 2s to update progress modal.

    Flow:
    1. Query Celery task status (via Celery result backend)
    2. Read DIARIZATION task metadata from HDF5
    3. Combine both sources for complete status

    Args:
        job_id: Celery task ID (returned from finalize endpoint)

    Returns:
        DiarizationStatusResponse with current status and progress

    Raises:
        404: Job not found
        500: Internal error
    """
    try:
        logger.info("DIARIZATION_STATUS_REQUEST", job_id=job_id)

        # Step 1: Query Celery task status
        from backend.workers.celery_app import celery_app

        task_result = celery_app.AsyncResult(job_id)

        # Map Celery states to our status
        celery_state = task_result.state
        if celery_state == "PENDING":
            task_status = "pending"
            task_progress = 0
        elif celery_state == "STARTED":
            task_status = "processing"
            task_progress = 10  # Just started
        elif celery_state in ("RETRY", "PROGRESS"):
            task_status = "processing"
            # Try to get progress from task info
            task_info = task_result.info or {}
            task_progress = task_info.get("progress", 50)
        elif celery_state == "SUCCESS":
            task_status = "completed"
            task_progress = 100
        elif celery_state == "FAILURE":
            task_status = "failed"
            task_progress = 0
        else:
            task_status = "pending"
            task_progress = 0

        # Extract session_id from task result (if available)
        task_info = task_result.info or {}
        session_id = task_info.get("session_id", "unknown")

        # If we have session_id, try to get more detailed info from HDF5
        segment_count = 0
        transcription_sources = None
        error_message = None

        if session_id != "unknown":
            try:
                # Step 2: Read DIARIZATION task metadata from HDF5
                diarization_metadata = get_task_metadata(session_id, TaskType.DIARIZATION)

                if diarization_metadata:
                    # Update status from HDF5 (more authoritative)
                    hdf5_status = diarization_metadata.get("status", task_status)
                    hdf5_progress = diarization_metadata.get("progress_percent", task_progress)
                    segment_count = diarization_metadata.get("segment_count", 0)

                    # Use HDF5 status if available
                    if hdf5_status:
                        task_status = hdf5_status
                        task_progress = hdf5_progress

                    logger.info(
                        "DIARIZATION_STATUS_FROM_HDF5",
                        job_id=job_id,
                        session_id=session_id,
                        status=task_status,
                        progress=task_progress,
                        segments=segment_count,
                    )

                # Step 3: Try to get transcription sources (triple vision)
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
                # Continue with Celery status only

        # Handle failure case
        if celery_state == "FAILURE":
            if isinstance(task_result.info, dict):
                error_message = task_result.info.get("error", str(task_result.info))
            else:
                error_message = str(task_result.info)

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
