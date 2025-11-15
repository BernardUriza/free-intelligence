# Transcription Polling Workflow

## Complete Integration Flow

### Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                     FI-STRIDE Architecture                      │
└────────────────────────────────────────────────────────────────┘

┌─────────────────┐         ┌──────────────────┐
│  Upload Agent   │────────▶│ /tmp/patient_    │
│  (Terminal 1)   │  Write  │ session_id.txt   │
└─────────────────┘         └────────┬─────────┘
                                     │
                                     │ Read
                                     ▼
                            ┌─────────────────┐
                            │ Polling Agent   │
                            │  (Terminal 2)   │
                            └────────┬────────┘
                                     │
                                     │ Poll every 15s
                                     ▼
                            ┌─────────────────┐
                            │  Backend API    │
                            │  :7001/internal │
                            │  /transcribe    │
                            └────────┬────────┘
                                     │
                                     │ Read/Write
                                     ▼
                            ┌─────────────────┐
                            │  JobRepository  │
                            │  (HDF5 Storage) │
                            └────────┬────────┘
                                     │
                                     │ Process
                                     ▼
                            ┌─────────────────┐
                            │  Celery Worker  │
                            │  (Transcription)│
                            └─────────────────┘
```

## Endpoints Used

### 1. Transcription Job Status (Polling)
**GET** `/internal/transcribe/jobs/{session_id}`

**Response:**
```json
{
  "session_id": "session_20251114_142300",
  "job_id": "session_20251114_142300",
  "status": "pending | in_progress | completed | failed",
  "total_chunks": 62,
  "processed_chunks": 28,
  "progress_percent": 45,
  "chunks": [
    {
      "chunk_number": 0,
      "status": "completed",
      "transcript": "Patient reports...",
      "duration": 4.5,
      "language": "es",
      "confidence": 0.95,
      "audio_quality": "high",
      "timestamp_start": 0.0,
      "timestamp_end": 4.5,
      "created_at": "2025-11-14T14:23:00Z"
    }
  ],
  "created_at": "2025-11-14T14:23:00Z",
  "updated_at": "2025-11-14T14:24:00Z"
}
```

### 2. Individual Chunk Status (Optional)
**GET** `/internal/transcribe/jobs/{session_id}/chunks/{chunk_number}`

**Response:**
```json
{
  "session_id": "session_20251114_142300",
  "chunk_number": 0,
  "status": "completed",
  "transcript": "Patient reports chest pain...",
  "duration": 4.5,
  "language": "es",
  "confidence": 0.95,
  "audio_quality": "high"
}
```

## Step-by-Step Workflow

### Step 1: Start Backend API

```bash
make run
# Or: uvicorn backend.app.main:app --reload --port 7001
```

**Verify:**
```bash
curl http://localhost:7001/health
# Expected: {"status":"ok"}
```

### Step 2: Start Celery Worker (Background)

```bash
# Terminal 3
celery -A backend.workers worker --loglevel=info
```

### Step 3: Start Polling Agent (Waits for session_id)

```bash
# Terminal 2
python3 tools/poll_transcription_progress.py

# Output:
# 🚀 Transcription Progress Polling Agent
# API Base: http://localhost:7001
# Session ID File: /tmp/patient_session_id.txt
#
# ⏳ Waiting for session ID file: /tmp/patient_session_id.txt
```

### Step 4: Start Upload Agent (Creates session_id file)

```bash
# Terminal 1
python3 tools/upload_chunks.py /path/to/audio.webm

# This will:
# 1. Split audio into chunks
# 2. Create session_id
# 3. Write to /tmp/patient_session_id.txt
# 4. Upload chunks to /internal/transcribe/chunks
```

### Step 5: Polling Starts Automatically

```
# Terminal 2 output:
✅ Found session ID: session_20251114_142300

