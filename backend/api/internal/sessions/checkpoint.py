"""Session checkpoint endpoint - INTERNAL layer.

Called by frontend on each PAUSE to incrementally concatenate audio chunks.

Flow:
1. Frontend pauses recording
2. POST /sessions/{session_id}/checkpoint { last_chunk_idx: N }
3. Backend concatenates chunks since last checkpoint
4. Appends to full_audio.webm (append-only)
5. Returns status

Benefits:
- Incremental concatenation (not just at end)
- Resilient (audio saved even if session interrupted)
- Distributed workload (small batches per pause)

Author: Bernard Uriza Orozco
Created: 2025-11-14
"""

from datetime import UTC, datetime
from fastapi import APIRouter, HTTPException, status

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.storage.task_repository import add_full_audio, get_task_metadata, update_task_metadata

from .checkpoint_logic import perform_checkpoint_concatenation
from .checkpoint_models import CheckpointRequest, CheckpointResponse

logger = get_logger(__name__)

router = APIRouter(tags=["internal-sessions"])


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/sessions/{session_id}/checkpoint",
    response_model=CheckpointResponse,
    status_code=status.HTTP_200_OK,
)
async def checkpoint_session(session_id: str, request: CheckpointRequest) -> CheckpointResponse:
    """Create checkpoint: concatenate audio chunks incrementally.

    Called by frontend on each PAUSE. Concatenates audio chunks since last
    checkpoint and appends to full_audio.webm (append-only).

    Flow:
    1. Get last checkpoint index from task metadata
    2. Concatenate chunks from last_checkpoint+1 to request.last_chunk_idx
    3. Append to existing full_audio.webm (or create if first checkpoint)
    4. Update task metadata with new checkpoint
    5. Return status

    Args:
        session_id: Session UUID
        request: CheckpointRequest with last_chunk_idx

    Returns:
        CheckpointResponse with concatenation status

    Raises:
        404: Session/task not found
        500: Concatenation failed
    """
    try:
        logger.info(
            "CHECKPOINT_STARTED",
            session_id=session_id,
            last_chunk_idx=request.last_chunk_idx,
        )

        # 1. Get task metadata to find last checkpoint
        task_metadata = get_task_metadata(session_id, TaskType.TRANSCRIPTION)

        if not task_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"TRANSCRIPTION task not found for session {session_id}",
            )

        last_checkpoint_idx = task_metadata.get("last_checkpoint_idx", -1)

        logger.info(
            "CHECKPOINT_RANGE",
            session_id=session_id,
            last_checkpoint=last_checkpoint_idx,
            new_checkpoint=request.last_chunk_idx,
        )

        # 2. Perform concatenation
        chunks_concatenated, full_audio_bytes = perform_checkpoint_concatenation(
            session_id=session_id,
            last_checkpoint_idx=last_checkpoint_idx,
            new_checkpoint_idx=request.last_chunk_idx,
        )

        if chunks_concatenated == 0:
            return CheckpointResponse(
                session_id=session_id,
                checkpoint_at=datetime.now(UTC).isoformat(),
                chunks_concatenated=0,
                full_audio_size=0,
                message="No new chunks to concatenate",
            )

        # 3. Save to HDF5 (overwrites full_audio.webm with new concatenated version)
        add_full_audio(
            session_id=session_id,
            audio_bytes=full_audio_bytes,
            filename="full_audio.webm",
            task_type=TaskType.TRANSCRIPTION,
        )

        # 4. Update task metadata with new checkpoint
        task_metadata["last_checkpoint_idx"] = request.last_chunk_idx
        task_metadata["last_checkpoint_at"] = datetime.now(UTC).isoformat()
        update_task_metadata(session_id, TaskType.TRANSCRIPTION, task_metadata)

        logger.info(
            "CHECKPOINT_COMPLETED",
            session_id=session_id,
            chunks_concatenated=chunks_concatenated,
            full_audio_size=len(full_audio_bytes),
            checkpoint_idx=request.last_chunk_idx,
        )

        return CheckpointResponse(
            session_id=session_id,
            checkpoint_at=datetime.now(UTC).isoformat(),
            chunks_concatenated=chunks_concatenated,
            full_audio_size=len(full_audio_bytes),
            message=f"Checkpoint created: {chunks_concatenated} chunks concatenated, {len(full_audio_bytes):,} bytes total",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "CHECKPOINT_FAILED",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Checkpoint failed: {e!s}",
        ) from e
