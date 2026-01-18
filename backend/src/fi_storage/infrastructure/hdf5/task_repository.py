"""Task-based HDF5 repository for session data.

REFACTORED: 2026-01-18 - Split from 2048-line monolith into modular packages.
This file is now a thin facade that re-exports all functions from tasks/ submodules.

Philosophy:
  - 1 Session = 1 medical consultation (AURITY)
  - 1 Session → N Tasks (each type appears MAX 1 time)
  - Task = purpose (TRANSCRIPTION, DIARIZATION, etc.)
  - Job = execution metadata (job_id, status, progress)

Storage structure:
  /sessions/{session_id}/tasks/
    ├── TRANSCRIPTION/
    │   ├── chunks/chunk_N/
    │   └── job_metadata.json
    ├── DIARIZATION/
    │   ├── speakers/speaker_N/
    │   ├── segments/segment_N/
    │   └── job_metadata.json
    └── [other tasks...]

Modules:
  - tasks/h5_file_access.py: Low-level HDF5 file access with SWMR mode
  - tasks/lifecycle.py: Task creation, existence, listing
  - tasks/metadata.py: Task metadata CRUD
  - tasks/chunks.py: Transcription chunk management
  - tasks/chunk_audio.py: Audio blob storage
  - tasks/transcription_sources.py: WebSpeech, full transcription, full audio
  - tasks/compat.py: Backwards compatibility with legacy schemas
  - tasks/diarization.py: Speaker diarization segments
  - tasks/soap.py: SOAP note storage
  - tasks/orders.py: Medical orders CRUD

Author: Bernard Uriza Orozco
Created: 2025-11-14
Refactored: 2026-01-18
"""

from __future__ import annotations

from typing import Any

# Re-export everything from the tasks subpackage for backwards compatibility
from backend.src.fi_storage.infrastructure.hdf5.tasks import (
    # Constants
    CORPUS_PATH,
    # H5 file access
    _h5_lock,
    # Chunk audio
    add_audio_to_chunk,
    # Transcription sources
    add_full_audio,
    add_full_transcription,
    add_webspeech_transcripts,
    # Chunks
    append_chunk_to_task,
    batch_update_chunk_datasets,
    count_task_chunks,
    create_empty_chunk,
    # Orders
    create_order,
    delete_order,
    # Lifecycle
    ensure_task_exists,
    get_chunk_audio_bytes,
    # Diarization
    get_diarization_segments,
    get_orders,
    # Compatibility
    get_session_chunks_compat,
    # SOAP
    get_soap_data,
    get_task_chunks,
    # Metadata
    get_task_metadata,
    get_task_transcript,
    list_session_tasks,
    open_h5_read,
    open_h5_write,
    save_diarization_segments,
    save_soap_data,
    task_exists,
    update_chunk_dataset,
    update_diarization_segment_text,
    update_order,
    update_task_metadata,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TASK REPOSITORY CLASS (Implements ITaskRepository interface)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TaskRepository:
    """HDF5-based task repository implementing ITaskRepository interface."""

    def get_task_metadata(self, session_id: str, task_type: str) -> dict[str, Any] | None:
        """Get task metadata."""
        return get_task_metadata(session_id, task_type)

    def task_exists(self, session_id: str, task_type: str) -> bool:
        """Check if task exists."""
        return task_exists(session_id, task_type)

    def ensure_task_exists(
        self, session_id: str, task_type: str, metadata: dict[str, Any] | None = None
    ) -> str:
        """Ensure task exists, create if not."""
        return ensure_task_exists(session_id, task_type, metadata)  # type: ignore[call-arg]

    def get_task_chunks(self, session_id: str, task_type: str) -> list[dict[str, Any]]:
        """Get task chunks."""
        return get_task_chunks(session_id, task_type)

    def save_task_metadata(self, session_id: str, task_type: str, metadata: dict[str, Any]) -> None:
        """Save task metadata."""
        update_task_metadata(session_id, task_type, metadata)

__all__ = [
    # Constants
    "CORPUS_PATH",
    # H5 file access
    "_h5_lock",
    "open_h5_read",
    "open_h5_write",
    # Lifecycle
    "ensure_task_exists",
    "list_session_tasks",
    "task_exists",
    # Metadata
    "get_task_metadata",
    "update_task_metadata",
    # Chunks
    "append_chunk_to_task",
    "batch_update_chunk_datasets",
    "count_task_chunks",
    "create_empty_chunk",
    "get_task_chunks",
    "get_task_transcript",
    "update_chunk_dataset",
    # Chunk audio
    "add_audio_to_chunk",
    "get_chunk_audio_bytes",
    # Transcription sources
    "add_full_audio",
    "add_full_transcription",
    "add_webspeech_transcripts",
    # Compatibility
    "get_session_chunks_compat",
    # Diarization
    "get_diarization_segments",
    "save_diarization_segments",
    "update_diarization_segment_text",
    # SOAP
    "get_soap_data",
    "save_soap_data",
    # Orders
    "create_order",
    "delete_order",
    "get_orders",
    "update_order",
    # Class
    "TaskRepository",
]
