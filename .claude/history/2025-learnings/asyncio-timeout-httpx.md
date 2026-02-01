# SSE Streaming Timeout: asyncio.timeout() vs asyncio.wait_for()

**Date:** 2025-12-12
**Context:** Fixing SSE streaming endpoint timeout for Qwen3 models
**File:** `backend/api/public/workflows/assistant/stream.py`

## Problem

The SSE streaming endpoint was hanging indefinitely when Qwen3:4b (a slow "thinking" model) took longer than expected to respond. The `asyncio.wait_for()` timeout was NOT firing, even with short timeout values (5s).

### Observed Behavior
- `asyncio.wait_for(coroutine, timeout=5)` did NOT cancel the httpx request
- curl would wait until its own `--max-time` expired
- Backend logs showed `SSE_TIMEOUT_START` but never `SSE_TIMEOUT_FIRED`

## Root Cause

`asyncio.wait_for()` relies on the awaited coroutine to check for `CancelledError` at await points. When httpx is waiting on a socket read from Ollama, the cancellation signal may not propagate properly because:

1. httpx uses lower-level socket operations that may not yield control back to the event loop frequently
2. The internal `/internal/llm/chat` endpoint has its own blocking behavior waiting on OllamaProvider
3. OllamaProvider has a 120s default timeout that was never reached

## Solution

Replace `asyncio.wait_for()` with `asyncio.timeout()` context manager (Python 3.11+):

```python
# BEFORE (NOT WORKING)
result = await asyncio.wait_for(
    llm_client.chat(...),
    timeout=30,
)

# AFTER (WORKING)
async with asyncio.timeout(30):
    result = await llm_client.chat(...)
```

## Why asyncio.timeout() Works Better

1. **Stricter cancellation**: `asyncio.timeout()` uses a deadline-based approach that's checked by the event loop itself
2. **Better httpx integration**: httpx properly handles the `TimeoutError` raised by the context manager
3. **Immediate cancellation**: The timeout fires at the deadline regardless of what the coroutine is doing

## Code Location

```
backend/api/public/workflows/assistant/stream.py:93-114
```

## Timeout Chain (Reference)

When debugging timeout issues, remember the full chain:

1. **asyncio.timeout()** in `stream.py` - Controls SSE endpoint timeout (now 30s)
2. **httpx.Timeout()** in `InternalLLMClient` - HTTP client timeouts (connect=5s, read=8s)
3. **OllamaProvider timeout** - Default 120s for LLM generation

For the SSE endpoint to timeout properly, the asyncio timeout must be shorter than the httpx read timeout, which must be shorter than the OllamaProvider timeout.

## Testing Commands

```bash
# Test with slow model (should timeout)
curl -N -s --max-time 40 -X POST "http://localhost:7001/api/workflows/aurity/assistant/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:4b","persona":"clinical_advisor","messages":[{"role":"user","content":"Hola"}],"stream":true}'

# Expected output on timeout:
# data: {"id":"...","choices":[{"delta":{"role":"assistant"}}]}
# data: {"id":"...","choices":[{"delta":{"content":"El modelo está tardando..."}}]}
# data: {"id":"...","choices":[{"delta":{},"finish_reason":"stop"}]}
# data: [DONE]
```

## Related Files

- `backend/api/public/workflows/assistant/stream.py` - SSE streaming endpoint
- `backend/clients/internal_llm_client.py` - HTTP wrapper for internal LLM calls
- `backend/providers/llm.py` - OllamaProvider with 120s timeout
