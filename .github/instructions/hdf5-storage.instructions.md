---
applyTo: "backend/storage/**/*.py,backend/workers/**/*.py,backend/services/**/*storage*.py"
---

# HDF5 Event Sourcing Instructions - AURITY

## CRITICAL: Append-Only Pattern

HDF5 files store **immutable clinical data** for HIPAA compliance. All writes MUST be append-only.

### Storage Architecture

- **One HDF5 file per session**: `storage/sessions/{session_id}.h5`
- **Single-writer**: Only one process writes to each file
- **SWMR optional**: Single-Writer-Multiple-Reader for live monitoring
- **Integrity**: SHA256 checksum per session (published in manifest/DB)
- **TTL**: Configurable by session type (e.g., RealtimeTalk ephemeral)

### HDF5 Schema

```
/sessions/{session_id}/
  ├─ tasks/
  │   ├─ TRANSCRIPTION/
  │   │   ├─ chunks/          # Audio chunks
  │   │   ├─ versions/        # Result versions (append-only)
  │   │   │   ├─ 2025-12-07T10:30:00Z
  │   │   │   └─ 2025-12-07T10:35:00Z
  │   │   └─ metadata         # JSON attributes
  │   ├─ DIARIZATION/
  │   │   ├─ chunks/
  │   │   ├─ versions/
  │   │   └─ metadata
  │   ├─ SOAP_GENERATION/
  │   │   ├─ versions/
  │   │   └─ metadata
  │   ├─ EMOTION_ANALYSIS/
  │   │   ├─ versions/
  │   │   └─ metadata
  │   └─ ENCRYPTION/
  │       ├─ versions/
  │       └─ metadata
  ├─ audio/                   # Consolidated audio
  └─ metadata                 # Session-level attributes
```

### Valid Task Types

1. **TRANSCRIPTION** - Speech-to-text conversion
2. **DIARIZATION** - Speaker identification
3. **SOAP_GENERATION** - Medical SOAP notes
4. **EMOTION_ANALYSIS** - Sentiment/emotion detection
5. **ENCRYPTION** - End-to-end encryption metadata

### FORBIDDEN Operations

```python
# ❌ VIOLATION #1 - Deleting data
with h5py.File(path, "r+") as f:
    del f['/sessions/123/tasks/TRANSCRIPTION']  # DESTROYS AUDIT TRAIL

# ❌ VIOLATION #2 - Overwriting data
with h5py.File(path, "r+") as f:
    f['/sessions/123/result'] = new_data  # LOSES HISTORY

# ❌ VIOLATION #3 - Modifying attributes
with h5py.File(path, "r+") as f:
    f.attrs['status'] = 'updated'  # CHANGES IMMUTABLE METADATA
```

### CORRECT: Versioned Append Pattern

```python
from datetime import UTC, datetime
import h5py

def save_transcription_result(session_id: str, result: dict):
    """Save transcription with versioning."""
    timestamp = datetime.now(UTC).isoformat()
    version_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/versions/{timestamp}"

    with h5py.File(CORPUS_PATH, "a") as f:
        # Append new version
        result_json = json.dumps(result, ensure_ascii=False)
        f.create_dataset(
            version_path,
            data=result_json.encode("utf-8"),
            dtype=h5py.special_dtype(vlen=bytes)
        )

        # Update pointer to latest version
        parent = f[f"/sessions/{session_id}/tasks/TRANSCRIPTION"]
        parent.attrs["latest_version"] = timestamp
        parent.attrs["version_count"] = parent.attrs.get("version_count", 0) + 1

    logger.info(
        "transcription_saved",
        session_id=session_id,
        version=timestamp
    )
```

## Atomic Writes

All HDF5 writes MUST use atomic rename pattern to prevent corruption.

