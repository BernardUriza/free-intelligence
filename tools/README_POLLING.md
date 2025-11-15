# Transcription Progress Polling

## Overview

`poll_transcription_progress.py` monitors transcription session progress in real-time by polling the backend API every 15 seconds.

## Usage

### Automatic Mode (with upload agent)

The polling agent automatically waits for `/tmp/patient_session_id.txt` to be created by the upload agent:

```bash
# Terminal 1: Start polling agent (waits for session_id file)
python3 tools/poll_transcription_progress.py

# Terminal 2: Upload chunks (creates session_id file)
python3 tools/upload_chunks.py /path/to/audio.webm
```

### Manual Mode (test with existing session)

```bash
# Write session ID to trigger file
echo "session_20251114_123456" > /tmp/patient_session_id.txt

# Start polling
python3 tools/poll_transcription_progress.py
```

## Configuration

Edit `poll_transcription_progress.py` to customize:

```python
API_BASE = "http://localhost:7001"  # Backend API URL
SESSION_ID_FILE = Path("/tmp/patient_session_id.txt")  # Trigger file
POLL_INTERVAL_SECONDS = 15  # Poll every 15 seconds
TIMEOUT_MINUTES = 20  # Max time to wait
MAX_TRANSCRIPT_PREVIEW = 500  # Chars to show in final report
```

## Output Format

### Progress Updates (every 15s)

```
[14:23:45] Session: session_2025... | Progress: 45% | Chunks: 28/62 | Status: in_progress
[14:24:00] Session: session_2025... | Progress: 67% | Chunks: 42/62 | Status: in_progress
[14:24:15] Session: session_2025... | Progress: 100% | Chunks: 62/62 | Status: completed
```

### Final Report

```
================================================================================
FINAL REPORT
================================================================================
Session ID:        session_20251114_142300
Final Status:      completed
Total Time:        287.3s (4.8min)
Final Chunks:      62/62
Progress:          100%
Created At:        2025-11-14T14:23:00Z
Updated At:        2025-11-14T14:27:47Z

Transcript Preview (15234 total chars):
--------------------------------------------------------------------------------
Patient reports experiencing chest pain that started approximately 2 hours ago.
Pain is described as sharp and localized to the left side. No radiation to arm
or jaw. Patient has history of hypertension and is currently taking lisinopril
...
--------------------------------------------------------------------------------
================================================================================
```

## Exit Codes

- `0`: Transcription completed successfully
- `1`: Error (timeout, failure, or not found)

## API Endpoint

Polls: `GET /api/internal/transcribe/jobs/{session_id}`

Response:
```json
{
  "session_id": "session_20251114_142300",
  "job_id": "session_20251114_142300",
  "status": "in_progress",
  "total_chunks": 62,
  "processed_chunks": 28,
  "progress_percent": 45,
  "chunks": [...],
  "created_at": "2025-11-14T14:23:00Z",
  "updated_at": "2025-11-14T14:24:00Z"
}
```

## Architecture

```
┌─────────────────┐
│ Upload Agent    │ ──┐
│ (Terminal 1)    │   │
└─────────────────┘   │
                      ├─ Writes session_id
                      │
┌─────────────────┐   │
│ Polling Agent   │ ◄─┘
│ (Terminal 2)    │
└────────┬────────┘
         │
         │ Poll every 15s
         ▼
┌─────────────────┐
│ Backend API     │
│ :7001/internal  │
│ /transcribe/    │
└─────────────────┘
```

## Error Handling

- **Job not found**: Waits and retries (job may not exist yet)
- **HTTP errors**: Logged and continues polling
- **Timeout**: Returns final status after 20 minutes
- **Failed status**: Reports failure immediately

## Dependencies

- `httpx`: HTTP client (already in pyproject.toml)
- Python 3.9+

## Example Session

```bash
$ python3 tools/poll_transcription_progress.py

🚀 Transcription Progress Polling Agent
API Base: http://localhost:7001
Session ID File: /tmp/patient_session_id.txt

⏳ Waiting for session ID file: /tmp/patient_session_id.txt
✅ Found session ID: session_20251114_142300

🔄 Starting polling (interval: 15s, timeout: 20min)
================================================================================
[14:23:45] Session: session_2025... | Progress: 0% | Chunks: 0/62 | Status: pending
[14:24:00] Session: session_2025... | Progress: 18% | Chunks: 11/62 | Status: in_progress
[14:24:15] Session: session_2025... | Progress: 35% | Chunks: 22/62 | Status: in_progress
[14:24:30] Session: session_2025... | Progress: 53% | Chunks: 33/62 | Status: in_progress
[14:24:45] Session: session_2025... | Progress: 71% | Chunks: 44/62 | Status: in_progress
[14:25:00] Session: session_2025... | Progress: 89% | Chunks: 55/62 | Status: in_progress
[14:25:15] Session: session_2025... | Progress: 100% | Chunks: 62/62 | Status: completed
================================================================================
✅ COMPLETED in 287.3s

[... Final Report ...]
```

## Notes

- Agent runs independently of upload process
- Safe to kill and restart (reads current state from API)
- Does NOT upload any data (read-only)
- Designed for FI-STRIDE hackathon workflow
