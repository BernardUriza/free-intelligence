"""Celery Background Tasks.

Card: FI-BACKEND-ARCH-001 (TODO #1) + AUR-PROMPT-4.2

Provides asynchronous task processing for:
- Diarization job processing (transcription + speaker separation)
- SOAP generation (LLM-based medical note extraction)
- Chunk transcription + HDF5 append (NEW: AUR-PROMPT-4.2)

Features:
- Automatic retries with exponential backoff
- Task status tracking
- Error handling and logging
- Graceful degradation
- HDF5 append-only corpus operations

File: backend/workers/tasks.py
Created: 2025-11-09
Updated: 2025-11-09 (added transcribe_chunk_task)
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from celery.exceptions import SoftTimeLimitExceeded

from backend.container import get_container
from backend.logger import get_logger
from backend.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, name="process_diarization_job", max_retries=3)
def process_diarization_job(self, job_id: str) -> dict:
    """
    Process diarization job asynchronously.

    **Workflow:**
    1. Get TranscriptionService and DiarizationService
    2. Call process_job (transcription + diarization)
    3. Handle errors with exponential backoff retry

    **Args:**
        job_id: Unique job identifier

    **Returns:**
        dict with:
            - job_id: str
            - status: str (completed, failed)
            - message: str

    **Raises:**
        Exception: Triggers automatic retry (max 3 attempts)

    **Retry Strategy:**
        - Retry 1: 60s delay
        - Retry 2: 120s delay (2^1 * 60)
        - Retry 3: 240s delay (2^2 * 60)
    """
    try:
        logger.info("CELERY_JOB_STARTED", job_id=job_id, task_id=self.request.id)

        # Get services from DI container
        from backend.services.diarization.worker import process_job
        from backend.services.transcription.service import TranscriptionService

        transcription_svc = TranscriptionService()
        diarization_svc = get_container().get_diarization_service()

        # Process job (blocking operation)
        process_job(job_id, transcription_svc, diarization_svc)

        logger.info(
            "CELERY_JOB_COMPLETED",
            job_id=job_id,
            task_id=self.request.id,
        )

        return {
            "job_id": job_id,
            "status": "completed",
            "message": "Diarization job completed successfully",
        }

    except SoftTimeLimitExceeded:
        logger.error(
            "CELERY_JOB_TIMEOUT",
            job_id=job_id,
            task_id=self.request.id,
            timeout_sec=540,
        )
        # Don't retry on timeout (likely system overload)
        return {
            "job_id": job_id,
            "status": "failed",
            "message": "Job timeout (9 minutes) - System may be overloaded",
        }

    except Exception as exc:
        logger.error(
            "CELERY_JOB_FAILED",
            job_id=job_id,
            task_id=self.request.id,
            error=str(exc),
            retry_count=self.request.retries,
        )

        # Retry with exponential backoff
        countdown = 60 * (2**self.request.retries)

        # If max retries reached, don't retry
        if self.request.retries >= self.max_retries:
            logger.error(
                "CELERY_JOB_MAX_RETRIES",
                job_id=job_id,
                task_id=self.request.id,
                max_retries=self.max_retries,
            )
            return {
                "job_id": job_id,
                "status": "failed",
                "message": f"Job failed after {self.max_retries} retries: {exc!s}",
            }

        # Retry
        logger.warning(
            "CELERY_JOB_RETRY",
            job_id=job_id,
            task_id=self.request.id,
            retry_count=self.request.retries + 1,
            countdown_sec=countdown,
        )

        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, name="generate_soap_note", max_retries=2)
def generate_soap_note(self, job_id: str, result_data: dict) -> dict:
    """
    Generate SOAP note asynchronously (optional separate task).

    **Note:** Currently SOAP generation is handled inline in the workflow router
    with threading. This task is provided for future migration to fully async.

    **Workflow:**
    1. Extract transcription text from result_data
    2. Call Ollama LLM to extract SOAP sections
    3. Calculate completeness score
    4. Update job with SOAP note

    **Args:**
        job_id: Unique job identifier
        result_data: Job result data with transcription

    **Returns:**
        dict with:
            - job_id: str
            - status: str (completed, failed)
            - soap_note: dict (if successful)

    **Retry Strategy:**
        - Retry 1: 30s delay
        - Retry 2: 60s delay (2^1 * 30)
    """
    try:
        logger.info("CELERY_SOAP_STARTED", job_id=job_id, task_id=self.request.id)

        from backend.services.diarization.jobs import update_job
        from backend.services.soap_generation.completeness import CompletenessCalculator
        from backend.services.soap_generation.ollama_client import OllamaClient
        from backend.services.soap_generation.soap_builder import SOAPBuilder

        # Extract transcription text
        transcription_text = ""
        if result_data.get("diarization", {}).get("segments"):
            segments = result_data["diarization"]["segments"]
            transcription_text = " ".join(
                seg.get("improved_text") or seg.get("text", "") for seg in segments
            )

        if not transcription_text:
            transcription_text = result_data.get("transcription", {}).get("text", "")

        if not transcription_text:
            raise ValueError("No transcription text available for SOAP generation")

        # Extract SOAP via Ollama
        ollama_client = OllamaClient(model="qwen2.5:7b-instruct-q4_0")
        soap_data = ollama_client.extract_soap(transcription_text)

        # Build SOAP models
        subjetivo, objetivo, analisis, plan = SOAPBuilder.build(job_id, soap_data)
        completeness = CompletenessCalculator.calculate(subjetivo, objetivo, analisis, plan)
        soap_obj = SOAPBuilder.build_note(job_id, subjetivo, objetivo, analisis, plan, completeness)

        # Update job with SOAP note
        updated_result = result_data.copy()
        updated_result["soap_note"] = soap_obj.model_dump(mode="json")
        updated_result["soap_status"] = "completed"
        update_job(job_id, result_data=updated_result)

        logger.info(
            "CELERY_SOAP_COMPLETED",
            job_id=job_id,
            task_id=self.request.id,
            completeness=completeness,
        )

        return {
            "job_id": job_id,
            "status": "completed",
            "soap_note": updated_result["soap_note"],
        }

    except SoftTimeLimitExceeded:
        logger.error(
            "CELERY_SOAP_TIMEOUT",
            job_id=job_id,
            task_id=self.request.id,
            timeout_sec=540,
        )
        return {
            "job_id": job_id,
            "status": "failed",
            "message": "SOAP generation timeout",
        }

    except Exception as exc:
        logger.error(
            "CELERY_SOAP_FAILED",
            job_id=job_id,
            task_id=self.request.id,
            error=str(exc),
            retry_count=self.request.retries,
        )

        # Retry with exponential backoff
        countdown = 30 * (2**self.request.retries)

        if self.request.retries >= self.max_retries:
            # Update job with failure status
            from backend.services.diarization.jobs import update_job

            updated_result = result_data.copy()
            updated_result["soap_status"] = "failed"
            updated_result["soap_error"] = str(exc)
            update_job(job_id, result_data=updated_result)

            logger.error(
                "CELERY_SOAP_MAX_RETRIES",
                job_id=job_id,
                task_id=self.request.id,
                max_retries=self.max_retries,
            )
            return {
                "job_id": job_id,
                "status": "failed",
                "message": f"SOAP generation failed after {self.max_retries} retries",
            }

        logger.warning(
            "CELERY_SOAP_RETRY",
            job_id=job_id,
            task_id=self.request.id,
            retry_count=self.request.retries + 1,
            countdown_sec=countdown,
        )

        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(bind=True, name="transcribe_chunk_task", max_retries=2)
def transcribe_chunk_task(
    self,
    session_id: str,
    chunk_number: int,
    audio_path: str,
    audio_hash: str,
    content_type: str,
) -> dict:
    """
    Transcribe audio chunk and append to HDF5 corpus.

    **Card: AUR-PROMPT-4.2**
    **Architecture: WORKER layer**

    **Workflow:**
    1. Convert audio to WAV (if needed) via ffmpeg
    2. Transcribe with faster-whisper (TranscriptionService)
    3. Append to HDF5: /sessions/{session_id}/chunks/{chunk_idx}
    4. Return result with transcript + metadata

    **Args:**
        session_id: Session identifier
        chunk_number: Chunk index (0-based)
        audio_path: Filesystem path to audio chunk
        audio_hash: SHA256 hash for integrity
        content_type: MIME type (audio/webm, audio/mp4, audio/wav)

    **Returns:**
        dict with:
            - session_id: str
            - chunk_number: int
            - transcript: str (full text)
            - audio_hash: str (SHA256)
            - duration: float (seconds)
            - language: str (detected)
            - hdf5_path: str (corpus location)
            - timestamps: dict (start, end)

    **Raises:**
        Exception: Triggers automatic retry (max 2 attempts)

    **Retry Strategy:**
        - Retry 1: 30s delay
        - Retry 2: 60s delay (2^1 * 30)
    """
    try:
        logger.info(
            "CHUNK_TASK_STARTED",
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=self.request.id,
            audio_hash=audio_hash[:16],
        )

        # Step 1: WebM Header Graft (AUR-PROMPT-3.4)
        # RecordRTC chunks > 0 lack EBML header → graft from chunk 0
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        candidate = audio_file
        enable_graft = os.getenv("AURITY_ENABLE_WEBM_GRAFT", "true").lower() in {
            "1",
            "true",
            "yes",
        }

        try:
            if enable_graft and audio_file.suffix.lower() == ".webm" and chunk_number > 0:
                from backend.workers.webm_graft import (
                    ensure_session_header,
                    graft_header,
                    is_ebml,
                )

                if not is_ebml(audio_file):
                    logger.info(
                        "CHUNK_GRAFT_NEEDED",
                        session_id=session_id,
                        chunk_number=chunk_number,
                        audio_file=str(audio_file),
                    )
                    header = ensure_session_header(audio_file.parent)
                    candidate = graft_header(audio_file, header)
                    logger.info(
                        "CHUNK_GRAFT_SUCCESS",
                        session_id=session_id,
                        chunk_number=chunk_number,
                        grafted=str(candidate),
                    )
        except Exception as e:
            # Non-fatal: attempt decode anyway
            logger.warning(
                "CHUNK_GRAFT_SKIP",
                session_id=session_id,
                chunk_number=chunk_number,
                error=str(e),
            )

        # Step 2: Convert to WAV if needed
        wav_path = candidate
        if content_type != "audio/wav":
            # Convert to WAV via ffmpeg
            wav_path = candidate.with_suffix(".wav")
            ffmpeg_cmd = [
                "ffmpeg",
                "-i",
                str(candidate),
                "-ar",
                "16000",  # Sample rate
                "-ac",
                "1",  # Mono
                "-y",  # Overwrite
                str(wav_path),
            ]

            try:
                subprocess.run(ffmpeg_cmd, check=True, capture_output=True, timeout=30)
                logger.info(
                    "CHUNK_CONVERTED_TO_WAV",
                    session_id=session_id,
                    chunk_number=chunk_number,
                    wav_path=str(wav_path),
                )
            except subprocess.CalledProcessError as e:
                # Last attempt: if we didn't graft before and it's WebM, try grafting
                if (
                    enable_graft
                    and audio_file.suffix.lower() == ".webm"
                    and candidate == audio_file
                ):
                    try:
                        from backend.workers.webm_graft import (
                            ensure_session_header,
                            graft_header,
                        )

                        logger.info(
                            "CHUNK_GRAFT_RETRY",
                            session_id=session_id,
                            chunk_number=chunk_number,
                        )
                        header = ensure_session_header(audio_file.parent)
                        candidate = graft_header(audio_file, header)
                        wav_path = candidate.with_suffix(".wav")

                        # Retry ffmpeg with grafted file
                        ffmpeg_cmd[2] = str(candidate)
                        ffmpeg_cmd[-1] = str(wav_path)
                        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, timeout=30)
                        logger.info(
                            "CHUNK_GRAFT_RETRY_SUCCESS",
                            session_id=session_id,
                            chunk_number=chunk_number,
                            grafted=str(candidate),
                        )
                    except Exception as retry_exc:
                        logger.error(
                            "CHUNK_GRAFT_RETRY_FAILED",
                            session_id=session_id,
                            chunk_number=chunk_number,
                            error=str(retry_exc),
                        )
                        raise retry_exc
                else:
                    logger.error(
                        "CHUNK_FFMPEG_FAILED",
                        session_id=session_id,
                        chunk_number=chunk_number,
                        error=e.stderr.decode() if e.stderr else str(e),
                    )
                    raise

        # Step 2: Transcribe with faster-whisper
        transcription_service = get_container().get_transcription_service()

        with open(wav_path, "rb") as f:
            audio_content = f.read()

        result = transcription_service.process_transcription(
            session_id=session_id,
            audio_content=audio_content,
            filename=f"chunk_{chunk_number}.wav",
            content_type="audio/wav",
            metadata={
                "chunk_number": chunk_number,
                "audio_hash": audio_hash,
                "worker_task_id": self.request.id,
            },
        )

        transcript = result.get("text", "")
        language = result.get("language", "es")
        duration = result.get("duration", 0.0)

        logger.info(
            "CHUNK_TRANSCRIBED",
            session_id=session_id,
            chunk_number=chunk_number,
            transcript_length=len(transcript),
            language=language,
            duration=duration,
        )

        # Step 3: Append to HDF5 corpus
        from backend.storage.session_chunks_schema import append_chunk_to_session

        hdf5_path = append_chunk_to_session(
            session_id=session_id,
            chunk_idx=chunk_number,
            transcript=transcript,
            audio_hash=audio_hash,
            duration=duration,
            language=language,
            timestamp_start=chunk_number * 3.0,  # Assuming 3s chunks
            timestamp_end=(chunk_number + 1) * 3.0,
        )

        logger.info(
            "CHUNK_APPENDED_TO_HDF5",
            session_id=session_id,
            chunk_number=chunk_number,
            hdf5_path=hdf5_path,
        )

        # Step 4: Return result
        return {
            "session_id": session_id,
            "chunk_number": chunk_number,
            "transcript": transcript,
            "audio_hash": audio_hash,
            "duration": duration,
            "language": language,
            "hdf5_path": hdf5_path,
            "timestamps": {
                "start": chunk_number * 3.0,
                "end": (chunk_number + 1) * 3.0,
            },
            "status": "completed",
        }

    except SoftTimeLimitExceeded:
        logger.error(
            "CHUNK_TASK_TIMEOUT",
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=self.request.id,
            timeout_sec=540,
        )
        return {
            "session_id": session_id,
            "chunk_number": chunk_number,
            "status": "failed",
            "error": "Task timeout (9 minutes)",
        }

    except Exception as exc:
        logger.error(
            "CHUNK_TASK_FAILED",
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=self.request.id,
            error=str(exc),
            retry_count=self.request.retries,
        )

        # Retry with exponential backoff
        countdown = 30 * (2**self.request.retries)

        if self.request.retries >= self.max_retries:
            logger.error(
                "CHUNK_TASK_MAX_RETRIES",
                session_id=session_id,
                chunk_number=chunk_number,
                task_id=self.request.id,
                max_retries=self.max_retries,
            )
            return {
                "session_id": session_id,
                "chunk_number": chunk_number,
                "status": "failed",
                "error": f"Failed after {self.max_retries} retries: {exc!s}",
            }

        logger.warning(
            "CHUNK_TASK_RETRY",
            session_id=session_id,
            chunk_number=chunk_number,
            task_id=self.request.id,
            retry_count=self.request.retries + 1,
            countdown_sec=countdown,
        )

        raise self.retry(exc=exc, countdown=countdown)