```python
import os
import hashlib

def save_session_atomic(session_id: str, audio_data: bytes):
    """Atomic write with integrity verification."""
    final_path = f"storage/sessions/{session_id}.h5"
    temp_path = f"{final_path}.part"

    try:
        # 1. Write to temporary file
        with h5py.File(temp_path, "w", libver="latest") as f:
            f.create_dataset(
                f"/sessions/{session_id}/audio",
                data=audio_data,
                compression="gzip",
                compression_opts=9
            )

            # Add metadata
            f.attrs["session_id"] = session_id
            f.attrs["created_at"] = datetime.now(UTC).isoformat()
            f.attrs["format_version"] = "1.0"

            # Force write to disk
            f.flush()
            os.fsync(f.fileno())

        # 2. Atomic rename (POSIX guarantee)
        os.rename(temp_path, final_path)

        # 3. Calculate and store checksum
        with open(final_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # Store checksum separately
        checksum_path = f"{final_path}.sha256"
        with open(checksum_path, "w") as f:
            f.write(f"{file_hash}  {session_id}.h5\n")
            os.fsync(f.fileno())

        logger.info(
            "session_saved",
            session_id=session_id,
            size_bytes=len(audio_data),
            checksum=file_hash[:16]
        )

    except Exception as e:
        logger.error("session_save_failed", session_id=session_id, error=str(e))
        raise

    finally:
        # Cleanup temporary file if exists
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
```

## Reading Data

### Reading Latest Version
```python
def get_latest_transcription(session_id: str) -> dict | None:
    """Get most recent transcription version."""
    with h5py.File(CORPUS_PATH, "r") as f:
        task_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION"

        if task_path not in f:
            return None

        task_group = f[task_path]
        latest_version = task_group.attrs.get("latest_version")

        if not latest_version:
            return None

        version_path = f"{task_path}/versions/{latest_version}"
        data = f[version_path][()]

        return json.loads(data.decode("utf-8"))
```

### Reading All Versions (Audit Trail)
```python
def get_transcription_history(session_id: str) -> list[dict]:
    """Get full version history for audit."""
    versions = []

    with h5py.File(CORPUS_PATH, "r") as f:
        versions_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/versions"

        if versions_path not in f:
            return versions

        versions_group = f[versions_path]

        for timestamp in sorted(versions_group.keys()):
            data = versions_group[timestamp][()]
            result = json.loads(data.decode("utf-8"))

            versions.append({
                "timestamp": timestamp,
                "data": result
            })

    return versions
```

## SWMR Mode (Single-Writer-Multiple-Reader)

For real-time monitoring while writing:

```python
# Writer process
def write_with_swmr(session_id: str, data: bytes):
    """Write with SWMR enabled for live readers."""
    with h5py.File(CORPUS_PATH, "a", libver="latest", swmr=True) as f:
        f.swmr_mode = True  # Enable SWMR

        chunk_path = f"/sessions/{session_id}/chunks/{chunk_idx}"
        f.create_dataset(chunk_path, data=data)
        f.flush()  # Make visible to readers

# Reader process
def read_with_swmr(session_id: str):
    """Read live data with SWMR."""
    with h5py.File(CORPUS_PATH, "r", libver="latest", swmr=True) as f:
        chunks_path = f"/sessions/{session_id}/chunks"

        if chunks_path in f:
            chunks = f[chunks_path]
            for key in sorted(chunks.keys()):
                yield chunks[key][()]
```

## Compression

```python
# Use compression for large datasets
def save_audio_compressed(session_id: str, audio: bytes):
    with h5py.File(CORPUS_PATH, "a") as f:
        f.create_dataset(
            f"/sessions/{session_id}/audio",
            data=audio,
            compression="gzip",  # or "lzf" for speed
            compression_opts=9,   # max compression
            chunks=True          # Enable chunking
        )
```

## Error Handling

```python
def safe_h5_operation(session_id: str, operation: str):
    """Template for safe HDF5 operations."""
    try:
        with h5py.File(CORPUS_PATH, "a") as f:
            # Perform operation
            result = perform_operation(f, session_id)
            return result

    except OSError as e:
        logger.error(
            "h5_file_error",
            session_id=session_id,
            operation=operation,
            error=str(e)
        )
        raise

    except KeyError as e:
        logger.error(
            "h5_path_not_found",
            session_id=session_id,
            path=str(e)
        )
        return None

    except Exception as e:
        logger.error(
            "h5_operation_failed",
            session_id=session_id,
            operation=operation,
            error=str(e)
        )
        raise
```

