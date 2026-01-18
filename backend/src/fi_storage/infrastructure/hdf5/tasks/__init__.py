"""Task-based HDF5 repository - Modular facade.

This package provides modular access to task-based HDF5 storage.
All functions are re-exported here for backwards compatibility.

Modules:
  - h5_file_access: Low-level HDF5 file access with SWMR mode
  - lifecycle: Task creation, existence, listing
  - metadata: Task metadata CRUD
  - chunks: Transcription chunk management
  - chunk_audio: Audio blob storage
  - transcription_sources: WebSpeech, full transcription, full audio
  - diarization: Speaker diarization segments
  - soap: SOAP note storage
  - orders: Medical orders CRUD

Author: Bernard Uriza Orozco
Created: 2025-11-14
Refactored: 2026-01-18 (modularization from 2048-line monolith)
"""

from __future__ import annotations

# Re-export CORPUS_PATH from session manager
from backend.src.fi_storage.infrastructure.hdf5.session_h5_manager import CORPUS_PATH

# Chunk audio
from backend.src.fi_storage.infrastructure.hdf5.tasks.chunk_audio import (
    add_audio_to_chunk,
    get_chunk_audio_bytes,
)

# Chunks
from backend.src.fi_storage.infrastructure.hdf5.tasks.chunks import (
    append_chunk_to_task,
    batch_update_chunk_datasets,
    count_task_chunks,
    create_empty_chunk,
    get_task_chunks,
    get_task_transcript,
    update_chunk_dataset,
)

# Diarization
from backend.src.fi_storage.infrastructure.hdf5.tasks.diarization import (
    get_diarization_segments,
    save_diarization_segments,
    update_diarization_segment_text,
)

# H5 file access
from backend.src.fi_storage.infrastructure.hdf5.tasks.h5_file_access import (
    _h5_lock,
    open_h5_read,
    open_h5_write,
)

# Lifecycle
from backend.src.fi_storage.infrastructure.hdf5.tasks.lifecycle import (
    ensure_task_exists,
    list_session_tasks,
    task_exists,
)

# Metadata
from backend.src.fi_storage.infrastructure.hdf5.tasks.metadata import (
    get_task_metadata,
    update_task_metadata,
)

# Orders
from backend.src.fi_storage.infrastructure.hdf5.tasks.orders import (
    create_order,
    delete_order,
    get_orders,
    update_order,
)

# SOAP
from backend.src.fi_storage.infrastructure.hdf5.tasks.soap import (
    get_soap_data,
    save_soap_data,
)

# Transcription sources
from backend.src.fi_storage.infrastructure.hdf5.tasks.transcription_sources import (
    add_full_audio,
    add_full_transcription,
    add_webspeech_transcripts,
)

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
]
