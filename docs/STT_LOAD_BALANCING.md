# STT Load Balancing - Intelligent Provider Distribution

**Created:** 2025-11-15
**Author:** Bernard Uriza Orozco
**Status:** ⚠️ Updated - Azure Whisper endpoint removed (2025-01-XX)
**Current:** Deepgram-only (load balancer available for future providers)

## Historical Context

Previously, Azure Whisper S0 tier had a strict rate limit:
- **3 requests per minute (RPM)**
- With 4 ThreadPoolExecutor workers, chunks 4+ hit rate limit
- Results in **35-52 second delays** per chunk (waiting for rate limit window)
- Real latency: 52s instead of expected 2-5s

**Solution implemented:** Intelligent Load Balancer that alternated between Azure Whisper and Deepgram.

## Current Status

**Azure Whisper endpoint has been removed** by Microsoft. The system now uses **Deepgram exclusively** as the primary STT provider.

### Current Architecture

```
All chunks → Deepgram (very fast, 1-2s)
```

The load balancer infrastructure remains in place for future multi-provider support.

### Historical Benefits (Before Azure removal)

| Metric | Before | After |
|--------|--------|-------|
| **Avg Latency** | 52s per chunk | 2-3s per chunk |
| **Throughput** | ~1 chunk/min | ~20-30 chunks/min |
| **Azure RPM** | 3 RPM (limit hit) | ~2 RPM (safe) |
| **Cost** | Free (Azure S0) | Free (both free tiers) |

### Current Performance (Deepgram-only)

- **Avg Latency**: 1-2s per chunk
- **Throughput**: ~30-60 chunks/min (no rate limits)
- **Cost**: Free tier (50k minutes/month)

## Implementation

### 1. Load Balancer (`backend/utils/stt_load_balancer.py`)

```python
from backend.utils.stt_load_balancer import get_stt_load_balancer

balancer = get_stt_load_balancer()
provider = balancer.select_provider(chunk_number=5)  # Returns "deepgram"
```

**Features:**
- Thread-safe round-robin selection
- Deterministic chunk-based routing (chunk N % num_providers)
- Auto-detection of available providers (checks env vars)
- Fallback support if provider fails
- Singleton pattern (one instance per app)

### 2. TranscriptionService Integration

```python
# OLD (single provider)
stt_provider = os.environ.get("AURITY_ASR_PROVIDER", "deepgram")

# NEW (load balanced)
load_balancer = get_stt_load_balancer()
stt_provider = load_balancer.select_provider(chunk_number=chunk_number)
```

### 3. Provider Tracking

Each chunk now records which provider was used:

```python
update_chunk_dataset(
    session_id,
    TaskType.TRANSCRIPTION,
    chunk_number,
    "provider",
    stt_provider,  # "azure_whisper" or "deepgram"
)
```

## Configuration

Deepgram must be configured in `.env`:

```bash
# Deepgram (required)
DEEPGRAM_API_KEY=your-key-here
```

**Note:** Azure Whisper configuration is no longer needed (endpoint removed).

**Auto-Detection:**
- If Deepgram configured: Uses Deepgram exclusively
- If not configured: Raises error

## Testing

Run manual test:

```bash
python3 /tmp/test_load_balancer.py
```

Expected output (current):
```
Chunk 0 → deepgram
Chunk 1 → deepgram
Chunk 2 → deepgram
Chunk 3 → deepgram
...
✅ All tests passed!
```

**Note:** Load balancer will return Deepgram for all chunks since Azure Whisper is no longer available.

## Monitoring

Check logs for provider selection:

```bash
tail -f logs/backend-dev.log | grep STT_PROVIDER_SELECTED
```

Example log:
```json
{
  "event": "STT_PROVIDER_SELECTED",
  "provider": "deepgram",
  "chunk_number": 5,
  "index": 1,
  "strategy": "round_robin"
}
```

## Performance Comparison

### Historical Performance (Before load balancing)

```
Chunk 0: 2.5s   (Azure)
Chunk 1: 3.1s   (Azure)
Chunk 2: 2.8s   (Azure)
Chunk 3: 52s    (Azure - RATE LIMITED!)
Chunk 4: 48s    (Azure - RATE LIMITED!)
Chunk 5: 51s    (Azure - RATE LIMITED!)
---
Total: 160s for 6 chunks = 26.6s/chunk avg
```

### Historical Performance (With load balancing - Azure + Deepgram)

```
Chunk 0: 2.5s   (Azure)
Chunk 1: 1.8s   (Deepgram)
Chunk 2: 2.3s   (Azure)
Chunk 3: 1.5s   (Deepgram)
Chunk 4: 2.7s   (Azure)
Chunk 5: 1.9s   (Deepgram)
---
Total: 12.7s for 6 chunks = 2.1s/chunk avg
```

### Current Performance (Deepgram-only)

```
Chunk 0: 1.8s   (Deepgram)
Chunk 1: 1.5s   (Deepgram)
Chunk 2: 1.9s   (Deepgram)
Chunk 3: 1.6s   (Deepgram)
Chunk 4: 1.7s   (Deepgram)
Chunk 5: 1.8s   (Deepgram)
---
Total: 10.3s for 6 chunks = 1.7s/chunk avg
```

**Current: Consistent 1-2s latency, no rate limits** ✅

## Future Enhancements

Potential improvements (not implemented yet):

1. **Multi-Provider Support**
   - Add alternative STT providers (e.g., Google Speech-to-Text, AWS Transcribe)
   - Load balancer infrastructure ready for this

2. **Weighted Load Balancing**
   - Give more traffic to faster/more reliable providers
   - Example: 80% Deepgram, 20% fallback provider

3. **Dynamic Provider Selection**
   - Track latency per provider
   - Route to fastest provider in real-time

4. **Cost-Aware Routing**
   - Route based on cost optimization
   - Use free tier providers first

5. **Circuit Breaker**
   - Auto-disable failing providers
   - Re-enable after cooldown period

## Files Modified

- `backend/utils/stt_load_balancer.py` (NEW)
- `backend/services/transcription_service.py` (updated to use balancer)
- `backend/workers/tasks/transcription_worker.py` (updated to track provider)
- `backend/tests/test_stt_load_balancer.py` (NEW - test suite)
- `docs/STT_LOAD_BALANCING.md` (this document)

## Related

- Rate Limiter: `backend/utils/rate_limiter.py`
- STT Providers: `backend/providers/stt.py`
- Executor Pool: `backend/workers/executor_pool.py`
