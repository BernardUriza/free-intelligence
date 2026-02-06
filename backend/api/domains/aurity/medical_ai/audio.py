"""Session audio retrieval endpoint.

Serves the full audio recording from a completed medical session.

Migrated from: backend/api/routers/session/public/sessions_pkg/audio.py
"""

from __future__ import annotations

import os
import tempfile

from backend.api.audit.dependencies import DIAuditService, get_audit_service
from backend.domain.session.dependencies import get_corpus_repository
from backend.infrastructure.auth import User, get_current_user, validate_session_access
from backend.repositories.interfaces.icorpus_repository import ICorpusRepository
from backend.utils.common.logging.logger import get_logger
from backend.validators import validate_session_id
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/sessions/{session_id}/audio",
    status_code=status.HTTP_200_OK,
)
async def get_session_audio_workflow(
    session_id: str,
    corpus_repo: ICorpusRepository = Depends(get_corpus_repository),
    audit_service: DIAuditService = Depends(get_audit_service),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Serve full audio file from completed session (PUBLIC endpoint)."""
    validate_session_id(session_id)
    validate_session_access(session_id, current_user, action="download session audio")

    temp_file_path = None
    try:
        logger.info("SESSION_AUDIO_GET_STARTED", session_id=session_id)

        # Get audio from corpus repository (injected via DI)
        audio_bytes = corpus_repo.get_session_audio(session_id, "tasks/TRANSCRIPTION/full_audio.webm")

        if audio_bytes is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Audio not found for session {session_id}. Session may not have been checkpointed yet."
                ),
            )

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
        # Audit failure for compliance tracking
        audit_service.log_action(
            action="session_audio_retrieved",
            user_id=current_user.id,
            resource=session_id,
            result="failure",
            details={"error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session audio: {e!s}",
        ) from e
