# Transcription Performance - Quick Reference Guide

## Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TRANSCRIPTION API                        │
│  /api/transcribe → Direct Whisper transcription (no chunks) │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
   ┌─────────────────┐              ┌──────────────────────┐
   │  Fast Path      │              │  Diarization Path    │
   │  (1-2 min)      │              │  (3-4 min for 10m)   │
   └─────────────────┘              └──────────────────────┘
        ↓                                   ↓
   Whisper ASR                    Split into 30s chunks
   Direct output                  │
                                  ├─ Transcribe each chunk
                                  │  (Whisper)
                                  │
                                  ├─ Classify speaker
                                  │  (LLM - 63% of time!)
                                  │
                                  └─ Merge + store (HDF5)
```

## Performance by Task

### Simple Transcription (`/api/transcribe`)

| Duration | tiny | base | small | medium | large-v3 |
|----------|------|------|-------|--------|----------|
| 1 min    | 0.3s | 0.6s | 1s    | 2.5s   | 5s       |
| 5 min    | 1.5s | 3s   | 5s    | 12s    | 25s      |
| 10 min   | 3s   | 6s   | 10s   | 25s    | 50s      |
| 30 min   | 9s   | 18s  | 30s   | 75s    | 150s     |

**Recommendation:** Use `small` for production (10s for 10 min audio)

### Diarization WITH Speaker Classification

| Duration | Process | Time | RTF  |
|----------|---------|------|------|
| 10 min   | ASR     | 20s  | 0.03 |
| 10 min   | LLM     | 160s | 0.27 |
| 10 min   | Total   | 180s | 0.30 |

**Key:** LLM adds 160 seconds for 10 minutes of audio

### Diarization WITHOUT Speaker Classification

| Duration | Process | Time | RTF  |
|----------|---------|------|------|
| 10 min   | ASR     | 20s  | 0.03 |
| 10 min   | I/O     | 10s  | 0.02 |
| 10 min   | Merge   | 5s   | 0.01 |
| 10 min   | Total   | 35s  | 0.06 |

**Key:** No LLM = 5x faster (35s vs 180s)

## Bottleneck Breakdown (10-min audio with LLM)

```
LLM Classification    ████████████████████ 63% (160s)
Whisper Transcribe    █████████ 27% (60s)
I/O Operations        ████ 13% (30s)
Overhead              ██ 7% (15s)
─────────────────────────────────────────
TOTAL: ~245s (4.1 min, 2.4x realtime)
```

## Quick Performance Tuning

### 3-4x Speedup (Disable LLM)
```bash
export ENABLE_LLM_CLASSIFICATION=false
export FI_ENRICHMENT=off
# 10 min audio → 35s (vs 180s)
```

### 2-3x Speedup (Smaller Model)
```bash
export WHISPER_MODEL_SIZE=base    # 5x faster than small
export WHISPER_MODEL_SIZE=tiny    # 10x faster
# 10 min audio → 60s (vs 180s)
```

### Combined: 7-10x Speedup
```bash
export WHISPER_MODEL_SIZE=base
export ENABLE_LLM_CLASSIFICATION=false
# 10 min audio → 18s (vs 180s)
```

## Configuration Parameters

### Environment Variables (in order of impact)

| Variable | Default | Dev | Prod | GPU |
|----------|---------|-----|------|-----|
| ENABLE_LLM_CLASSIFICATION | true | false | true | true |
| WHISPER_MODEL_SIZE | small | tiny | small | medium |
| WHISPER_COMPUTE_TYPE | int8 | int8 | int8 | float16 |
| WHISPER_DEVICE | cpu | cpu | cpu | mps/cuda |
| DIARIZATION_CHUNK_SEC | 30 | 30 | 30 | 15 |
| DIARIZATION_PARALLEL_CHUNKS | 2 | 1 | 2 | 4 |
| DIARIZATION_LOWPRIO | true | true | true | false |

### Where They Live

```
whisper_service.py (lines 24-31)
├─ WHISPER_MODEL_SIZE
├─ WHISPER_COMPUTE_TYPE
├─ WHISPER_DEVICE
├─ WHISPER_LANGUAGE
├─ ASR_CPU_THREADS
└─ ASR_NUM_WORKERS

diarization_service.py (lines 31-42)
├─ DIARIZATION_CHUNK_SEC
├─ MIN_SEGMENT_SEC
├─ LLM_BASE_URL
├─ LLM_MODEL
├─ LLM_TIMEOUT_MS
├─ FI_ENRICHMENT
└─ ENABLE_LLM_CLASSIFICATION

diarization_service_v2.py (lines 52-55)
├─ DIARIZATION_PARALLEL_CHUNKS
└─ WHISPER_DEVICE

