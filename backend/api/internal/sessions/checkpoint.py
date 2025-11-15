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

from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.logger import get_logger
from backend.models.task_type import TaskType
from backend.storage.task_repository import (
    CORPUS_PATH,
    add_full_audio,
    get_task_metadata,
    update_task_metadata,
)

logger = get_logger(__name__)

router = APIRouter(tags=["internal-sessions"])


# ============================================================================
# Request/Response Models
# ============================================================================


class CheckpointRequest(BaseModel):
    """Request for session checkpoint."""

    last_chunk_idx: int = Field(..., description="Last chunk index to include in checkpoint")


class CheckpointResponse(BaseModel):
    """Response for session checkpoint."""

    session_id: str = Field(..., description="Session identifier")
    checkpoint_at: str = Field(..., description="ISO timestamp")
    chunks_concatenated: int = Field(..., description="Number of chunks added")
    full_audio_size: int = Field(..., description="Total size of full_audio.webm in bytes")
    message: str = Field(..., description="Human-readable message")


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

        # 2. Read chunks in range (last_checkpoint+1 to request.last_chunk_idx)
        import h5py

        temp_dir = Path(tempfile.mkdtemp(prefix="checkpoint_"))
        audio_files = []
        chunks_concatenated = 0

        with h5py.File(CORPUS_PATH, "r") as f:
            for chunk_idx in range(last_checkpoint_idx + 1, request.last_chunk_idx + 1):
                chunk_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/chunks/chunk_{chunk_idx}"

                if chunk_path in f:
                    chunk_group = f[chunk_path]

                    # Check if audio exists and is not empty
                    if "audio.webm" in chunk_group:
                        audio_data = chunk_group["audio.webm"][()]
                        audio_bytes = (
                            bytes(audio_data) if hasattr(audio_data, "__iter__") else audio_data
                        )

                        # Skip empty audio files
                        if len(audio_bytes) == 0:
                            logger.warning(
                                "CHUNK_AUDIO_EMPTY",
                                session_id=session_id,
                                chunk_idx=chunk_idx,
                            )
                            continue

                        # Save to temp file
                        temp_audio = temp_dir / f"chunk_{chunk_idx:03d}.webm"
                        temp_audio.write_bytes(audio_bytes)
                        audio_files.append(temp_audio)
                        chunks_concatenated += 1
                    else:
                        logger.warning(
                            "CHUNK_NO_AUDIO",
                            session_id=session_id,
                            chunk_idx=chunk_idx,
                        )
                else:
                    logger.warning(
                        "CHUNK_NOT_FOUND",
                        session_id=session_id,
                        chunk_idx=chunk_idx,
                    )

        if not audio_files:
            logger.warning(
                "NO_NEW_CHUNKS_TO_CONCATENATE",
                session_id=session_id,
                range=f"{last_checkpoint_idx+1} to {request.last_chunk_idx}",
            )
            return CheckpointResponse(
                session_id=session_id,
                checkpoint_at=datetime.now(timezone.utc).isoformat(),
                chunks_concatenated=0,
                full_audio_size=0,
                message="No new chunks to concatenate",
            )

        # 3. Check if full_audio.webm exists (read from HDF5)
        existing_audio_bytes = None
        with h5py.File(CORPUS_PATH, "r") as f:
            full_audio_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/full_audio.webm"
            if full_audio_path in f:
                existing_audio_bytes = f[full_audio_path][()]
                logger.info(
                    "EXISTING_AUDIO_FOUND",
                    session_id=session_id,
                    size_bytes=len(existing_audio_bytes),
                )

        # 4. Concatenate: existing + new chunks
        concat_list_files = []

        if existing_audio_bytes:
            # Save existing audio to temp
            existing_audio_file = temp_dir / "existing_audio.webm"
            existing_audio_file.write_bytes(existing_audio_bytes)
            concat_list_files.append(existing_audio_file)

        concat_list_files.extend(audio_files)

        # Create ffmpeg concat file list
        concat_list = temp_dir / "concat_list.txt"
        with open(concat_list, "w") as f:
            for audio_file in concat_list_files:
                f.write(f"file '{audio_file}'\n")

        # Concatenate using ffmpeg (re-encode to WebM/Opus for consistency)
        output_file = temp_dir / "full_audio_new.webm"
        ffmpeg_cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c:a",
            "libopus",  # Encode to Opus codec (WebM standard)
            "-b:a",
            "128k",  # 128 kbps bitrate
            str(output_file),
            "-loglevel",
            "error",
            "-y",
        ]

        subprocess.run(ffmpeg_cmd, check=True, timeout=60)

        # Read concatenated audio
        full_audio_bytes = output_file.read_bytes()

        # 5. Save to HDF5 (overwrites full_audio.webm with new concatenated version)
        add_full_audio(
            session_id=session_id,
            audio_bytes=full_audio_bytes,
            filename="full_audio.webm",
            task_type=TaskType.TRANSCRIPTION,
        )

        # 6. Update task metadata with new checkpoint
        task_metadata["last_checkpoint_idx"] = request.last_chunk_idx
        task_metadata["last_checkpoint_at"] = datetime.now(timezone.utc).isoformat()
        update_task_metadata(session_id, TaskType.TRANSCRIPTION, task_metadata)

        # Cleanup temp files
        shutil.rmtree(temp_dir)

        # 7. Launch full_transcription task (transcribe complete audio)
        import os

        from backend.workers.transcription_tasks import transcribe_full_audio_task

        stt_provider = os.environ.get("AURITY_ASR_PROVIDER", "faster_whisper")
        full_transcription_task = transcribe_full_audio_task.delay(
            session_id=session_id, stt_provider=stt_provider
        )

        logger.info(
            "CHECKPOINT_COMPLETED",
            session_id=session_id,
            chunks_concatenated=chunks_concatenated,
            full_audio_size=len(full_audio_bytes),
            checkpoint_idx=request.last_chunk_idx,
            full_transcription_task_id=full_transcription_task.id,
        )

        return CheckpointResponse(
            session_id=session_id,
            checkpoint_at=datetime.now(timezone.utc).isoformat(),
            chunks_concatenated=chunks_concatenated,
            full_audio_size=len(full_audio_bytes),
            message=f"Checkpoint created: {chunks_concatenated} chunks + full_transcription task {full_transcription_task.id}",
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
