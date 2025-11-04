"""Service layer for diarization job management.

Handles job status retrieval, result reconstruction, export formatting,
job state transitions, and log retrieval.

Clean Code: This service layer encapsulates all diarization job logic,
making endpoints thin controllers focused only on HTTP concerns.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from backend.diarization_jobs import get_job
from backend.diarization_service import diarize_audio
from backend.diarization_service import export_diarization as export_to_format
from backend.diarization_worker_lowprio import get_job_status as get_lowprio_status
from backend.logger import get_logger

logger = get_logger(__name__)


class DiarizationJobService:
    """Service for diarization job management.

    Orchestrates job status retrieval, result processing, export formatting,
    and job state transitions (restart, cancel).

    Supports both:
    - Low-priority worker (HDF5-backed)
    - Legacy in-memory job store
    """

    def __init__(self, use_lowprio: bool = True):
        """Initialize service.

        Args:
            use_lowprio: Use low-priority worker (HDF5) vs legacy in-memory
        """
        self.use_lowprio = use_lowprio
        logger.info(f"DiarizationJobService initialized with use_lowprio={use_lowprio}")

    def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """Get job status with chunks array.

        Args:
            job_id: Job identifier

        Returns:
            Job status dict with chunks, or None if not found

        Raises:
            ValueError: If job_id format is invalid
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")

        try:
            # Try low-priority worker first (HDF5)
            if self.use_lowprio:
                lowprio_status = get_lowprio_status(job_id)
                if lowprio_status:
                    logger.info(f"JOB_STATUS_FROM_LOWPRIO: job_id={job_id}")
                    return {
                        "job_id": lowprio_status["job_id"],
                        "session_id": lowprio_status["session_id"],
                        "status": lowprio_status["status"],
                        "progress_pct": lowprio_status["progress_pct"],
                        "total_chunks": lowprio_status["total_chunks"],
                        "processed_chunks": lowprio_status["processed_chunks"],
                        "chunks": lowprio_status["chunks"],
                        "created_at": lowprio_status["created_at"],
                        "updated_at": lowprio_status["updated_at"],
                        "error": lowprio_status.get("error"),
                    }

            # Fallback to legacy in-memory job store
            job = get_job(job_id)
            if not job:
                logger.warning(f"JOB_NOT_FOUND: job_id={job_id}")
                return None

            logger.info(f"JOB_STATUS_FROM_LEGACY: job_id={job_id}")
            return {
                "job_id": job.job_id,
                "session_id": job.session_id,
                "status": job.status.value,
                "progress_pct": job.progress_percent,
                "total_chunks": job.total,
                "processed_chunks": job.processed,
                "chunks": [],  # Legacy mode: no incremental chunks
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "error": job.error_message,
            }

        except Exception as e:
            logger.error(f"JOB_STATUS_RETRIEVAL_FAILED: job_id={job_id}, error={str(e)}")
            raise

    def get_diarization_result(
        self, job_id: str, reprocess_if_not_cached: bool = True
    ) -> Optional[dict[str, Any]]:
        """Get diarization result for completed job.

        Reconstructs result from chunks or cached result.

        Args:
            job_id: Job identifier
            reprocess_if_not_cached: Reprocess job if result not cached (V1 fallback)

        Returns:
            Diarization result dict with segments, or None if job not completed

        Raises:
            ValueError: If job not found or not completed
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")

        try:
            # Try low-priority worker first (HDF5)
            if self.use_lowprio:
                lowprio_status = get_lowprio_status(job_id)
                if lowprio_status:
                    if lowprio_status["status"] != "completed":
                        raise ValueError(f"Job not completed. Status: {lowprio_status['status']}")

                    # Reconstruct result from chunks
                    logger.info(
                        f"RESULT_FROM_LOWPRIO_CHUNKS: job_id={job_id}, "
                        + f"chunks={len(lowprio_status['chunks'])}"
                    )

                    segments = [
                        {
                            "start_time": chunk["start_time"],
                            "end_time": chunk["end_time"],
                            "speaker": chunk["speaker"],
                            "text": chunk["text"],
                        }
                        for chunk in lowprio_status["chunks"]
                    ]

                    # Compute total duration from last chunk
                    total_duration = segments[-1]["end_time"] if segments else 0.0

                    return {
                        "session_id": lowprio_status["session_id"],
                        "audio_file_hash": "",
                        "duration_sec": total_duration,
                        "language": "es",  # Default
                        "model_asr": "faster-whisper",
                        "model_llm": "none",
                        "segments": segments,
                        "processing_time_sec": 0.0,
                        "created_at": lowprio_status["created_at"],
                    }

            # Fallback to legacy in-memory job store
            job = get_job(job_id)
            if not job:
                logger.warning(f"DIARIZATION_RESULT_NOT_FOUND: job_id={job_id}")
                raise ValueError(f"Job {job_id} not found")

            if job.status.value != "completed":
                raise ValueError(f"Job not completed. Status: {job.status.value}")

            # Use cached result (V2) or re-process (V1 fallback)
            if job.result_data:
                logger.info(f"RESULT_SERVED_FROM_CACHE: job_id={job_id}")
                return {
                    "session_id": job.result_data["session_id"],
                    "audio_file_hash": job.result_data["audio_file_hash"],
                    "duration_sec": job.result_data["duration_sec"],
                    "language": job.result_data["language"],
                    "model_asr": job.result_data["model_asr"],
                    "model_llm": job.result_data["model_llm"],
                    "segments": job.result_data["segments"],
                    "processing_time_sec": job.result_data["processing_time_sec"],
                    "created_at": job.result_data["created_at"],
                }

            # V1 fallback: Re-run diarization (expensive)
            if reprocess_if_not_cached:
                logger.warning(f"RESULT_NOT_CACHED_REPROCESSING: job_id={job_id}")
                audio_path = Path(job.audio_file_path)
                result = diarize_audio(audio_path, job.session_id, language="es", persist=False)

                return {
                    "session_id": result.session_id,
                    "audio_file_hash": result.audio_file_hash,
                    "duration_sec": result.duration_sec,
                    "language": result.language,
                    "model_asr": result.model_asr,
                    "model_llm": result.model_llm,
                    "segments": [
                        {
                            "start_time": seg.start_time,
                            "end_time": seg.end_time,
                            "speaker": seg.speaker,
                            "text": seg.text,
                        }
                        for seg in result.segments
                    ],
                    "processing_time_sec": result.processing_time_sec,
                    "created_at": result.created_at,
                }
            else:
                raise ValueError("Result not cached and reprocessing disabled")

        except Exception as e:
            logger.error(f"DIARIZATION_RESULT_FAILED: job_id={job_id}, error={str(e)}")
            raise

    def export_result(self, job_id: str, format: str = "json") -> Optional[str]:
        """Export diarization result in specified format.

        Args:
            job_id: Job identifier
            format: Export format (json, markdown, vtt, srt, csv)

        Returns:
            Exported content as string

        Raises:
            ValueError: If job not found/completed or invalid format
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")

        if format not in ["json", "markdown", "vtt", "srt", "csv"]:
            raise ValueError(
                f"Invalid format: {format}. Must be one of: json, markdown, vtt, srt, csv"
            )

        try:
            # Get result first
            result = self.get_diarization_result(job_id)
            if not result:
                raise ValueError(f"Result not found for job {job_id}")

            logger.info(f"EXPORTING_DIARIZATION: job_id={job_id}, format={format}")

            # Use existing export function (backend/diarization_service.py)
            # This function handles format conversion
            from pathlib import Path

            # Try to find audio file
            job = get_job(job_id)
            audio_path = None
            if job:
                audio_path = Path(job.audio_file_path)

            exported = export_to_format(
                result=result,
                format=format,
                audio_path=audio_path,
                job_id=job_id,
            )

            logger.info(
                f"DIARIZATION_EXPORTED: job_id={job_id}, format={format}, size={len(exported)}"
            )
            return exported

        except Exception as e:
            logger.error(
                f"DIARIZATION_EXPORT_FAILED: job_id={job_id}, format={format}, error={str(e)}"
            )
            raise

    def restart_job(self, job_id: str) -> dict[str, Any]:
        """Restart diarization job.

        Args:
            job_id: Job identifier

        Returns:
            Updated job status dict

        Raises:
            ValueError: If job not found
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")

        try:
            if self.use_lowprio:
                # Get current job to retrieve audio path
                lowprio_status = get_lowprio_status(job_id)
                if not lowprio_status:
                    raise ValueError(f"Job {job_id} not found")

                # For now, return a placeholder response
                # In production, this would queue a restart
                logger.info(f"JOB_RESTARTED: job_id={job_id}")
                return {
                    "job_id": job_id,
                    "session_id": lowprio_status.get("session_id"),
                    "status": "pending",
                }

            # Legacy mode: not implemented
            raise ValueError("Job restart not supported in legacy mode")

        except Exception as e:
            logger.error(f"JOB_RESTART_FAILED: job_id={job_id}, error={str(e)}")
            raise

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Cancel diarization job.

        Args:
            job_id: Job identifier

        Returns:
            Updated job status dict

        Raises:
            ValueError: If job not found
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")

        try:
            if self.use_lowprio:
                # Get current job to verify it exists
                lowprio_status = get_lowprio_status(job_id)
                if not lowprio_status:
                    raise ValueError(f"Job {job_id} not found")

                # For now, return a placeholder response
                # In production, this would mark the job as cancelled
                logger.info(f"JOB_CANCELLED: job_id={job_id}")
                return {
                    "job_id": job_id,
                    "session_id": lowprio_status.get("session_id"),
                    "status": "cancelled",
                }

            # Legacy mode: not implemented
            raise ValueError("Job cancel not supported in legacy mode")

        except Exception as e:
            logger.error(f"JOB_CANCEL_FAILED: job_id={job_id}, error={str(e)}")
            raise

    def get_job_logs(self, job_id: str) -> Optional[list[dict[str, Any]]]:
        """Get job processing logs.

        Args:
            job_id: Job identifier

        Returns:
            List of log entries, or None if job not found
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")

        try:
            if self.use_lowprio:
                lowprio_status = get_lowprio_status(job_id)
                if lowprio_status:
                    # Extract logs if available
                    logs = lowprio_status.get("logs", [])
                    logger.info(f"JOB_LOGS_FROM_LOWPRIO: job_id={job_id}, count={len(logs)}")
                    return logs

            # Legacy mode: try to get from job
            job = get_job(job_id)
            if not job:
                logger.warning(f"JOB_LOGS_NOT_FOUND: job_id={job_id}")
                return None

            # Return empty list (legacy doesn't track logs)
            logger.info(f"JOB_LOGS_FROM_LEGACY: job_id={job_id}")
            return []

        except Exception as e:
            logger.error(f"JOB_LOGS_RETRIEVAL_FAILED: job_id={job_id}, error={str(e)}")
            raise

    def list_jobs(self, limit: int = 100, session_id: Optional[str] = None) -> list[dict[str, Any]]:
        """List diarization jobs.

        Args:
            limit: Maximum number of jobs to return
            session_id: Filter by session ID (optional)

        Returns:
            List of job status dicts
        """
        try:
            if self.use_lowprio:
                from backend.diarization_worker_lowprio import (
                    list_all_jobs as list_lowprio_jobs,
                )

                jobs = list_lowprio_jobs(limit=limit, session_id=session_id)
                logger.info(f"JOBS_LISTED_FROM_LOWPRIO: count={len(jobs)}, limit={limit}")
                return jobs

            # Legacy mode: list in-memory jobs
            from backend.diarization_jobs import list_jobs as list_legacy_jobs

            jobs = list_legacy_jobs(limit=limit, session_id=session_id)
            logger.info(f"JOBS_LISTED_FROM_LEGACY: count={len(jobs)}, limit={limit}")
            return jobs

        except Exception as e:
            logger.error(f"JOBS_LIST_FAILED: error={str(e)}")
            raise
