"""
Unit Tests for Low-Priority Diarization Worker
Card: FI-RELIABILITY-IMPL-004

Tests:
1. CPU scheduler: idle detection
2. HDF5 storage: incremental chunk saves
3. Job creation and status tracking
4. Worker thread lifecycle
5. Error handling and recovery

File: tests/test_diarization_lowprio.py
Created: 2025-10-31
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import h5py
import pytest

from backend.diarization_worker_lowprio import (
    ChunkResult,
    CPUScheduler,
    DiarizationJob,
    create_diarization_job,
)


@pytest.fixture
def temp_h5_path(tmp_path):
    """Temporary HDF5 file for testing."""
    return tmp_path / "test_diarization.h5"


@pytest.fixture
def mock_audio_file(tmp_path):
    """Mock audio file for testing."""
    audio_path = tmp_path / "test_audio.wav"
    audio_path.write_bytes(b"RIFF" + b"\x00" * 100)  # Minimal WAV header
    return audio_path


@pytest.fixture
def worker_with_temp_h5(temp_h5_path, monkeypatch):
    """Worker instance with temporary HDF5 storage."""
    # Must set env BEFORE importing to ensure worker picks it up
    import importlib

    monkeypatch.setenv("DIARIZATION_H5_PATH", str(temp_h5_path))

    # Reload module to pick up new env var
    import backend.diarization_worker_lowprio as worker_module

    importlib.reload(worker_module)

    worker = worker_module.DiarizationWorker()
    yield worker
    worker.stop()

    # Reset module state
    worker_module._worker_instance = None


# ============================================================================
# CPU SCHEDULER TESTS
# ============================================================================


def test_cpu_scheduler_init() -> None:
    """Test CPUScheduler initialization."""
    scheduler = CPUScheduler(threshold=60.0, window=5)
    assert scheduler.threshold == 60.0
    assert scheduler.window == 5


@patch("backend.diarization_worker_lowprio.psutil.cpu_percent")
def test_cpu_scheduler_idle_detected(mock_cpu_percent) -> None:
    """Test CPU scheduler detects idle state."""
    # Mock CPU usage: 30% busy = 70% idle
    mock_cpu_percent.return_value = 30.0

    scheduler = CPUScheduler(threshold=50.0, window=2)
    is_idle = scheduler.is_cpu_idle()

    assert is_idle is True
    assert mock_cpu_percent.call_count == 2  # window=2 samples


@patch("backend.diarization_worker_lowprio.psutil.cpu_percent")
def test_cpu_scheduler_busy_detected(mock_cpu_percent) -> None:
    """Test CPU scheduler detects busy state."""
    # Mock CPU usage: 80% busy = 20% idle
    mock_cpu_percent.return_value = 80.0

    scheduler = CPUScheduler(threshold=50.0, window=2)
    is_idle = scheduler.is_cpu_idle()

    assert is_idle is False


# ============================================================================
# HDF5 STORAGE TESTS
# ============================================================================


def test_h5_storage_initialization(worker_with_temp_h5, temp_h5_path) -> None:
    """Test HDF5 storage is initialized correctly."""
    assert temp_h5_path.exists()

    with h5py.File(temp_h5_path, "r") as h5:
        assert "diarization" in h5


def test_save_chunk_to_h5(worker_with_temp_h5, temp_h5_path) -> None:
    """Test saving chunk to HDF5."""
    job = DiarizationJob(
        job_id="test-job-001",
        session_id="test-session",
        audio_path=Path("/tmp/test.wav"),
        audio_hash="sha256:abcd1234",
        total_chunks=10,
        processed_chunks=0,
        status="in_progress",
        created_at="2025-10-31T12:00:00Z",
        updated_at="2025-10-31T12:00:00Z",
    )

    chunk = ChunkResult(
        chunk_idx=0,
        start_time=0.0,
        end_time=30.0,
        text="Hola doctor, me duele la cabeza.",
        speaker="PACIENTE",
        confidence=None,
        temperature=-0.5,
        rtf=0.25,
        timestamp="2025-10-31T12:00:30Z",
    )

    worker_with_temp_h5._save_chunk_to_h5(job, chunk)

    # Verify chunk saved (decode bytes from HDF5)
    with h5py.File(temp_h5_path, "r") as h5:
        assert f"diarization/{job.job_id}" in h5
        chunks_ds = h5[f"diarization/{job.job_id}/chunks"]
        assert len(chunks_ds) == 1
        assert chunks_ds[0]["chunk_idx"] == 0

        # HDF5 returns bytes for vlen strings
        text = chunks_ds[0]["text"]
        speaker = chunks_ds[0]["speaker"]
        assert (
            text.decode("utf-8") if isinstance(text, bytes) else text
        ) == "Hola doctor, me duele la cabeza."
        assert (speaker.decode("utf-8") if isinstance(speaker, bytes) else speaker) == "PACIENTE"


def test_save_multiple_chunks_incremental(worker_with_temp_h5, temp_h5_path) -> None:
    """Test incremental chunk saves (append-only)."""
    job = DiarizationJob(
        job_id="test-job-002",
        session_id="test-session",
        audio_path=Path("/tmp/test.wav"),
        audio_hash="sha256:xyz789",
        total_chunks=3,
        processed_chunks=0,
        status="in_progress",
        created_at="2025-10-31T12:00:00Z",
        updated_at="2025-10-31T12:00:00Z",
    )

    # Save 3 chunks incrementally
    for i in range(3):
        chunk = ChunkResult(
            chunk_idx=i,
            start_time=float(i * 30),
            end_time=float((i + 1) * 30),
            text=f"Chunk {i} text",
            speaker="DESCONOCIDO",
            confidence=None,
            temperature=-0.3,
            rtf=0.2,
            timestamp=f"2025-10-31T12:00:{i:02d}Z",
        )
        worker_with_temp_h5._save_chunk_to_h5(job, chunk)

    # Verify all chunks saved (decode bytes)
    with h5py.File(temp_h5_path, "r") as h5:
        chunks_ds = h5[f"diarization/{job.job_id}/chunks"]
        assert len(chunks_ds) == 3

        text = chunks_ds[2]["text"]
        assert (text.decode("utf-8") if isinstance(text, bytes) else text) == "Chunk 2 text"


# ============================================================================
# JOB STATUS TESTS
# ============================================================================


def test_get_job_status_from_h5(worker_with_temp_h5, temp_h5_path) -> None:
    """Test retrieving job status from HDF5."""
    job = DiarizationJob(
        job_id="test-job-status",
        session_id="session-123",
        audio_path=Path("/tmp/test.wav"),
        audio_hash="sha256:hash123",
        total_chunks=2,
        processed_chunks=0,
        status="in_progress",
        created_at="2025-10-31T12:00:00Z",
        updated_at="2025-10-31T12:00:00Z",
    )

    # Save 2 chunks
    for i in range(2):
        chunk = ChunkResult(
            chunk_idx=i,
            start_time=float(i * 30),
            end_time=float((i + 1) * 30),
            text=f"Test chunk {i}",
            speaker="DESCONOCIDO",
            confidence=None,
            temperature=-0.4,
            rtf=0.3,
            timestamp=f"2025-10-31T12:00:{i:02d}Z",
        )
        worker_with_temp_h5._save_chunk_to_h5(job, chunk)

    # Update status
    worker_with_temp_h5._update_job_status("test-job-status", "completed", 100)

    # Get status
    status = worker_with_temp_h5.get_job_status("test-job-status")

    assert status is not None
    assert status["job_id"] == "test-job-status"
    assert status["session_id"] == "session-123"
    assert status["status"] == "completed"
    assert status["progress_pct"] == 100
    assert len(status["chunks"]) == 2


def test_get_job_status_not_found(worker_with_temp_h5) -> None:
    """Test get_job_status returns None for unknown job."""
    status = worker_with_temp_h5.get_job_status("unknown-job-id")
    assert status is None


# ============================================================================
# WORKER LIFECYCLE TESTS
# ============================================================================


def test_worker_start_stop(worker_with_temp_h5) -> None:
    """Test worker thread starts and stops cleanly."""
    # Worker fixture does NOT auto-start (fixture calls stop() in teardown)
    # Start manually for this test
    worker_with_temp_h5.start()

    assert worker_with_temp_h5.running is True
    assert worker_with_temp_h5.worker_thread is not None

    # Stop worker
    worker_with_temp_h5.stop()
    assert worker_with_temp_h5.running is False


def test_worker_singleton() -> None:
    """Test worker singleton pattern."""
    from backend.diarization_worker_lowprio import get_worker

    worker1 = get_worker()
    worker2 = get_worker()

    assert worker1 is worker2
    worker1.stop()


# ============================================================================
# JOB CREATION TESTS
# ============================================================================


@patch("backend.diarization_worker_lowprio.get_worker")
def test_create_diarization_job(mock_get_worker, mock_audio_file) -> None:
    """Test job creation and submission."""
    mock_worker = Mock()
    mock_get_worker.return_value = mock_worker

    job_id = create_diarization_job("session-456", mock_audio_file)

    assert len(job_id) == 36  # UUID4 format
    mock_worker.submit_job.assert_called_once()

    # Verify job submitted
    submitted_job = mock_worker.submit_job.call_args[0][0]
    assert submitted_job.session_id == "session-456"
    assert submitted_job.audio_path == mock_audio_file


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


def test_process_job_whisper_unavailable(worker_with_temp_h5, mock_audio_file) -> None:
    """Test job fails gracefully when Whisper unavailable."""
    job = DiarizationJob(
        job_id="test-fail-001",
        session_id="session-fail",
        audio_path=mock_audio_file,
        audio_hash="sha256:fail",
        total_chunks=0,
        processed_chunks=0,
        status="pending",
        created_at="2025-10-31T12:00:00Z",
        updated_at="2025-10-31T12:00:00Z",
    )

    with patch("backend.diarization_worker_lowprio.is_whisper_available", return_value=False):
        worker_with_temp_h5._process_job(job)

    # Check job marked as failed
    status = worker_with_temp_h5.get_job_status("test-fail-001")
    assert status is not None
    assert status["status"] == "failed"


# ============================================================================
# INTEGRATION TEST
# ============================================================================


@pytest.mark.slow
@patch("backend.diarization_worker_lowprio.get_whisper_model")
@patch("backend.diarization_worker_lowprio.is_whisper_available", return_value=True)
def test_full_job_processing_mock(
    mock_whisper_avail, mock_get_model, worker_with_temp_h5, mock_audio_file, temp_h5_path
) -> None:
    """Test full job processing with mocked Whisper."""
    # Mock Whisper model
    mock_model = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = "Test transcription"
    mock_segment.avg_logprob = -0.5

    mock_info = MagicMock()
    mock_info.duration = 30.0

    mock_model.transcribe.return_value = ([mock_segment], mock_info)
    mock_get_model.return_value = mock_model

    # Create job
    job = DiarizationJob(
        job_id="test-full-001",
        session_id="session-full",
        audio_path=mock_audio_file,
        audio_hash="sha256:full",
        total_chunks=0,
        processed_chunks=0,
        status="pending",
        created_at="2025-10-31T12:00:00Z",
        updated_at="2025-10-31T12:00:00Z",
    )

    # Mock CPU scheduler to return idle immediately
    with patch.object(worker_with_temp_h5.scheduler, "is_cpu_idle", return_value=True):
        # Mock chunk creation (avoid ffprobe dependency)
        with patch(
            "backend.diarization_worker_lowprio.DiarizationWorker._create_chunks",
            return_value=[(0.0, 30.0)],
        ):
            # Mock chunk extraction
            with patch(
                "backend.diarization_worker_lowprio.DiarizationWorker._extract_chunk",
                return_value=mock_audio_file,
            ):
                worker_with_temp_h5._process_job(job)

    # Verify job completed
    status = worker_with_temp_h5.get_job_status("test-full-001")
    assert status is not None
    assert status["status"] == "completed"
    assert len(status["chunks"]) == 1
    assert status["chunks"][0]["text"] == "Test transcription"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
