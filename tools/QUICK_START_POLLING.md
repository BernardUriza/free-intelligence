# Quick Start: Transcription Polling Agent

## TL;DR

Monitor transcription job progress in real-time with automatic polling every 15 seconds.

## One-Command Usage

```bash
# Start polling (waits for session_id file automatically)
python3 tools/poll_transcription_progress.py
```

## With Upload Agent (Two Terminals)

```bash
# Terminal 1: Start polling (waits for /tmp/patient_session_id.txt)
python3 tools/poll_transcription_progress.py

# Terminal 2: Upload audio chunks (creates session_id file)
python3 tools/upload_chunks.py /path/to/audio.webm
```

## Manual Test (Existing Session)

```bash
# Write session ID to trigger file
echo "session_20251114_142300" > /tmp/patient_session_id.txt

# Start polling
python3 tools/poll_transcription_progress.py
```

## Output Example

```
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

================================================================================
FINAL REPORT
================================================================================
Session ID:        session_20251114_142300
Final Status:      completed
Total Time:        287.3s (4.8min)
Final Chunks:      62/62
Progress:          100%

Transcript Preview (15234 total chars):
--------------------------------------------------------------------------------
Patient reports experiencing chest pain that started approximately 2 hours ago.
Pain is described as sharp and localized to the left side. No radiation to arm
or jaw. Patient has history of hypertension and is currently taking lisinopril
...
--------------------------------------------------------------------------------
```

## API Endpoint

**Polls:** `GET http://localhost:7001/internal/transcribe/jobs/{session_id}`

## Configuration

Edit `/Users/bernardurizaorozco/Documents/free-intelligence/tools/poll_transcription_progress.py`:

```python
API_BASE = "http://localhost:7001"  # Backend URL
POLL_INTERVAL_SECONDS = 15          # Poll frequency
TIMEOUT_MINUTES = 20                # Max wait time
```

## Prerequisites

- Backend API running on port 7001: `make run`
- Celery worker running: `celery -A backend.workers worker --loglevel=info`
- httpx installed: ✅ (already in pyproject.toml)

## Exit Codes

- `0` = Success (completed)
- `1` = Error (timeout/failure/not found)

## Documentation

- **User Guide:** `tools/README_POLLING.md`
- **Integration Workflow:** `tools/POLLING_WORKFLOW.md`
- **Demo Script:** `tools/test_polling_demo.sh`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Hangs at "Waiting for session ID file" | Check upload agent is running OR manually create file |
| "Job not found" | Wait for first chunk upload OR check backend logs |
| HTTP 500 error | Verify backend is running: `curl http://localhost:7001/health` |
| Timeout after 20min | Check Celery worker OR view worker logs |

## Files

```
tools/
├── poll_transcription_progress.py   # ⭐ Main script
├── test_polling_demo.sh             # Test/demo
├── README_POLLING.md                # Full docs
├── POLLING_WORKFLOW.md              # Integration guide
└── QUICK_START_POLLING.md           # This file

/tmp/
└── patient_session_id.txt           # Trigger (auto-created)
```

## Author

Bernard Uriza Orozco
Created: 2025-11-14
Card: FI-STRIDE polling automation
