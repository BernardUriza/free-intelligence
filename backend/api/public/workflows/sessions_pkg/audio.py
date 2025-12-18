from __future__ import annotations

import os
import tempfile

import h5py
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from backend.logger import get_logger
from backend.validators import validate_session_id

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/sessions/{session_id}/audio",
    status_code=status.HTTP_200_OK,
)
async def get_session_audio_workflow(session_id: str) -> FileResponse:
    """Serve full audio file from completed session (PUBLIC endpoint)."""
    validate_session_id(session_id)

    from backend.packages.fi_storage.infrastructure.hdf5.task_repository import CORPUS_PATH

    temp_file_path = None
    try:
        logger.info("SESSION_AUDIO_GET_STARTED", session_id=session_id)

        with h5py.File(CORPUS_PATH, "r") as f:
            full_audio_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/full_audio.webm"
            if full_audio_path not in f:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        f"Audio not found for session {session_id}. Session may not have been checkpointed yet."
                    ),
                )

            audio_data = f[full_audio_path][()]
            if hasattr(audio_data, "tobytes"):
                audio_bytes = audio_data.tobytes()
            elif isinstance(audio_data, bytes):
                audio_bytes = audio_data
            else:
                audio_bytes = bytes(audio_data)

            if len(audio_bytes) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Audio file is empty for session {session_id}",
                )

        try:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".webm", prefix=f"session_{session_id}_"
            ) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            logger.info(
                "SESSION_AUDIO_GET_SUCCESS",
                session_id=session_id,
                audio_size_bytes=len(audio_bytes),
                temp_file_path=temp_file_path,
            )

            import atexit

            def cleanup_temp_file():
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                        logger.debug("TEMP_FILE_CLEANUP_ATEXIT", path=temp_file_path)
                    except Exception as e:
                        logger.warning(
                            "TEMP_FILE_CLEANUP_ATEXIT_FAILED", path=temp_file_path, error=str(e)
                        )

            atexit.register(cleanup_temp_file)

            return FileResponse(
                path=temp_file_path,
                media_type="audio/webm",
                filename=f"session_{session_id}.webm",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                },
                background=BackgroundTask(cleanup_temp_file),
            )

        except Exception:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    logger.warning(
                        "TEMP_FILE_CLEANUP_ON_ERROR_FAILED",
                        path=temp_file_path,
                        error=str(cleanup_error),
                    )
            raise

    except HTTPException:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as cleanup_error:
                logger.warning(
                    "TEMP_FILE_CLEANUP_FAILED",
                    temp_file=temp_file_path,
                    error=str(cleanup_error),
                )
        raise
    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as cleanup_error:
                logger.warning(
                    "TEMP_FILE_CLEANUP_FAILED",
                    temp_file=temp_file_path,
                    error=str(cleanup_error),
                )
        logger.error("SESSION_AUDIO_GET_FAILED", session_id=session_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session audio: {e!s}",
        ) from e