## Anti-Patterns

1. ❌ `del f[path]` - Deletes audit trail
2. ❌ `f[path] = data` - Overwrites history
3. ❌ Writing without `.part` + rename
4. ❌ No fsync before rename
5. ❌ No checksum verification
6. ❌ Modifying `attrs` of existing data
7. ❌ Opening with mode `"w"` on existing file

## RealtimeTalk Workflow (Speech → ASR → LLM → TTS)

### Operational Contract

1. **Frontend uploads** `audio/*` → Returns `202 Accepted` + `jobId`
2. **Worker executes** ASR → LLM → TTS pipeline
3. **Persist** to temporary `talk-{session_id}.h5.part` (append-only)
4. **Finalize**: Consolidate 2 messages (user, assistant) to longitudinal chat H5
5. **Cleanup**: Delete temporary H5 file

### Append-Only Events

All events written to `/sessions/{session_id}/realtime_events/` with timestamp keys:

```python
# Event types (chronological order)
events = [
    "user.audio",          # User's audio chunk received
    "asr.partial",         # Partial ASR transcription
    "asr.final",           # Final ASR transcription
    "assistant.delta",     # LLM streaming token
    "assistant.text",      # Complete LLM response
    "tts.audio",          # Generated speech audio
    "interrupt",          # User interrupted assistant
]
```

### Storage Pattern

```python
import h5py
from datetime import UTC, datetime

def save_realtime_event(
    session_id: str,
    event_type: str,
    data: bytes
):
    """Save RealtimeTalk event (append-only)."""
    temp_path = f"storage/talk-{session_id}.h5.part"
    timestamp = datetime.now(UTC).isoformat()

    with h5py.File(temp_path, "a", libver="latest") as f:
        event_path = f"/sessions/{session_id}/realtime_events/{timestamp}"

        f.create_dataset(event_path, data=data)
        f[event_path].attrs["event_type"] = event_type
        f[event_path].attrs["timestamp"] = timestamp

        f.flush()
        os.fsync(f.fileno())

def finalize_realtime_session(session_id: str):
    """Consolidate to main chat H5 and cleanup temp file."""
    temp_path = f"storage/talk-{session_id}.h5.part"
    main_path = f"storage/sessions/{session_id}.h5"

    # Read all events from temporary file
    with h5py.File(temp_path, "r") as temp_f:
        events = temp_f[f"/sessions/{session_id}/realtime_events"]

        # Extract user and assistant messages
        user_message = extract_user_message(events)
        assistant_message = extract_assistant_message(events)

    # Append to main chat history (versioned)
    with h5py.File(main_path, "a") as main_f:
        timestamp = datetime.now(UTC).isoformat()

        main_f.create_dataset(
            f"/sessions/{session_id}/chat/versions/{timestamp}/user",
            data=user_message.encode("utf-8")
        )
        main_f.create_dataset(
            f"/sessions/{session_id}/chat/versions/{timestamp}/assistant",
            data=assistant_message.encode("utf-8")
        )

    # Delete temporary file
    os.remove(temp_path)
    logger.info("realtime_session_finalized", session_id=session_id)
```

### SLO - RealtimeTalk

- **p95 total latency**: ≤ 5000ms (ASR + LLM + TTS combined)
- **Dropout rate**: < 1%
- **Components**:
  - ASR (Deepgram): ~500ms
  - LLM (Claude/Qwen): ~2000ms
  - TTS (Cartesia): ~500ms
  - Overhead: ~500ms

## Success Checklist

- [ ] All writes use versioned paths
- [ ] Atomic rename pattern (`.part` → final)
- [ ] `fsync()` before rename
- [ ] SHA256 checksum calculated
- [ ] `latest_version` pointer updated
- [ ] No `del` operations
- [ ] Compression enabled for large data
- [ ] Error handling with structured logging
- [ ] RealtimeTalk events timestamped with UTC
- [ ] Temporary H5 files cleaned up after finalize
