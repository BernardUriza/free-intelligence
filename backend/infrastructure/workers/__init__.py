"""FI Workers package - Production-grade worker implementations."""

from backend.infrastructure.workers.executor_pool import spawn_worker
from backend.infrastructure.workers.tasks.audit_worker import log_audit_event_worker
from backend.infrastructure.workers.tasks.diarization_worker import diarize_session_worker
from backend.infrastructure.workers.tasks.soap_worker import generate_soap_worker
from backend.infrastructure.workers.tasks.transcription_worker import transcribe_chunk_worker

__all__ = [
    "diarize_session_worker",
    "generate_soap_worker",
    "log_audit_event_worker",
    "spawn_worker",
    "transcribe_chunk_worker",
]