api/diarization.py (lines 51-54)
├─ MAX_DIARIZATION_FILE_MB
├─ DIARIZATION_USE_V2
└─ DIARIZATION_LOWPRIO
```

## Real-World Performance

### Scenario 1: Development (Fast Iteration)
```
Config: tiny + no LLM
10 min audio: 15-20s
30 min audio: 45-60s
→ Use for rapid testing
```

### Scenario 2: Production (DS923+)
```
Config: small + with LLM
10 min audio: 3-4 min
30 min audio: 9-12 min
60 min audio: 18-24 min
→ Standard for NAS deployment
```

### Scenario 3: GPU Available (M1/M2)
```
Config: small/medium + float16
10 min audio: 30-60s
30 min audio: 90-180s
60 min audio: 180-360s
→ Premium performance
```

## File Size Thresholds

```
Size Range      Processing Time    Recommendation
─────────────────────────────────────────────────
< 1 min        Instant (cold-start)   Use directly
1-5 min        10-30s                 Use directly
5-15 min       1-5 min                Use directly
15-60 min      5-20 min               Use low-prio worker
> 60 min       20+ min                Batch/night processing
```

## Architecture Components

### 1. Transcription Service
- **File:** `backend/whisper_service.py`
- **Model:** faster-whisper (singleton, lazy-loaded)
- **Cold start:** 10-30s (first call)
- **Warm start:** 0.5s overhead

### 2. Diarization V2 (Default)
- **File:** `backend/diarization_service_v2.py`
- **Strategy:** Parallel chunk processing (2 at a time)
- **Throughput:** 20 chunks in ~30s (vs V1: 60s sequential)
- **Overhead:** ~7% (context switching, merging)

### 3. Low-Priority Worker
- **File:** `backend/diarization_worker_lowprio.py`
- **Storage:** HDF5 (incremental, persistent)
- **Scheduler:** CPU-aware (only runs when idle >50%)
- **Benefit:** Non-blocking, real-time progress

### 4. Audio Storage
- **Path:** `storage/audio/{session_id}/{timestamp_ms}.{ext}`
- **TTL:** 7 days
- **Manifest:** JSON with SHA256 hash
- **Atomic writes:** fsync + rename

### 5. LLM Speaker Classification
- **Model:** qwen2.5:7b-instruct-q4_0 (default)
- **Backend:** Ollama (http://localhost:11434)
- **Timeout:** 60s (configurable)
- **Impact:** 63% of total diarization time

## Critical Hardcoded Values

These should be environment variables but are currently hardcoded:

1. **Beam size** (whisper_service.py:188)
   ```python
   beam_size=5  # Should be: int(os.getenv("ASR_BEAM", "5"))
   ```
   **Impact:** 10-15% speedup if reduced to 1

2. **Beam size in worker** (diarization_worker_lowprio.py:300)
   ```python
   beam_size=5  # Same issue
   ```

3. **Language auto-detection** (diarization_worker_lowprio.py:298)
   ```python
   language=None  # Should use env var (es for Spanish)
   ```

## Optimization Roadmap

### ✅ Already Done
- V2 pipeline (parallel chunks)
- Low-priority worker (CPU scheduler)
- HDF5 incremental storage
- VAD (silence detection)
- Int8 quantization (CPU)

### 🔧 Quick Wins (No code changes)
1. Disable LLM classification (3-4x speedup)
2. Use smaller model (2-3x speedup)
3. Increase chunk size (25% speedup)

### 📝 Medium-Term (1-2 days)
1. Expose `ASR_BEAM` as environment variable
2. Parallel LLM classification (batch requests)
3. Transcription result caching

### 🚀 Long-Term (1-2 weeks)
1. GPU acceleration (10-20x speedup)
2. Distributed processing (scale to multiple workers)
3. Streaming transcription mode

## Monitoring & Observability

### Metrics to Track

1. **Real-time Factor (RTF)**
   - Definition: processing_time / audio_duration
   - Target: < 1.0 (faster than realtime)
   - Current: 0.30 with LLM, 0.06 without

2. **Chunk Processing Time (seconds)**
   - Whisper per chunk: 0.5-1s for 30s audio
   - LLM per chunk: 8-12s
   - I/O per chunk: 0.5-1s

3. **Job Success Rate**
   - Track failures (LLM timeout, Whisper errors)
   - Alert if >5% failure rate

4. **CPU Usage**
   - Target: < 80% with low-prio worker
   - Alert if > 90%

### Log Locations

All logs contain timing information:
- `CHUNK_TRANSCRIPTION_COMPLETE` - Whisper time
- `LLM_CLASSIFICATION_SUCCESS` - LLM time
- `CHUNK_PROCESSED` - RTF (processing time / duration)
- `DIARIZATION_COMPLETE_V2` - Total time

## Troubleshooting

### Slow Transcription
1. Check model size: `WHISPER_MODEL_SIZE=small` (default is OK)
2. Check CPU usage: Reduce `ASR_CPU_THREADS` if >90%
3. Check VAD: Ensure `ASR_VAD=true` (cuts silence)
4. Check beam size: Currently hardcoded to 5 (reduce to 1 for speed)

### Slow Diarization
1. Disable LLM: `ENABLE_LLM_CLASSIFICATION=false` (60% speedup)
2. Increase chunk size: `DIARIZATION_CHUNK_SEC=45` (25% speedup)
3. Check LLM timeout: `LLM_TIMEOUT_MS=60000` (may be too high)
4. Use low-prio worker: `DIARIZATION_LOWPRIO=true` (non-blocking)

### LLM Timeout Errors
1. Increase timeout: `LLM_TIMEOUT_MS=90000` (90s)
2. Check Ollama: `curl http://localhost:11434/api/tags`
3. Use smaller model: `qwen2.5:3b-instruct` (faster)
4. Disable LLM: `ENABLE_LLM_CLASSIFICATION=false`

---

**Last Updated:** 2025-10-31
**Full Analysis:** See `docs/TRANSCRIPTION_PERFORMANCE_ANALYSIS.md`
