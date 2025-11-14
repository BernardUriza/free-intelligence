#!/usr/bin/env python3
"""Inspect HDF5 architecture - Shows the complete structure with examples.

This script demonstrates the unified architecture for:
- Sessions (medical consultations)
- Jobs (transcription, diarization)
- Transcription sources (3 separate sources)
- Chunks (per-chunk transcripts)
- ML-ready data

Usage:
    python3 tools/inspect_h5_architecture.py

Author: Bernard Uriza Orozco
Created: 2025-11-14
"""

from __future__ import annotations

import json
from pathlib import Path

import h5py


def print_tree(group, prefix="", max_depth=10, current_depth=0):
    """Recursively print HDF5 tree structure."""
    if current_depth >= max_depth:
        print(f"{prefix}... (max depth reached)")
        return

    items = list(group.keys())
    for idx, key in enumerate(items):
        is_last = idx == len(items) - 1
        branch = "└── " if is_last else "├── "
        print(f"{prefix}{branch}{key}", end="")

        item = group[key]
        if isinstance(item, h5py.Group):
            # Show attributes if present
            if len(item.attrs) > 0:
                attrs_str = ", ".join(f"{k}={v}" for k, v in list(item.attrs.items())[:3])
                print(f" (Group, attrs: {attrs_str}...)")
            else:
                print(" (Group)")

            # Recurse into subgroup
            extension = "    " if is_last else "│   "
            print_tree(item, prefix + extension, max_depth, current_depth + 1)
        elif isinstance(item, h5py.Dataset):
            # Show dataset info
            dtype = item.dtype
            shape = item.shape
            size = item.size

            # Try to preview content if small
            preview = ""
            if size < 1000:
                try:
                    data = item[()]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    if isinstance(data, str):
                        # If it's JSON, parse and show keys
                        try:
                            json_data = json.loads(data)
                            if isinstance(json_data, dict):
                                keys = list(json_data.keys())[:5]
                                preview = f", keys: {keys}"
                        except:
                            preview = f", preview: {str(data)[:50]}..."
                except:
                    pass

            print(f" (Dataset, dtype={dtype}, shape={shape}{preview})")