🔄 Starting polling (interval: 15s, timeout: 20min)
================================================================================
[14:23:45] Session: session_2025... | Progress: 0% | Chunks: 0/62 | Status: pending
[14:24:00] Session: session_2025... | Progress: 18% | Chunks: 11/62 | Status: in_progress
[14:24:15] Session: session_2025... | Progress: 35% | Chunks: 22/62 | Status: in_progress
...
[14:25:15] Session: session_2025... | Progress: 100% | Chunks: 62/62 | Status: completed
================================================================================
✅ COMPLETED in 287.3s
```

### Step 6: View Final Report

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

## Manual Testing (Without Upload Agent)

If you want to test polling without uploading chunks:

```bash
# 1. Create a session manually
curl -X POST http://localhost:7001/internal/sessions \
  -H "Content-Type: application/json" \
  -d '{"session_type": "training", "athlete_id": "test_001"}'

# Response: {"session_id": "session_20251114_142300", ...}

# 2. Write session_id to trigger file
echo "session_20251114_142300" > /tmp/patient_session_id.txt

# 3. Run polling agent
python3 tools/poll_transcription_progress.py
```

## Troubleshooting

### Polling Agent Hangs at "Waiting for session ID file"

**Cause:** Upload agent hasn't written `/tmp/patient_session_id.txt` yet

**Solution:**
- Check upload agent is running
- Verify file exists: `ls -la /tmp/patient_session_id.txt`
- Manually create file for testing: `echo "session_xxx" > /tmp/patient_session_id.txt`

### "Job not found yet for session"

**Cause:** Transcription job hasn't been created yet (first chunk not uploaded)

**Solution:**
- Wait for first chunk to upload
- Agent will retry automatically
- Check backend logs: `tail -f backend.log`

### "HTTP error 500"

**Cause:** Backend API error

**Solution:**
- Check backend is running: `curl http://localhost:7001/health`
- View backend logs for errors
- Verify HDF5 file permissions: `ls -la storage/`

### Timeout after 20 minutes

**Cause:** Transcription taking too long or stuck

**Solution:**
- Check Celery worker is running
- View worker logs: `celery -A backend.workers inspect active`
- Check for failed chunks: `curl http://localhost:7001/internal/transcribe/jobs/{session_id}`

## Environment Configuration

### Development (.env.local)

```bash
# Backend API
BACKEND_URL=http://localhost:7001

# Polling settings
POLL_INTERVAL=15
POLL_TIMEOUT_MINUTES=20

# Session ID file location
SESSION_ID_FILE=/tmp/patient_session_id.txt
```

### Production (NAS DS923+)

```bash
# Backend API
BACKEND_URL=http://nas.local:7001

# Longer timeout for production
POLL_INTERVAL=30
POLL_TIMEOUT_MINUTES=60

# Shared storage
SESSION_ID_FILE=/volume1/fi-stride/session_id.txt
```

## Files Created

```
tools/
├── poll_transcription_progress.py   # Main polling agent
├── test_polling_demo.sh             # Demo/test script
├── README_POLLING.md                # User documentation
└── POLLING_WORKFLOW.md              # This file (integration guide)

/tmp/
└── patient_session_id.txt           # Trigger file (created by upload agent)
```

## Performance Metrics

- **Poll Interval:** 15 seconds
- **API Response Time:** < 100ms (p95)
- **Timeout:** 20 minutes (1200 seconds)
- **Max Polls:** ~80 polls (20min / 15s)
- **Network Overhead:** ~8 KB per poll (JSON response)
- **Total Network:** ~640 KB for 80 polls

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success (completed) | ✅ Transcript ready |
| 1 | Timeout or failure | ❌ Check logs |

## Next Steps

1. **Upload Agent:** Create chunk uploader that writes session_id to trigger file
2. **Integration Test:** End-to-end test with real audio
3. **Monitoring:** Add Prometheus metrics for poll latency
4. **Alerting:** Notify on timeout or failure
5. **Dashboard:** Real-time progress visualization

## References

- Backend API: `/Users/bernardurizaorozco/Documents/free-intelligence/backend/api/internal/transcribe/router.py`
- Job Repository: `/Users/bernardurizaorozco/Documents/free-intelligence/backend/repositories/__init__.py`
- Celery Worker: `/Users/bernardurizaorozco/Documents/free-intelligence/backend/workers/transcription_tasks.py`
- Main App: `/Users/bernardurizaorozco/Documents/free-intelligence/backend/app/main.py`
