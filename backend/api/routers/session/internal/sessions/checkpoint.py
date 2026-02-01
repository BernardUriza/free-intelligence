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

Architecture: Uses Clean Architecture checkpoint service.
The endpoint is a thin adapter that translates HTTP to use case calls.

Author: Bernard Uriza Orozco
Created: 2025-11-14
Updated: 2025-12-11 - Refactored to Clean Architecture
"""

from datetime import UTC, datetime

from backend.domain.session.dependencies import get_task_repository
from backend.models.task_type import TaskType
from backend.repositories.interfaces.itask_repository import ITaskRepository
from backend.utils.common.logging.logger import get_logger
from backend.infrastructure.common.services.checkpoint import (
    CheckpointError,
    CheckpointRequest,
    NoChunksToProcessError,
    TooManyChunksError,
    create_checkpoint_service,
)
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

# ============================================================================
# DTOs (Pydantic models for FastAPI)
# ============================================================================


class CheckpointRequestDTO(BaseModel):
    """Request DTO for session checkpoint endpoint."""

    last_chunk_idx: int = Field(..., description="Last chunk index to include in checkpoint")


class CheckpointResponse(BaseModel):
    """Response for session checkpoint."""

    session_id: str = Field(..., description="Session identifier")
    checkpoint_at: str = Field(..., description="ISO timestamp")
    chunks_concatenated: int = Field(..., description="Number of chunks added")
    full_audio_size: int = Field(..., description="Total size of full_audio.webm in bytes")
    message: str = Field(..., description="Human-readable message")


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
async def checkpoint_session(
    session_id: str,
    request: CheckpointRequestDTO,
    task_repo: ITaskRepository = Depends(get_task_repository),
) -> CheckpointResponse:
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
        request: CheckpointRequestDTO with last_chunk_idx

    Returns:
        CheckpointResponse with concatenation status

    Raises:
        404: Session/task not found
        500: Concatenation failed
    """
    try:
        logger.info(
            "CHECKPOINT_ENDPOINT_CALLED",
            session_id=session_id,
            last_chunk_idx=request.last_chunk_idx,
        )

        # 1. Get task metadata to find last checkpoint (from injected repo)
        task_metadata = task_repo.get_task_metadata(session_id, TaskType.TRANSCRIPTION)

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

        # 2. Create service request (validates input)
        try:
            service_request = CheckpointRequest(
                session_id=session_id,
                last_checkpoint_idx=last_checkpoint_idx,
                new_checkpoint_idx=request.last_chunk_idx,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

        # 3. Execute checkpoint via clean architecture service
        service = create_checkpoint_service()
        result = service.execute(service_request)

        logger.info(
            "CHECKPOINT_COMPLETED",
            session_id=session_id,
            chunks_concatenated=result.chunks_concatenated,
            full_audio_size=len(result.audio_bytes),
            checkpoint_idx=request.last_chunk_idx,
        )

        return CheckpointResponse(
            session_id=session_id,
            checkpoint_at=datetime.now(UTC).isoformat(),
            chunks_concatenated=result.chunks_concatenated,
            full_audio_size=len(result.audio_bytes),
            message=f"Checkpoint created: {result.chunks_concatenated} chunks concatenated, {len(result.audio_bytes):,} bytes total",
        )

    except NoChunksToProcessError:
        return CheckpointResponse(
            session_id=session_id,
            checkpoint_at=datetime.now(UTC).isoformat(),
            chunks_concatenated=0,
            full_audio_size=0,
            message="No new chunks to concatenate",
        )
    except TooManyChunksError as e:
        logger.error(
            "CHECKPOINT_TOO_MANY_CHUNKS",
            session_id=session_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except CheckpointError as e:
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
    except Exception as e:
        logger.error(
            "CHECKPOINT_UNEXPECTED_ERROR",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Checkpoint failed: {e!s}",
        ) from e