def show_architecture_diagram():
    """Show ASCII diagram of HDF5 architecture."""
    print("\n" + "=" * 80)
    print("HDF5 ARCHITECTURE - Free Intelligence (Unified)")
    print("=" * 80)
    print(
        """
storage/corpus.h5
│
├── /sessions/                              # Main sessions group
│   │
│   └── {session_id}/                       # One session = one medical consultation
│       │
│       ├── metadata.json                   # Session model (Dataset)
│       │   └── {                           # JSON string with:
│       │       "session_id": "uuid",
│       │       "status": "finalized",      # active → finalized → diarized → reviewed → completed
│       │       "created_at": "ISO",
│       │       "updated_at": "ISO",
│       │       "recording_duration": 120.5,
│       │       "total_chunks": 15,
│       │       "encryption_metadata": {    # AES-GCM-256 encryption
│       │           "algorithm": "AES-GCM-256",
│       │           "key_id": "key-abc123",
│       │           "iv": "hex-string",     # Initialization vector
│       │           "encrypted_at": "ISO"
│       │       },
│       │       "transcription_sources": {  # 3 SEPARATE SOURCES (NEW!)
│       │           "webspeech_final": ["text1", "text2"],  # Instant browser previews
│       │           "transcription_per_chunks": [           # High-quality Whisper
│       │               {"chunk_number": 0, "text": "...", "latency_ms": 2500},
│       │               {"chunk_number": 1, "text": "...", "latency_ms": 2400}
│       │           ],
│       │           "full_transcription": "complete text"   # Concatenated final
│       │       },
│       │       "diarization_job_id": "celery-task-id",
│       │       "finalized_at": "ISO",
│       │       "diarized_at": "ISO"
│       │   }
│       │
│       ├── jobs/                           # Jobs for this session
│       │   ├── transcription/
│       │   │   └── {job_id}.json          # TranscriptionJob (Dataset)
│       │   │       └── {
│       │   │           "job_id": "uuid",
│       │   │           "session_id": "uuid",
│       │   │           "job_type": "transcription",
│       │   │           "status": "completed",
│       │   │           "progress_percent": 100,
│       │   │           "total_chunks": 15,
│       │   │           "processed_chunks": 15,
│       │   │           "chunks": [         # Chunk metadata
│       │   │               {
│       │   │                   "chunk_number": 0,
│       │   │                   "status": "completed",
│       │   │                   "transcript": "texto del chunk 0",
│       │   │                   "duration": 8.5,
│       │   │                   "language": "es",
│       │   │                   "confidence": 0.95,
│       │   │                   "audio_quality": 0.87,
│       │   │                   "audio_hash": "sha256",
│       │   │                   "timestamp_start": 0.0,
│       │   │                   "timestamp_end": 8.5,
│       │   │                   "created_at": "ISO"
│       │   │               }
│       │   │           ]
│       │   │       }
│       │   │
│       │   └── diarization/
│       │       └── {job_id}.json          # DiarizationJob (Dataset)
│       │
│       ├── production/                    # Production data (application use)
│       │   └── chunks/
│       │       └── chunk_{N}/             # Per-chunk production data
│       │           ├── transcript         # Dataset: string
│       │           ├── audio_hash         # Dataset: string (SHA256)
│       │           ├── duration           # Dataset: float64
│       │           ├── language           # Dataset: string (es, en)
│       │           ├── timestamp_start    # Dataset: float64
│       │           ├── timestamp_end      # Dataset: float64
│       │           └── created_at         # Dataset: string (ISO)
│       │
│       └── ml_ready/                      # ML training data (separate)
│           └── text/
│               └── chunks/
│                   └── chunk_{N}/         # Per-chunk ML data
│                       ├── transcript     # Dataset: string
│                       ├── audio_hash     # Dataset: string
│                       ├── duration       # Dataset: float64
│                       ├── language       # Dataset: string
│                       ├── confidence     # Dataset: float64
│                       ├── audio_quality  # Dataset: float64
│                       └── created_at     # Dataset: string
│
├── /interactions/                         # LLM interactions (legacy)
├── /embeddings/                           # Vector embeddings (legacy)
└── /metadata/                             # Global metadata (legacy)

KEY CONCEPTS:
═════════════

1. **Session-based architecture**:
   - 1 session = 1 medical consultation
   - Session ID is UUID4 (e.g., "8eb5f521-2dc5-482c-b95f-89bd49778861")

2. **Job types**:
   - TranscriptionJob: 1 per session, tracks all chunks
   - DiarizationJob: 1 per session, runs after finalization

3. **3 Transcription sources** (NEW!):
   - webspeech_final: Instant browser previews (may have errors)
   - transcription_per_chunks: High-quality Whisper per chunk
   - full_transcription: Concatenated final text
   → Stored in session metadata, used by LLM for curated diarization

4. **Dual-write pattern**:
   - production/: Application data (fast access)
   - ml_ready/: ML training data (with confidence, quality metrics)

5. **Encryption**:
   - AES-GCM-256 on session finalization
   - IV (initialization vector) stored in metadata
   - Data becomes immutable after finalization

6. **Lifecycle**:
   ACTIVE → FINALIZED → DIARIZED → REVIEWED → COMPLETED
   (record)  (encrypt)   (speakers)  (approved)  (SOAP)
"""
    )


