from __future__ import annotations

"""
Diarization Low-Priority Worker with CPU Scheduler
Card: FI-RELIABILITY-IMPL-004

Background worker that:
1. Monitors CPU idle ≥50% for 10-15s
2. Processes 1 chunk at a time (30-45s audio, 0.8s overlap)
3. Uses faster-whisper (CPU, int8, num_workers=1)
4. Saves incremental results to HDF5 (storage/diarization.h5)
5. Updates job progress after each chunk
6. Does NOT block main thread or Triage events

File: backend/diarization_worker_lowprio.py
Created: 2025-10-31
"""

import hashlib
import os
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Optional

import h5py
import psutil

from backend.logger import get_logger
from backend.whisper_service import get_whisper_model, is_whisper_available

logger = get_logger(__name__)

# Configuration
CPU_IDLE_THRESHOLD = float(os.getenv("DIARIZATION_CPU_IDLE_THRESHOLD", "50.0"))  # 50% idle
CPU_IDLE_WINDOW_SEC = int(os.getenv("DIARIZATION_CPU_IDLE_WINDOW", "10"))  # 10s monitoring window
CHUNK_DURATION_SEC = int(os.getenv("DIARIZATION_CHUNK_SEC", "30"))  # 30-45s chunks
CHUNK_OVERLAP_SEC = float(os.getenv("DIARIZATION_OVERLAP_SEC", "0.8"))  # 0.8s overlap
H5_STORAGE_PATH = Path(os.getenv("DIARIZATION_H5_PATH", "storage/diarization.h5"))
WHISPER_MODEL_SIZE = os.getenv(
    "WHISPER_MODEL_SIZE", "small"
)  # Aligned with whisper_service.py default
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
NUM_WORKERS = 1  # Single worker to avoid blocking


@dataclass
class ChunkResult:
    """Single chunk transcription result."""

    chunk_idx: int
    start_time: float
    end_time: float
    text: str
    speaker: str  # PACIENTE | MEDICO | DESCONOCIDO
    confidence: Optional[float]
    temperature: float  # Whisper temperature
    rtf: float  # Real-time factor (processing_time / audio_duration)
    timestamp: str  # ISO 8601


@dataclass
class DiarizationJob:
    """Low-priority diarization job."""

    job_id: str
    session_id: str
    audio_path: Path
    audio_hash: str
    total_chunks: int
    processed_chunks: int
    status: str  # pending | in_progress | completed | failed
    created_at: str
    updated_at: str
    error: Optional[str] = None


class CPUScheduler:
    """
    CPU scheduler that monitors idle time and triggers processing.

    Only starts chunk processing when:
    - CPU idle ≥ threshold for monitoring window
    - No other high-priority tasks running
    """

    def __init__(self, threshold: float = CPU_IDLE_THRESHOLD, window: int = CPU_IDLE_WINDOW_SEC):
        self.threshold = threshold
        self.window = window
        self.logger = get_logger(__name__ + ".CPUScheduler")

    def is_cpu_idle(self) -> bool:
        """
        Check if CPU is idle enough to start processing.

        Returns:
            True if CPU idle ≥ threshold for window seconds
        """
        samples = []
        sample_interval = 1.0  # 1s per sample
        num_samples = self.window

        for _ in range(num_samples):
            # Get CPU usage (100 - idle)
            cpu_percent = psutil.cpu_percent(interval=sample_interval)
            idle_percent = 100.0 - cpu_percent
            samples.append(idle_percent)

        avg_idle = sum(samples) / len(samples)
        is_idle = avg_idle >= self.threshold

        self.logger.debug(
            "CPU_IDLE_CHECK",
            avg_idle=f"{avg_idle:.1f}%",
            threshold=f"{self.threshold}%",
            is_idle=is_idle,
        )

        return is_idle


