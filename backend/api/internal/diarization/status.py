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

import json
import os
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.src.fi_storage.infrastructure.hdf5.task_repository import get_task_metadata

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
    progress_pct: int = Field(default=0, description="Progress percentage (0-100)")
    segment_count: int = Field(default=0, description="Number of diarized segments")
    transcription_sources: dict[str, Any] | None = Field(
        default=None, description="Triple vision transcription sources"
    )
    error: str | None = Field(default=None, description="Error message if failed")
    created_at: str | None = Field(default=None, description="Job created at timestamp")


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

        # First, check if tests or runtime configured a diarization jobs HDF5 path
        diarization_h5 = os.getenv("AURITY_DIARIZATION_HDF5")
        session_id = job_id
        task_status = "pending"
        task_progress = 0
        segment_count = 0
        transcription_sources = None
        error_message = None

        if diarization_h5:
            # If jobs HDF5 is provided, read /jobs/{job_id} dataset
            try:
                import h5py

                if not os.path.exists(diarization_h5):
                    raise FileNotFoundError(diarization_h5)

                with h5py.File(diarization_h5, "r") as f:
                    path = f"/jobs/{job_id}"
                    if path not in f:  # job missing
                        raise KeyError(f"Job {job_id} not found")

                    raw = f[path][()]
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8")

                    job_obj = json.loads(raw)

                    # Map fields expected by tests
                    session_id = job_obj.get("session_id") or job_obj.get("session") or session_id
                    status_in = job_obj.get("status", "pending")
                    progress_pct = job_obj.get("progress_percent", job_obj.get("progress", 0))

                    # Resolve soap failure case
                    soap_status = (
                        job_obj.get("result_data", {}).get("soap_status")
                        if isinstance(job_obj.get("result_data"), dict)
                        else None
                    )
                    if status_in == "completed" and soap_status == "failed":
                        task_status = "completed_with_errors"
                    else:
                        task_status = status_in

                    task_progress = int(progress_pct or 0)
                    # Segment count may be nested
                    segs = (
                        job_obj.get("result_data", {}).get("diarization", {}).get("segments")
                        if isinstance(job_obj.get("result_data"), dict)
                        else None
                    )
                    if isinstance(segs, list):
                        segment_count = len(segs)

                    # Retain created_at if present
                    created_at = job_obj.get("created_at")

                    logger.info(
                        "DIARIZATION_STATUS_FROM_JOBS_HDF5",
                        job_id=job_id,
                        session_id=session_id,
                        status=task_status,
                        progress=task_progress,
                        segments=segment_count,
                    )
                    # return using job_obj fields where appropriate
                    return DiarizationStatusResponse(
                        job_id=job_id,
                        session_id=session_id,
                        status=task_status,
                        progress_pct=task_progress,
                        segment_count=segment_count,
                        transcription_sources=None,
                        error=job_obj.get("error_message"),
                        created_at=created_at,
                    )
            except KeyError:
                # Job not found in jobs HDF5
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
            except FileNotFoundError:
                # Fall through to corpus-based approach
                logger.warning("DIARIZATION_JOBS_HDF5_NOT_FOUND", path=diarization_h5)
            except Exception as e:
                logger.warning(
                    "DIARIZATION_JOBS_HDF5_READ_FAILED",
                    job_id=job_id,
                    error=str(e),
                )

        # Fallback: read DIARIZATION task metadata from corpus HDF5
        try:
            # Read DIARIZATION task metadata from HDF5 via task repository
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

            from backend.src.fi_storage.infrastructure.hdf5.task_repository import (
                CORPUS_PATH,
            )

            with h5py.File(CORPUS_PATH, "r") as f:
                trans_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION"
                if trans_path in f:
                    trans_group = f[trans_path]
                    sources = {}

                    # Check for webspeech_final
                    if "webspeech_final" in trans_group:  # type: ignore[operator]
                        ws_data = trans_group["webspeech_final"][()]
                        ws_json = bytes(ws_data).decode("utf-8")
                        sources["webspeech_final"] = json.loads(ws_json)

                    # Check for full_transcription
                    if "full_transcription" in trans_group:  # type: ignore[operator]
                        full_data = trans_group["full_transcription"][()]
                        sources["full_transcription"] = bytes(full_data).decode("utf-8")

                    # Count chunks
                    if "chunks" in trans_group:  # type: ignore[operator]
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
            progress_pct=task_progress,
            segment_count=segment_count,
            transcription_sources=transcription_sources,
            error=error_message,
            created_at=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("DIARIZATION_STATUS_FAILED", job_id=job_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get diarization status: {e!s}",
        ) from e
