"""Service layer for diarization operations.

Handles audio file management and diarization job coordination.
Encapsulates business logic for processing audio files.

Clean Code: Separates concerns - service handles validation and
coordination, repositories handle storage, endpoints handle HTTP.
"""

from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc
from typing import Any, Optional
from uuid import uuid4

from backend.logger import get_logger

logger = get_logger(__name__)


class DiarizationService:
    """Service for diarization operations.

    Responsibilities:
    - Validate audio files
    - Create diarization jobs
    - Track job progress
    - Manage audio file storage
    - Coordinate with other services
    """

    # Configuration
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {"webm", "wav", "mp3", "m4a", "ogg", "flac"}
    DEFAULT_LANGUAGE = "es"

    def __init__(
        self, corpus_service: Optional[Any] = None, session_service: Optional[Any] = None
    ) -> None:
        """Initialize diarization service with dependencies.

        Args:
            corpus_service: CorpusService for document storage
            session_service: SessionService for session validation
        """
        self.corpus_service = corpus_service
        self.session_service = session_service
        self.active_jobs: dict[str, dict[str, Any]] = {}  # In-memory job tracking

    def validate_audio_file(
        self,
        filename: Optional[str],
        file_size: int,
    ) -> tuple[bool, Optional[str]]:
        """Validate audio file for diarization.

        Args:
            filename: Original filename
            file_size: Size of file in bytes

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate filename
        if not filename:
            return False, "Filename required (e.g., audio.mp3)"

        # Validate extension
        try:
            ext = filename.rsplit(".", 1)[-1].lower()
        except IndexError:
            return False, "File must have extension (e.g., .mp3)"

        if ext not in self.ALLOWED_EXTENSIONS:
            allowed = ", ".join(self.ALLOWED_EXTENSIONS)
            return False, f"Unsupported format. Allowed: {allowed}"

        # Validate file size
        if file_size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / 1024 / 1024
            return False, f"File too large. Max: {max_mb:.0f}MB"

        if file_size == 0:
            return False, "File is empty"

        return True, None

    def validate_session(self, session_id: str) -> tuple[bool, Optional[str]]:
        """Validate that session exists and is active.

        Args:
            session_id: Session identifier

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not session_id:
            return False, "X-Session-ID header required"

        if self.session_service:
            try:
                session = self.session_service.get_session(session_id)
                if not session:
                    return False, f"Session {session_id} not found"

                status = session.get("status", "unknown")
                if status == "deleted":
                    return False, f"Session {session_id} is deleted"

                return True, None
            except Exception as e:
                logger.error("SESSION_VALIDATION_FAILED", error=str(e))  # type: ignore[call-arg]
                return False, "Failed to validate session"

        return True, None

    def create_diarization_job(
        self,
        session_id: str,
        audio_filename: str,
        audio_content: bytes,
        language: str = DEFAULT_LANGUAGE,
        persist: bool = False,
        whisper_model: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create diarization job for audio file.

        Args:
            session_id: Parent session ID
            audio_filename: Original filename
            audio_content: Raw audio file bytes
            language: Language code (default: es)
            persist: Whether to save results to disk
            whisper_model: Whisper model to use

        Returns:
            Job metadata with job_id

        Raises:
            ValueError: If input validation fails
            IOError: If storage fails
        """
        # Validate audio file
        is_valid, error = self.validate_audio_file(audio_filename, len(audio_content))
        if not is_valid:
            raise ValueError(error or "Invalid audio file")

        # Validate session
        is_valid, error = self.validate_session(session_id)
        if not is_valid:
            raise ValueError(error or "Invalid session")

        # Validate language
        if not language or len(language) < 2:
            raise ValueError("Language code must be 2+ characters (e.g., 'es', 'en')")

        # Create job ID
        job_id = str(uuid4())

        # Save audio file to corpus
        if self.corpus_service:
            try:
                doc_id = self.corpus_service.create_document(
                    document_id=f"audio_{job_id}",
                    content=audio_content.decode("utf-8", errors="ignore"),
                    source="diarization_upload",
                    metadata={
                        "original_filename": audio_filename,
                        "job_id": job_id,
                        "session_id": session_id,
                    },
                )
            except OSError as e:
                logger.error("AUDIO_SAVE_FAILED", job_id=job_id, error=str(e))  # type: ignore[call-arg]
                raise OSError(f"Failed to save audio file: {e}") from e
        else:
            # Fallback if corpus_service not injected
            doc_id = f"audio_{job_id}"

        # Create job metadata
        job_metadata = {
            "job_id": job_id,
            "session_id": session_id,
            "document_id": doc_id,
            "filename": audio_filename,
            "status": "pending",
            "language": language,
            "persist": persist,
            "whisper_model": whisper_model,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "progress_pct": 0,
            "chunks_processed": 0,
            "total_chunks": 0,
        }

        # Store in memory (or database in production)
        self.active_jobs[job_id] = job_metadata

        logger.info(
            "DIARIZATION_JOB_CREATED",
            job_id=job_id,
            session_id=session_id,
            filename=audio_filename,
            language=language,
        )

        return job_metadata

    def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """Get diarization job status.

        Args:
            job_id: Job identifier

        Returns:
            Job metadata or None if not found
        """
        if job_id not in self.active_jobs:
            logger.warning("JOB_NOT_FOUND", job_id=job_id)  # type: ignore[call-arg]
            return None

        return self.active_jobs[job_id]

    def update_job_progress(
        self,
        job_id: str,
        progress_pct: int,
        chunks_processed: int = 0,
        total_chunks: int = 0,
        status: Optional[str] = None,
    ) -> bool:
        """Update diarization job progress.

        Args:
            job_id: Job identifier
            progress_pct: Progress percentage (0-100)
            chunks_processed: Chunks processed so far
            total_chunks: Total chunks to process
            status: New status if provided

        Returns:
            True if update successful
        """
        if job_id not in self.active_jobs:
            logger.error("JOB_NOT_FOUND_FOR_UPDATE", job_id=job_id)  # type: ignore[call-arg]
            return False

        job = self.active_jobs[job_id]
        job["progress_pct"] = max(0, min(100, progress_pct))
        job["chunks_processed"] = chunks_processed
        job["total_chunks"] = total_chunks
        job["updated_at"] = datetime.now(UTC).isoformat()

        if status:
            job["status"] = status

        logger.info(
            "JOB_PROGRESS_UPDATED",
            job_id=job_id,
            progress=progress_pct,
            chunks=chunks_processed,
        )

        return True

    def complete_job(
        self,
        job_id: str,
        result: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Mark job as completed.

        Args:
            job_id: Job identifier
            result: Final result data

        Returns:
            True if update successful
        """
        if job_id not in self.active_jobs:
            logger.error("JOB_NOT_FOUND_FOR_COMPLETION", job_id=job_id)  # type: ignore[call-arg]
            return False

        job = self.active_jobs[job_id]
        job["status"] = "completed"
        job["progress_pct"] = 100
        job["completed_at"] = datetime.now(UTC).isoformat()

        if result:
            job["result"] = result

        logger.info("DIARIZATION_JOB_COMPLETED", job_id=job_id)  # type: ignore[call-arg]
        return True

    def fail_job(
        self,
        job_id: str,
        error: Optional[str] = None,
    ) -> bool:
        """Mark job as failed.

        Args:
            job_id: Job identifier
            error: Error message

        Returns:
            True if update successful
        """
        if job_id not in self.active_jobs:
            logger.error("JOB_NOT_FOUND_FOR_FAILURE", job_id=job_id)  # type: ignore[call-arg]
            return False

        job = self.active_jobs[job_id]
        job["status"] = "failed"
        job["error"] = error
        job["failed_at"] = datetime.now(UTC).isoformat()

        logger.error("DIARIZATION_JOB_FAILED", job_id=job_id, error=error)  # type: ignore[call-arg]
        return True

    def list_jobs(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """List diarization jobs with optional filtering.

        Args:
            session_id: Filter by session ID
            status: Filter by status (pending, processing, completed, failed)
            limit: Maximum jobs to return

        Returns:
            List of job metadata
        """
        jobs = list(self.active_jobs.values())

        # Apply filters
        if session_id:
            jobs = [j for j in jobs if j.get("session_id") == session_id]

        if status:
            jobs = [j for j in jobs if j.get("status") == status]

        # Sort by created_at (newest first)
        jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)

        # Apply limit
        if limit:
            jobs = jobs[:limit]

        return jobs

    def health_check(self) -> dict[str, Any]:
        """Check diarization service health.

        Returns:
            Health status dict with status and details
        """
        health_details = {
            "service": "diarization",
            "status": "healthy",
            "components": {},
        }

        # Check Whisper availability
        try:
            import torch

            health_details["components"]["whisper"] = {
                "available": True,
                "model": "faster-whisper",
                "pytorch_available": torch.cuda.is_available(),
            }
        except ImportError:
            health_details["components"]["whisper"] = {
                "available": False,
                "reason": "faster-whisper not installed",
            }
            health_details["status"] = "degraded"
        except Exception as e:
            health_details["components"]["whisper"] = {
                "available": False,
                "reason": str(e),
            }
            health_details["status"] = "degraded"

        # Check FFmpeg availability
        try:
            import subprocess

            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=2)
            if result.returncode == 0:
                health_details["components"]["ffmpeg"] = {
                    "available": True,
                    "version": "installed",
                }
            else:
                health_details["components"]["ffmpeg"] = {
                    "available": False,
                    "reason": "ffmpeg command failed",
                }
                health_details["status"] = "degraded"
        except Exception as e:
            health_details["components"]["ffmpeg"] = {
                "available": False,
                "reason": str(e),
            }
            health_details["status"] = "degraded"

        # Check active jobs
        active_job_count = len(self.active_jobs)
        health_details["active_jobs"] = active_job_count

        logger.info("DIARIZATION_HEALTH_CHECK", status=health_details["status"])
        return health_details
