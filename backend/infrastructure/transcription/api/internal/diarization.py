"""Diarization job status endpoint - INTERNAL layer.

Provides real-time status of diarization jobs for frontend polling.

Python 2026 patterns:
- Annotated[T, Depends(...)] for cleaner DI
- `|` union syntax for type hints
- Literal types for status values
- match/case for cleaner branching

Reads metadata from HDF5 DIARIZATION task to show:
- Current status (pending, in_progress, completed, failed)
- Progress percentage
- Segment count
- Transcription sources (triple vision)

Endpoints:
- GET /jobs/{job_id} - Get diarization job status

Migrated: 2026-02-03 (Phase 3 - Domain Migration)
From: backend/api/routers/transcription/internal/diarization/status.py
"""

from __future__ import annotations

import json
import os
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.models.task_type import TaskType
from backend.repositories.interfaces import ITaskRepository
from backend.infrastructure.common.repository_singletons import get_task_repository
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["internal-diarization"])

type DiarizationStatus = Literal["pending", "in_progress", "completed", "completed_with_errors", "failed"]


class DiarizationStatusResponse(BaseModel):
    """Real-time diarization job status."""

    job_id: str = Field(..., description="Celery task ID")
    session_id: str = Field(..., description="Session identifier")
    status: DiarizationStatus
    progress_pct: int = Field(default=0, ge=0, le=100, description="Progress percentage (0-100)")
    segment_count: int = Field(default=0, ge=0, description="Number of diarized segments")
    transcription_sources: dict[str, Any] | None = Field(
        default=None, description="Triple vision transcription sources"
    )
    error: str | None = Field(default=None, description="Error message if failed")
    created_at: str | None = Field(default=None, description="Job created at timestamp")


@router.get("/jobs/{job_id}", response_model=DiarizationStatusResponse, status_code=status.HTTP_200_OK)
async def get_diarization_status(
    job_id: str,
    task_repo: Annotated[ITaskRepository, Depends(get_task_repository)],
) -> DiarizationStatusResponse:
    """Get real-time status of diarization job.

    Frontend polls this endpoint every 2s to update progress modal.

    Flow:
    1. Use job_id as session_id (since we use session_id as job identifier now)
    2. Read DIARIZATION task metadata from HDF5
    3. Return status

    Args:
        job_id: Session ID (job_id is now the session_id)
        task_repo: Task repository (injected)

    Returns:
        DiarizationStatusResponse with current status and progress

    Raises:
        404: Job not found
        500: Internal error
    """
    try:
        logger.info("DIARIZATION_STATUS_REQUEST", job_id=job_id)

        diarization_h5 = os.getenv("AURITY_DIARIZATION_HDF5")
        session_id = job_id
        task_status: DiarizationStatus = "pending"
        task_progress = 0
        segment_count = 0
        transcription_sources = None
        error_message = None
        created_at = None

        if diarization_h5:
            result = _read_from_jobs_hdf5(job_id, diarization_h5)
            if result:
                return result

        # Fallback: read DIARIZATION task metadata from corpus HDF5
        try:
            diarization_metadata = task_repo.get_task_metadata(session_id, TaskType.DIARIZATION)

            if diarization_metadata:
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

            transcription_sources = _get_transcription_sources(session_id)

        except Exception as hdf5_err:
            logger.warning(
                "DIARIZATION_STATUS_HDF5_FAILED",
                job_id=job_id,
                session_id=session_id,
                error=str(hdf5_err),
            )

        return DiarizationStatusResponse(
            job_id=job_id,
            session_id=session_id,
            status=task_status,
            progress_pct=task_progress,
            segment_count=segment_count,
            transcription_sources=transcription_sources,
            error=error_message,
            created_at=created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("DIARIZATION_STATUS_FAILED", job_id=job_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get diarization status: {e!s}",
        ) from e


def _read_from_jobs_hdf5(job_id: str, diarization_h5: str) -> DiarizationStatusResponse | None:
    """Try to read diarization status from jobs HDF5 file."""
    try:
        import h5py

        if not os.path.exists(diarization_h5):
            return None

        with h5py.File(diarization_h5, "r") as f:
            path = f"/jobs/{job_id}"
            if path not in f:
                raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

            raw = f[path][()]
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")

            job_obj = json.loads(raw)

            session_id = job_obj.get("session_id") or job_obj.get("session") or job_id
            status_in = job_obj.get("status", "pending")
            progress_pct = job_obj.get("progress_percent", job_obj.get("progress", 0))

            soap_status = (
                job_obj.get("result_data", {}).get("soap_status")
                if isinstance(job_obj.get("result_data"), dict)
                else None
            )
            task_status = "completed_with_errors" if status_in == "completed" and soap_status == "failed" else status_in

            segs = (
                job_obj.get("result_data", {}).get("diarization", {}).get("segments")
                if isinstance(job_obj.get("result_data"), dict)
                else None
            )
            segment_count = len(segs) if isinstance(segs, list) else 0

            logger.info(
                "DIARIZATION_STATUS_FROM_JOBS_HDF5",
                job_id=job_id,
                session_id=session_id,
                status=task_status,
                progress=int(progress_pct or 0),
                segments=segment_count,
            )

            return DiarizationStatusResponse(
                job_id=job_id,
                session_id=session_id,
                status=task_status,
                progress_pct=int(progress_pct or 0),
                segment_count=segment_count,
                transcription_sources=None,
                error=job_obj.get("error_message"),
                created_at=job_obj.get("created_at"),
            )

    except HTTPException:
        raise
    except FileNotFoundError:
        logger.warning("DIARIZATION_JOBS_HDF5_NOT_FOUND", path=diarization_h5)
        return None
    except Exception as e:
        logger.warning("DIARIZATION_JOBS_HDF5_READ_FAILED", job_id=job_id, error=str(e))
        return None


def _get_transcription_sources(session_id: str) -> dict[str, Any] | None:
    """Try to get transcription sources (triple vision) from corpus HDF5."""
    try:
        import h5py
        from backend.domain.storage.corpus_manager import CORPUS_PATH

        with h5py.File(CORPUS_PATH, "r") as f:
            trans_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION"
            if trans_path not in f:
                return None

            trans_group = f[trans_path]
            sources = {}

            if "webspeech_final" in trans_group:
                ws_data = trans_group["webspeech_final"][()]
                ws_json = bytes(ws_data).decode("utf-8")
                sources["webspeech_final"] = json.loads(ws_json)

            if "full_transcription" in trans_group:
                full_data = trans_group["full_transcription"][()]
                sources["full_transcription"] = bytes(full_data).decode("utf-8")

            if "chunks" in trans_group:
                sources["transcription_per_chunks"] = list(trans_group["chunks"].keys())

            return sources if sources else None

    except Exception:
        return None
