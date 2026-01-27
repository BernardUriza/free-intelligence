from __future__ import annotations

from typing import Any

from backend.utils.common.api.public.models import UpdateSegmentRequest
from backend.utils.common.logging.logger import get_logger
from backend.validators import validate_session_id
from fastapi import APIRouter, HTTPException, status

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/diarization/jobs/{job_id}",
    status_code=status.HTTP_200_OK,
)
async def get_diarization_status_workflow(job_id: str) -> dict[str, Any]:
    """Poll diarization job status (PUBLIC orchestrator).

    Calls INTERNAL diarization status function directly and returns combined status.
    """
    from backend.services.transcription.api.internal.diarization.status import get_diarization_status

    try:
        result = await get_diarization_status(job_id)

        logger.info(
            "DIARIZATION_STATUS_POLLED",
            job_id=job_id,
            status=(result.get("status") if isinstance(result, dict) else result.status),
            progress=(result.get("progress") if isinstance(result, dict) else result.progress),
        )

        # Normalize to dict for response
        return result if isinstance(result, dict) else result.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "DIARIZATION_STATUS_WORKFLOW_FAILED",
            job_id=job_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get diarization status: {e!s}",
        ) from e


@router.get(
    "/sessions/{session_id}/diarization/segments",
    status_code=status.HTTP_200_OK,
)
async def get_diarization_segments_workflow(session_id: str) -> dict[str, Any]:
    """Get diarization segments (PUBLIC orchestrator)."""
    validate_session_id(session_id)

    from backend.models.task_type import TaskType
    # FIXME: Broken import - use DI container instead
    # from infrastructure.storage.infrastructure.hdf5.task_repository import (
        get_diarization_segments,
        get_task_metadata,
    )

    try:
        logger.info("DIARIZATION_SEGMENTS_GET_STARTED", session_id=session_id)

        metadata = get_task_metadata(session_id, TaskType.DIARIZATION)
        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diarization task not found for session {session_id}",
            )

        task_status = metadata.get("status", "pending")
        if task_status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Diarization not completed yet (status: {task_status})",
            )

        segments = get_diarization_segments(session_id)

        logger.info(
            "DIARIZATION_SEGMENTS_GET_SUCCESS",
            session_id=session_id,
            segment_count=len(segments),
        )

        transcription_sources = metadata.get("transcription_sources", {})

        return {
            "session_id": session_id,
            "segments": segments,
            "segment_count": len(segments),
            "provider": metadata.get("provider", "unknown"),
            "completed_at": metadata.get("completed_at", ""),
            "transcription_sources": transcription_sources,
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error("DIARIZATION_SEGMENTS_NOT_FOUND", session_id=session_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(
            "DIARIZATION_SEGMENTS_GET_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get diarization segments: {e!s}",
        ) from e


@router.patch(
    "/sessions/{session_id}/diarization/segments/{segment_index}",
    status_code=status.HTTP_200_OK,
)
async def update_diarization_segment_workflow(
    session_id: str,
    segment_index: int,
    request: UpdateSegmentRequest,
) -> dict[str, Any]:
    """Update text of a diarization segment (PUBLIC orchestrator)."""
    # FIXME: Broken import - use DI container instead
    # from infrastructure.storage.infrastructure.hdf5.task_repository import (
        update_diarization_segment_text,
    )

    try:
        logger.info(
            "DIARIZATION_SEGMENT_UPDATE_STARTED",
            session_id=session_id,
            segment_index=segment_index,
        )

        if segment_index < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="segment_index must be >= 0",
            )

        updated_segment = update_diarization_segment_text(
            session_id=session_id,
            segment_index=segment_index,
            new_text=request.text,
        )

        logger.info(
            "DIARIZATION_SEGMENT_UPDATE_SUCCESS",
            session_id=session_id,
            segment_index=segment_index,
        )

        return {
            "session_id": session_id,
            "segment_index": segment_index,
            "segment": updated_segment,
            "updated_at": str(
                __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat()
            ),
        }

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(
            "DIARIZATION_SEGMENT_UPDATE_NOT_FOUND",
            session_id=session_id,
            segment_index=segment_index,
            error=str(e),
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(
            "DIARIZATION_SEGMENT_UPDATE_FAILED",
            session_id=session_id,
            segment_index=segment_index,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update segment: {e!s}",
        ) from e
