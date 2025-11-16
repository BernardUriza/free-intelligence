"""Worker tasks module - Modular task implementations."""

from backend.workers.tasks.audit_worker import log_audit_event_worker
from backend.workers.tasks.transcription_worker import transcribe_chunk_worker

__all__ = [
    "transcribe_chunk_worker",
    "diarization_worker",
    "log_audit_event_worker",
]
