from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.domain.session.dependencies import get_task_repository
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.infrastructure.common.api.public.models import ImportDiarizationRequest, UpdateSegmentRequest
from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.utils.common.logging.logger import get_logger
from backend.validators import validate_session_id
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/diarization/jobs/{job_id}",
    status_code=status.HTTP_200_OK,
)
async def get_diarization_status_workflow(
    job_id: str,
    audit_service: DIAuditService = Depends(get_audit_service),
) -> dict[str, Any]:
    """Poll diarization job status (PUBLIC orchestrator).

    Calls INTERNAL diarization status function directly and returns combined status.
    """
    from backend.api.routers.transcription.internal.diarization.status import get_diarization_status

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
        audit_service.log_action(
            action="diarization_status_query_failed",
            user_id="system",
            resource=job_id,
            result="failure",
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get diarization status: {e!s}",
        ) from e


@router.get(
    "/sessions/{session_id}/diarization/segments",
    status_code=status.HTTP_200_OK,
)
async def get_diarization_segments_workflow(
    session_id: str,
    audit_service: DIAuditService = Depends(get_audit_service),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> dict[str, Any]:
    """Get diarization segments (PUBLIC orchestrator)."""
    validate_session_id(session_id)

    from backend.models.task_type import TaskType

    try:
        logger.info("DIARIZATION_SEGMENTS_GET_STARTED", session_id=session_id)

        metadata = task_repo.get_task_metadata(session_id, TaskType.DIARIZATION)
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

        segments = task_repo.get_diarization_segments(session_id)

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
        audit_service.log_action(
            action="diarization_segments_query_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"error": "segments_not_found"},
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        audit_service.log_action(
            action="diarization_segments_query_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"error": str(e)},
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
    audit_service: DIAuditService = Depends(get_audit_service),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> dict[str, Any]:
    """Update text of a diarization segment (PUBLIC orchestrator)."""

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

        # Get current segments
        segments = task_repo.get_diarization_segments(session_id)
        if not segments:
            raise ValueError(f"No diarization segments found for session {session_id}")

        if segment_index >= len(segments):
            raise ValueError(
                f"Segment index {segment_index} out of range (total segments: {len(segments)})"
            )

        # Update segment text
        segments[segment_index]["text"] = request.text

        # Save updated segments
        task_repo.save_diarization_segments(session_id, segments)

        updated_segment = segments[segment_index]

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
        audit_service.log_action(
            action="diarization_segment_update_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"segment_index": segment_index, "error": "segment_not_found"},
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        audit_service.log_action(
            action="diarization_segment_update_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"segment_index": segment_index, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update segment: {e!s}",
        ) from e


@router.post(
    "/sessions/{session_id}/diarization/import",
    status_code=status.HTTP_201_CREATED,
)
async def import_external_diarization(
    session_id: str,
    request: ImportDiarizationRequest,
    audit_service: DIAuditService = Depends(get_audit_service),
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> dict[str, Any]:
    """Import pre-diarized transcript from external service (e.g., Cue, AssemblyAI).

    This endpoint allows importing diarization results from external services that
    already performed speaker separation, avoiding the need to re-process audio.

    Use cases:
    - Cue.ai pre-diarized transcripts
    - AssemblyAI speaker diarization
    - Manual transcription with speaker labels
    - Any external service that provides speaker-separated text

    Args:
        session_id: Session identifier (must be valid UUID)
        request: Diarization data with segments, speakers, and metadata

    Returns:
        Success response with segment count and metadata
    """
    validate_session_id(session_id)

    from backend.models.task_type import TaskType

    try:
        logger.info(
            "EXTERNAL_DIARIZATION_IMPORT_STARTED",
            session_id=session_id,
            provider=request.provider,
            segment_count=len(request.segments),
        )

        # Convert Pydantic models to dict format expected by repository
        segments_dict = []
        speakers_dict = {}

        for segment in request.segments:
            # Build speaker dict (collect unique speakers)
            speaker_id = segment.speaker.speaker_id
            if speaker_id not in speakers_dict:
                speakers_dict[speaker_id] = {
                    "speaker_id": speaker_id,
                    "name": segment.speaker.name,
                    "confidence": segment.speaker.confidence,
                }

            # Build segment dict
            segment_dict = {
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "duration": segment.end_time - segment.start_time,
                "speaker": {
                    "speaker_id": speaker_id,
                    "name": segment.speaker.name,
                    "confidence": segment.speaker.confidence,
                },
                "text": segment.text,
                "confidence": segment.confidence,
            }
            segments_dict.append(segment_dict)

        # Calculate total duration (last segment end time)
        total_duration = max(seg.end_time for seg in request.segments) if request.segments else 0.0

        # Save segments via repository
        task_repo.save_diarization_segments(session_id, segments_dict)

        # Save task metadata
        metadata = {
            "status": "completed",
            "provider": request.provider,
            "num_speakers": len(speakers_dict),
            "segment_count": len(segments_dict),
            "duration_seconds": total_duration,
            "import_source": "external",
            "imported_at": datetime.now(UTC).isoformat(),
            **request.metadata,  # Merge user-provided metadata
        }
        task_repo.save_task_metadata(session_id, TaskType.DIARIZATION.name, metadata)

        logger.info(
            "EXTERNAL_DIARIZATION_IMPORT_SUCCESS",
            session_id=session_id,
            provider=request.provider,
            segment_count=len(segments_dict),
            num_speakers=len(speakers_dict),
            duration_seconds=total_duration,
        )

        return {
            "session_id": session_id,
            "status": "imported",
            "provider": request.provider,
            "segments_imported": len(segments_dict),
            "speakers_identified": len(speakers_dict),
            "duration_seconds": total_duration,
            "speakers": list(speakers_dict.values()),
            "imported_at": metadata["imported_at"],
            "message": f"Successfully imported {len(segments_dict)} segments from {request.provider}",
        }

    except HTTPException:
        raise
    except Exception as e:
        audit_service.log_action(
            action="external_diarization_import_failed",
            user_id="system",
            resource=session_id,
            result="failure",
            details={"provider": request.provider, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import external diarization: {e!s}",
        ) from e