class DiarizationWorker:
    """
    Low-priority background worker for diarization.

    Features:
    - CPU-aware scheduling (only runs when idle)
    - Incremental HDF5 storage (per-chunk saves)
    - Non-blocking (separate thread)
    - Progress tracking
    """

    def __init__(self):
        self.job_queue: Queue[DiarizationJob] = Queue()
        self.scheduler = CPUScheduler()
        self.h5_path = H5_STORAGE_PATH
        self.h5_lock = threading.Lock()
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.logger = get_logger(__name__ + ".DiarizationWorker")

        # Ensure HDF5 file exists
        self._init_h5_storage()

    def _init_h5_storage(self):
        """Initialize HDF5 storage with groups."""
        self.h5_path.parent.mkdir(parents=True, exist_ok=True)

        with h5py.File(self.h5_path, "a") as h5:
            if "diarization" not in h5:
                h5.create_group("diarization")
                self.logger.info("H5_STORAGE_INITIALIZED", path=str(self.h5_path))

    def start(self):
        """Start worker thread."""
        if self.running:
            self.logger.warning("WORKER_ALREADY_RUNNING")
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        self.logger.info("WORKER_STARTED", h5_path=str(self.h5_path))

    def stop(self):
        """Stop worker thread gracefully."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        self.logger.info("WORKER_STOPPED")

    def _init_job_in_h5(self, job: DiarizationJob):
        """
        Initialize job in HDF5 storage immediately.

        Creates the job group and metadata attrs so the job is queryable
        before processing begins.
        """
        with self.h5_lock:
            with h5py.File(self.h5_path, "a") as h5:
                job_group_path = f"diarization/{job.job_id}"

                if job_group_path not in h5:
                    # Create job group with metadata
                    job_group = h5.create_group(job_group_path)
                    job_group.attrs["session_id"] = job.session_id
                    job_group.attrs["audio_path"] = str(job.audio_path)
                    job_group.attrs["audio_hash"] = job.audio_hash
                    job_group.attrs["status"] = job.status
                    job_group.attrs["progress_pct"] = 0
                    job_group.attrs["total_chunks"] = job.total_chunks
                    job_group.attrs["created_at"] = job.created_at
                    job_group.attrs["updated_at"] = job.updated_at

                    # Create empty chunks dataset
                    dt = h5py.special_dtype(vlen=str)
                    h5.create_dataset(
                        f"{job_group_path}/chunks",
                        shape=(0,),
                        maxshape=(None,),
                        dtype=[
                            ("chunk_idx", "i4"),
                            ("start_time", "f8"),
                            ("end_time", "f8"),
                            ("text", dt),
                            ("speaker", dt),
                            ("temperature", "f8"),
                            ("rtf", "f8"),
                            ("timestamp", dt),
                        ],
                    )

                    h5.flush()
                    self.logger.info("JOB_INITIALIZED_IN_H5", job_id=job.job_id)

    def submit_job(self, job: DiarizationJob):
        """Submit job to queue."""
        self.job_queue.put(job)
        self.logger.info(
            "JOB_SUBMITTED",
            job_id=job.job_id,
            session_id=job.session_id,
            total_chunks=job.total_chunks,
        )

    def _worker_loop(self):
        """Main worker loop."""
        self.logger.info("WORKER_LOOP_START")

        while self.running:
            try:
                # Try to get job (non-blocking with timeout)
                try:
                    job = self.job_queue.get(timeout=5)
                except Empty:
                    continue

                # Wait for CPU to be idle
                self.logger.info("WAITING_FOR_CPU_IDLE", job_id=job.job_id)
                while self.running and not self.scheduler.is_cpu_idle():
                    time.sleep(5)  # Check every 5s

                if not self.running:
                    break

                # Process job
                self.logger.info("JOB_PROCESSING_START", job_id=job.job_id)
                self._process_job(job)

            except Exception as e:
                self.logger.error("WORKER_LOOP_ERROR", error=str(e))

    def _process_job(self, job: DiarizationJob):
        """
        Process diarization job incrementally.

        Processes one chunk at a time, saves to HDF5 after each chunk.
        """
        try:
            # Update job status
            self._update_job_status(job.job_id, "in_progress", 0)

            # Check Whisper availability
            if not is_whisper_available():
                raise RuntimeError("Whisper not available")

            model = get_whisper_model()
            if model is None:
                raise RuntimeError("Whisper model not loaded")

            # Create chunks
            chunks = self._create_chunks(job.audio_path, CHUNK_DURATION_SEC, CHUNK_OVERLAP_SEC)
            job.total_chunks = len(chunks)

            # CRITICAL: Persist total_chunks to HDF5 immediately
            # (so status endpoint knows total from the start)
            self._update_job_status(job.job_id, "in_progress", 0, total_chunks=job.total_chunks)

            self.logger.info("JOB_CHUNKS_CREATED", job_id=job.job_id, total_chunks=len(chunks))

            # Process each chunk
            for idx, (start_sec, end_sec) in enumerate(chunks):
                # Extract chunk
                chunk_path = self._extract_chunk(job.audio_path, start_sec, end_sec, idx)

                # Wait for CPU idle before processing
                if not self.scheduler.is_cpu_idle():
                    self.logger.info("CPU_BUSY_WAITING", job_id=job.job_id, chunk_idx=idx)
                    while self.running and not self.scheduler.is_cpu_idle():
                        time.sleep(5)

                # Transcribe chunk (auto-detect language)
                chunk_start_time = time.time()

                segments_iter, info = model.transcribe(
                    str(chunk_path),
                    language=None,  # Auto-detect (en, es, etc.)
                    vad_filter=True,
                    beam_size=5,
                )

                # Collect segments
                segments = list(segments_iter)
                text_parts = [seg.text.strip() for seg in segments]
                full_text = " ".join(text_parts)

                processing_time = time.time() - chunk_start_time
                audio_duration = end_sec - start_sec
                rtf = processing_time / audio_duration if audio_duration > 0 else 0

                # Get temperature (avg from segments if available)
                # Only segments with avg_logprob attribute count toward the average
                temps_with_data = [
                    seg.avg_logprob for seg in segments if hasattr(seg, "avg_logprob")
                ]
                if temps_with_data:
                    avg_temp = sum(temps_with_data) / len(temps_with_data)
                else:
                    # No temperature data available, log and use default
                    avg_temp = 0.0
                    if segments:
                        self.logger.warning(
                            "TEMPERATURE_METADATA_MISSING",
                            job_id=job.job_id,
                            chunk_idx=idx,
                            num_segments=len(segments),
                        )

                # Create chunk result
                chunk_result = ChunkResult(
                    chunk_idx=idx,
                    start_time=start_sec,
                    end_time=end_sec,
                    text=full_text,
                    speaker="DESCONOCIDO",  # LLM classification disabled for low-priority
                    confidence=None,
                    temperature=avg_temp,
                    rtf=rtf,
                    timestamp=datetime.now(UTC).isoformat() + "Z",
                )

                # Save chunk to HDF5
                self._save_chunk_to_h5(job, chunk_result)

                # Update progress
                job.processed_chunks = idx + 1
                progress_pct = int((job.processed_chunks / job.total_chunks) * 100)
                self._update_job_status(job.job_id, "in_progress", progress_pct)

                # Cleanup chunk file
                chunk_path.unlink(missing_ok=True)

                self.logger.info(
                    "CHUNK_PROCESSED",
                    job_id=job.job_id,
                    chunk_idx=idx,
                    rtf=f"{rtf:.2f}",
                    progress_pct=progress_pct,
                )

            # Mark job complete
            self._update_job_status(job.job_id, "completed", 100)
            self.logger.info("JOB_COMPLETED", job_id=job.job_id, chunks=job.total_chunks)

        except Exception as e:
            self.logger.error("JOB_PROCESSING_FAILED", job_id=job.job_id, error=str(e))
            self._update_job_status(job.job_id, "failed", 0, error=str(e))

    def _create_chunks(self, audio_path: Path, chunk_sec: int, overlap_sec: float) -> list[tuple]:
        """
        Create chunks with overlap for better continuity.

        Returns:
            List of (start_sec, end_sec) tuples
        """
        import subprocess

        # Get duration
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        duration = float(result.stdout.strip())

        chunks = []
        current = 0.0

        while current < duration:
            end = min(current + chunk_sec, duration)
            chunks.append((current, end))
            # Move forward with overlap
            current = end - overlap_sec if end < duration else end

        return chunks

    def _extract_chunk(self, audio_path: Path, start_sec: float, end_sec: float, idx: int) -> Path:
        """Extract audio chunk using ffmpeg."""
        import subprocess

        chunk_path = Path(f"/tmp/diarization_chunk_{idx:04d}.wav")
        duration = end_sec - start_sec

        subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(audio_path),
                "-ss",
                str(start_sec),
                "-t",
                str(duration),
                "-y",
                str(chunk_path),
                "-loglevel",
                "error",
            ],
            check=True,
            timeout=30,
        )

        return chunk_path

    def _save_chunk_to_h5(self, job: DiarizationJob, chunk: ChunkResult):
        """
        Save chunk result to HDF5.

        Structure:
        /diarization/{job_id}/
            metadata (attrs)
            chunks (dataset)
        """
        with self.h5_lock:
            with h5py.File(self.h5_path, "a") as h5:
                job_group_path = f"diarization/{job.job_id}"

                if job_group_path not in h5:
                    # Create job group
                    job_group = h5.create_group(job_group_path)
                    job_group.attrs["session_id"] = job.session_id
                    job_group.attrs["audio_path"] = str(job.audio_path)
                    job_group.attrs["audio_hash"] = job.audio_hash
                    job_group.attrs["created_at"] = job.created_at
                    job_group.attrs["total_chunks"] = job.total_chunks

                    # Create chunks dataset
                    dt = h5py.special_dtype(vlen=str)
                    h5.create_dataset(
                        f"{job_group_path}/chunks",
                        shape=(0,),
                        maxshape=(None,),
                        dtype=[
                            ("chunk_idx", "i4"),
                            ("start_time", "f8"),
                            ("end_time", "f8"),
                            ("text", dt),
                            ("speaker", dt),
                            ("temperature", "f8"),
                            ("rtf", "f8"),
                            ("timestamp", dt),
                        ],
                    )

                # Append chunk
                chunks_ds = h5[f"{job_group_path}/chunks"]
                current_size = chunks_ds.shape[0]  # type: ignore[attr-defined]
                chunks_ds.resize((current_size + 1,))  # type: ignore[attr-defined]

                chunks_ds[current_size] = (  # type: ignore[index]
                    chunk.chunk_idx,
                    chunk.start_time,
                    chunk.end_time,
                    chunk.text,
                    chunk.speaker,
                    chunk.temperature,
                    chunk.rtf,
                    chunk.timestamp,
                )

                h5.flush()

    def _update_job_status(
        self,
        job_id: str,
        status: str,
        progress_pct: int,
        error: Optional[str] = None,
        total_chunks: Optional[int] = None,
    ):
        """
        Update job status in HDF5.

        This updates metadata attrs in the job group.
        Creates group if not exists (for early failures).

        Args:
            job_id: Job ID
            status: Job status (pending, in_progress, completed, failed)
            progress_pct: Progress percentage (0-100)
            error: Error message if failed
            total_chunks: Total number of chunks (persists when calculated)
        """
        with self.h5_lock:
            with h5py.File(self.h5_path, "a") as h5:
                job_group_path = f"diarization/{job_id}"

                if job_group_path not in h5:
                    # Create minimal group for failed jobs
                    job_group = h5.create_group(job_group_path)
                    job_group.attrs["created_at"] = datetime.now(UTC).isoformat() + "Z"
                    # Create empty chunks dataset
                    dt = h5py.special_dtype(vlen=str)
                    h5.create_dataset(
                        f"{job_group_path}/chunks",
                        shape=(0,),
                        maxshape=(None,),
                        dtype=[
                            ("chunk_idx", "i4"),
                            ("start_time", "f8"),
                            ("end_time", "f8"),
                            ("text", dt),
                            ("speaker", dt),
                            ("temperature", "f8"),
                            ("rtf", "f8"),
                            ("timestamp", dt),
                        ],
                    )

                job_group = h5[job_group_path]
                job_group.attrs["status"] = status  # type: ignore[attr-defined]
                job_group.attrs["progress_pct"] = progress_pct  # type: ignore[attr-defined]
                job_group.attrs["updated_at"] = datetime.now(UTC).isoformat() + "Z"  # type: ignore[attr-defined]

                # CRITICAL FIX: Persist total_chunks when calculated
                # This prevents stuck jobs with total_chunks=0
                if total_chunks is not None:
                    job_group.attrs["total_chunks"] = total_chunks  # type: ignore[attr-defined]

                if error:
                    job_group.attrs["error"] = error  # type: ignore[attr-defined]

                h5.flush()

    def get_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """
        Get job status from HDF5.

        Returns:
            Dict with status, progress, chunks, or None if not found
        """
        with self.h5_lock:
            with h5py.File(self.h5_path, "r") as h5:
                job_group_path = f"diarization/{job_id}"

                if job_group_path not in h5:
                    return None

                job_group = h5[job_group_path]
                chunks_ds = job_group["chunks"]  # type: ignore[index]

                # Helper to decode bytes from HDF5
                def decode_if_bytes(val):
                    return val.decode("utf-8") if isinstance(val, bytes) else val

                # Convert chunks to list of dicts
                chunks = []
                for i in range(len(chunks_ds)):
                    chunk_data = chunks_ds[i]  # type: ignore[index]
                    chunks.append(
                        {
                            "chunk_idx": int(chunk_data["chunk_idx"]),  # type: ignore[index]
                            "start_time": float(chunk_data["start_time"]),  # type: ignore[index]
                            "end_time": float(chunk_data["end_time"]),  # type: ignore[index]
                            "text": decode_if_bytes(chunk_data["text"]),  # type: ignore[index]
                            "speaker": decode_if_bytes(chunk_data["speaker"]),  # type: ignore[index]
                            "temperature": float(chunk_data["temperature"]),  # type: ignore[index]
                            "rtf": float(chunk_data["rtf"]),  # type: ignore[index]
                            "timestamp": decode_if_bytes(chunk_data["timestamp"]),  # type: ignore[index]
                        }
                    )

                return {
                    "job_id": job_id,
                    "session_id": decode_if_bytes(job_group.attrs.get("session_id", "unknown")),  # type: ignore[attr-defined]
                    "status": decode_if_bytes(job_group.attrs.get("status", "unknown")),  # type: ignore[attr-defined]
                    "progress_pct": job_group.attrs.get("progress_pct", 0),  # type: ignore[attr-defined]
                    "total_chunks": job_group.attrs.get("total_chunks", 0),  # type: ignore[attr-defined]
                    "processed_chunks": len(chunks),
                    "chunks": chunks,
                    "created_at": decode_if_bytes(job_group.attrs.get("created_at", "")),  # type: ignore[attr-defined]
                    "updated_at": decode_if_bytes(
                        job_group.attrs.get("updated_at", job_group.attrs.get("created_at", ""))  # type: ignore[attr-defined]
                    ),
                    "error": decode_if_bytes(job_group.attrs.get("error", None)),  # type: ignore[attr-defined]
                }

    def list_all_jobs(
        self, session_id: Optional[str] = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        List all jobs from HDF5, optionally filtered by session_id.

        Args:
            session_id: Optional session ID to filter by
            limit: Maximum number of jobs to return

        Returns:
            List of job metadata dicts (without chunks array for performance)
        """
        jobs = []

        with self.h5_lock:
            with h5py.File(self.h5_path, "r") as h5:
                if "diarization" not in h5:
                    return []

                diarization_group = h5["diarization"]

                # Helper to decode bytes from HDF5 and convert numpy types to Python types
                def decode_if_bytes(val):
                    if isinstance(val, bytes):
                        return val.decode("utf-8")
                    # Convert numpy types to Python native types
                    if hasattr(val, "item"):  # numpy scalar
                        return val.item()
                    return val

                # Iterate through all job groups
                for job_id in diarization_group.keys():  # type: ignore[attr-defined]
                    job_group = diarization_group[job_id]  # type: ignore[index]

                    # Filter by session_id if provided
                    job_session_id = decode_if_bytes(job_group.attrs.get("session_id", ""))  # type: ignore[attr-defined]
                    if session_id and job_session_id != session_id:
                        continue

                    # Get chunk count
                    chunks_ds = job_group["chunks"]  # type: ignore[index]
                    processed_chunks = len(chunks_ds)

                    jobs.append(
                        {
                            "job_id": job_id,
                            "session_id": job_session_id,
                            "status": decode_if_bytes(job_group.attrs.get("status", "unknown")),  # type: ignore[attr-defined]
                            "progress_pct": int(
                                decode_if_bytes(job_group.attrs.get("progress_pct", 0))  # type: ignore[attr-defined]
                            ),
                            "total_chunks": int(
                                decode_if_bytes(job_group.attrs.get("total_chunks", 0))  # type: ignore[attr-defined]
                            ),
                            "processed_chunks": int(processed_chunks),
                            "created_at": decode_if_bytes(job_group.attrs.get("created_at", "")),  # type: ignore[attr-defined]
                            "updated_at": decode_if_bytes(
                                job_group.attrs.get(  # type: ignore[attr-defined]
                                    "updated_at", job_group.attrs.get("created_at", "")  # type: ignore[attr-defined]
                                )
                            ),
                            "error": decode_if_bytes(job_group.attrs.get("error", None)),  # type: ignore[attr-defined]
                        }
                    )

                # Sort by created_at descending (most recent first)
                jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)

                # Apply limit
                return jobs[:limit]