def inspect_corpus():
    """Inspect actual corpus.h5 file."""
    corpus_path = Path(__file__).parent.parent / "storage" / "corpus.h5"

    if not corpus_path.exists():
        print(f"\n⚠️  Corpus file not found: {corpus_path}")
        return

    print("\n" + "=" * 80)
    print(f"CURRENT CORPUS.H5 STRUCTURE: {corpus_path}")
    print("=" * 80)
    print()

    with h5py.File(corpus_path, "r") as f:
        print_tree(f, max_depth=6)

    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)

    with h5py.File(corpus_path, "r") as f:
        # Count sessions
        if "sessions" in f:
            sessions_group = f["sessions"]
            session_count = len(list(sessions_group.keys()))
            print(f"Total sessions: {session_count}")

            # Show latest session
            if session_count > 0:
                latest_session_id = list(sessions_group.keys())[-1]
                latest_session = sessions_group[latest_session_id]
                print(f"\nLatest session: {latest_session_id}")

                if "metadata" in latest_session:
                    metadata_json = latest_session["metadata"][()]
                    if isinstance(metadata_json, bytes):
                        metadata_json = metadata_json.decode("utf-8")
                    metadata = json.loads(metadata_json)

                    print(f"  Status: {metadata.get('status', 'unknown')}")
                    print(f"  Created: {metadata.get('created_at', 'N/A')}")
                    print(f"  Duration: {metadata.get('recording_duration', 0):.1f}s")
                    print(f"  Chunks: {metadata.get('total_chunks', 0)}")

                    # Show 3 transcription sources
                    ts = metadata.get("transcription_sources", {})
                    if ts:
                        print("\n  Transcription sources:")
                        print(f"    - WebSpeech: {len(ts.get('webspeech_final', []))} items")
                        print(f"    - Chunks: {len(ts.get('transcription_per_chunks', []))} items")
                        print(f"    - Full: {len(ts.get('full_transcription', ''))} chars")

                # Show jobs
                if "jobs" in latest_session:
                    jobs_group = latest_session["jobs"]
                    print("\n  Jobs:")
                    for job_type in jobs_group.keys():
                        job_type_group = jobs_group[job_type]
                        job_count = len(list(job_type_group.keys()))
                        print(f"    - {job_type}: {job_count}")


def show_example_queries():
    """Show example code for common queries."""
    print("\n" + "=" * 80)
    print("EXAMPLE QUERIES (Python)")
    print("=" * 80)
    print(
        """
# 1. Load a session
with h5py.File("storage/corpus.h5", "r") as f:
    session_id = "8eb5f521-2dc5-482c-b95f-89bd49778861"
    metadata_json = f[f"sessions/{session_id}/metadata"][()]
    metadata = json.loads(metadata_json.decode('utf-8'))

    print(f"Status: {metadata['status']}")
    print(f"Encrypted: {metadata.get('encryption_metadata') is not None}")

# 2. Get 3 transcription sources
with h5py.File("storage/corpus.h5", "r") as f:
    session_id = "..."
    metadata = json.loads(f[f"sessions/{session_id}/metadata"][()].decode('utf-8'))

    sources = metadata.get("transcription_sources", {})
    webspeech = sources.get("webspeech_final", [])
    chunks = sources.get("transcription_per_chunks", [])
    full = sources.get("full_transcription", "")

    print(f"WebSpeech items: {len(webspeech)}")
    print(f"Whisper chunks: {len(chunks)}")
    print(f"Full text length: {len(full)}")

# 3. Get transcription job
with h5py.File("storage/corpus.h5", "r") as f:
    session_id = "..."
    job_json = f[f"sessions/{session_id}/jobs/transcription/{session_id}"][()]
    job = json.loads(job_json.decode('utf-8'))

    print(f"Progress: {job['progress_percent']}%")
    print(f"Chunks: {job['processed_chunks']}/{job['total_chunks']}")

# 4. Get chunk transcript (production)
with h5py.File("storage/corpus.h5", "r") as f:
    session_id = "..."
    chunk_idx = 0
    transcript = f[f"sessions/{session_id}/production/chunks/chunk_{chunk_idx}/transcript"][()]

    if isinstance(transcript, bytes):
        transcript = transcript.decode('utf-8')

    print(f"Chunk {chunk_idx}: {transcript}")

# 5. List all sessions
with h5py.File("storage/corpus.h5", "r") as f:
    if "sessions" in f:
        for session_id in f["sessions"].keys():
            metadata = json.loads(f[f"sessions/{session_id}/metadata"][()].decode('utf-8'))
            print(f"{session_id}: {metadata['status']} ({metadata.get('total_chunks', 0)} chunks)")
"""
    )


if __name__ == "__main__":
    show_architecture_diagram()
    inspect_corpus()
    show_example_queries()

    print("\n" + "=" * 80)
    print("✅ Inspection complete")
    print("=" * 80)