# Global worker instance
_worker_instance: Optional[DiarizationWorker] = None


def get_worker() -> DiarizationWorker:
    """Get singleton worker instance."""
    global _worker_instance

    if _worker_instance is None:
        _worker_instance = DiarizationWorker()
        _worker_instance.start()

    return _worker_instance


def create_diarization_job(session_id: str, audio_path: Path) -> str:
    """
    Create low-priority diarization job.

    Args:
        session_id: Session ID
        audio_path: Path to audio file

    Returns:
        job_id (UUID)
    """
    import uuid

    job_id = str(uuid.uuid4())

    # Compute audio hash
    sha256 = hashlib.sha256()
    with open(audio_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    audio_hash = f"sha256:{sha256.hexdigest()}"

    now = datetime.now(UTC).isoformat() + "Z"

    job = DiarizationJob(
        job_id=job_id,
        session_id=session_id,
        audio_path=audio_path,
        audio_hash=audio_hash,
        total_chunks=0,  # Will be calculated during processing
        processed_chunks=0,
        status="pending",
        created_at=now,
        updated_at=now,
    )

    # Initialize job in HDF5 immediately (before submitting to queue)
    # This ensures the job is queryable via get_job_status() right away
    worker = get_worker()
    worker._init_job_in_h5(job)

    # Submit job to processing queue
    worker.submit_job(job)

    logger.info(
        "JOB_CREATED_IN_H5", job_id=job_id, session_id=session_id, audio_path=str(audio_path)
    )
    return job_id


def get_job_status(job_id: str) -> Optional[dict[str, Any]]:
    """Get job status and chunks from HDF5."""
    worker = get_worker()
    return worker.get_job_status(job_id)


def list_all_jobs(session_id: Optional[str] = None, limit: int = 50) -> list[dict[str, Any]]:
    """List all diarization jobs from HDF5."""
    worker = get_worker()
    return worker.list_all_jobs(session_id, limit)
