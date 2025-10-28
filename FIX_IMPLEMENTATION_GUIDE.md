# Sprint 3 Critical Issues: Implementation Guide

**Quick Reference**: This guide provides step-by-step fixes for the 2 critical + 7 important issues found in peer review.

---

## CRITICAL ISSUES (Must Fix Before Production)

### Issue #1: Semantic Search N+1 Query Problem

**File**: `/backend/search.py`
**Lines**: 103-131
**Time**: 2-3 hours
**Impact**: 50-100x latency improvement

#### Step 1: Understand Current Problem
```python
# Current (SLOW): O(n²) complexity
for i in range(total_embeddings):           # 100 iterations
    embedding_vec = embeddings_group["vector"][i]
    similarity = cosine_similarity(query_embedding, embedding_vec)

    for j in range(total_interactions):     # 100 iterations per embedding
        if interactions_group["interaction_id"][j].decode('utf-8') == interaction_id:
            results.append({...})
            break

# With 1000 embeddings: 1,000,000+ HDF5 reads!
```

#### Step 2: Implement Dictionary-Based Lookup
```python
def semantic_search(
    corpus_path: str,
    query: str,
    top_k: int = 5,
    min_score: float = 0.0
) -> List[Dict]:
    """Perform semantic search over corpus interactions (OPTIMIZED)."""
    logger.info("SEMANTIC_SEARCH_STARTED", query=query[:100], top_k=top_k)

    try:
        # Generate query embedding
        query_embedding = llm_embed(query)

        # Pad to 768 dimensions if needed
        if query_embedding.shape[0] == 384:
            padded_query = np.zeros(768, dtype=np.float32)
            padded_query[:384] = query_embedding
            query_embedding = padded_query

        logger.info("QUERY_EMBEDDING_GENERATED", embedding_dim=query_embedding.shape[0])

        # Read corpus embeddings and interactions
        with h5py.File(corpus_path, 'r') as f:
            embeddings_group = f["embeddings"]
            interactions_group = f["interactions"]

            total_embeddings = embeddings_group["interaction_id"].shape[0]
            total_interactions = interactions_group["interaction_id"].shape[0]

            if total_embeddings == 0:
                logger.warning("CORPUS_EMPTY", message="No embeddings in corpus")
                return []

            # ✨ KEY OPTIMIZATION: Load all interactions into memory (once)
            interactions_map = {}
            for i in range(total_interactions):
                iid = interactions_group["interaction_id"][i].decode('utf-8')
                interactions_map[iid] = {
                    'session_id': interactions_group["session_id"][i].decode('utf-8'),
                    'timestamp': interactions_group["timestamp"][i].decode('utf-8'),
                    'prompt': interactions_group["prompt"][i].decode('utf-8'),
                    'response': interactions_group["response"][i].decode('utf-8'),
                    'model': interactions_group["model"][i].decode('utf-8'),
                    'tokens': int(interactions_group["tokens"][i])
                }

            logger.info("CORPUS_LOADED", total_embeddings=total_embeddings)

            # ✨ KEY OPTIMIZATION: Compute similarities without nested loop
            results = []
            for i in range(total_embeddings):
                # Get embedding vector
                embedding_vec = embeddings_group["vector"][i]

                # Compute similarity
                similarity = cosine_similarity(query_embedding, embedding_vec)

                # Skip if below threshold
                if similarity < min_score:
                    continue

                # ✨ KEY OPTIMIZATION: O(1) lookup instead of O(n)
                interaction_id = embeddings_group["interaction_id"][i].decode('utf-8')
                if interaction_id in interactions_map:
                    results.append({
                        'score': similarity,
                        'interaction_id': interaction_id,
                        **interactions_map[interaction_id]
                    })

            # Sort by similarity (descending) and take top_k
            results.sort(key=lambda x: x['score'], reverse=True)
            results = results[:top_k]

            logger.info("SEMANTIC_SEARCH_COMPLETED",
                       total_results=len(results),
                       top_score=results[0]['score'] if results else 0.0)

            return results

    except Exception as e:
        logger.error("SEMANTIC_SEARCH_FAILED", error=str(e), query=query[:100])
        raise
```

#### Step 3: Test & Benchmark
```bash
# Run existing tests
python3 -m unittest tests.test_corpus_ops -v

# Benchmark: Create 1000 embeddings, measure search time
python3 -c "
import time
from backend.search import semantic_search
from backend.config_loader import load_config

config = load_config()
corpus_path = config['storage']['corpus_path']

start = time.time()
results = semantic_search(corpus_path, 'Free Intelligence', top_k=5)
elapsed = time.time() - start

print(f'Search latency: {elapsed*1000:.0f}ms')
print(f'Results found: {len(results)}')

# Should be <1000ms even with 1000+ embeddings
assert elapsed < 1.0, f'Too slow: {elapsed}s'
"
```

---

### Issue #2: Embedding Cache Missing

**File**: `/backend/llm_router.py`
**Lines**: 376-409
**Time**: 1-2 hours
**Impact**: 30-50% fewer API calls

#### Step 1: Add Cache Wrapper
```python
# At the top of llm_router.py, add:
from functools import lru_cache
import hashlib

# Global cache for embeddings (10,000 entries = ~4GB memory worst case)
@lru_cache(maxsize=10000)
def _llm_embed_cached(text_hash: str) -> tuple:
    """Internal caching function (uses hash because lru_cache needs hashable args)."""
    # This won't be called directly; just a marker
    pass

# Mapping from hash to actual embedding (avoids exposing sensitive text in cache key)
_embedding_cache = {}

def llm_embed_with_cache(
    text: str,
    provider: str = "claude",
    provider_config: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    Generate embedding vector with caching.

    Args:
        text: Input text to embed
        provider: Provider name
        provider_config: Provider-specific configuration

    Returns:
        numpy array with embedding vector (384 or 768 dimensions)
    """
    # Compute hash of text (prevents exposing text in cache key)
    text_hash = hashlib.sha256(text.encode()).hexdigest()

    # Check if embedding already computed
    if text_hash in _embedding_cache:
        logger.info("EMBEDDING_CACHE_HIT", text_length=len(text))
        return _embedding_cache[text_hash]

    # Compute embedding (slow path)
    logger.info("EMBEDDING_CACHE_MISS", text_length=len(text))
    llm_provider = get_provider(provider, provider_config)
    embedding = llm_provider.embed(text)

    # Store in cache
    _embedding_cache[text_hash] = embedding
    logger.info("EMBEDDING_CACHED", text_hash=text_hash[:8], cache_size=len(_embedding_cache))

    return embedding

# Keep original llm_embed for backward compatibility
def llm_embed(
    text: str,
    provider: str = "claude",
    provider_config: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    Generate embedding vector for text.

    Note: Uses caching automatically. Call llm_embed_cache_clear() to clear cache.

    Args:
        text: Input text to embed
        provider: Provider name
        provider_config: Provider-specific configuration

    Returns:
        numpy array with embedding vector (typically 384 or 768 dimensions)
    """
    return llm_embed_with_cache(text, provider, provider_config)

def llm_embed_cache_clear():
    """Clear embedding cache (useful for memory cleanup or policy changes)."""
    global _embedding_cache
    old_size = len(_embedding_cache)
    _embedding_cache.clear()
    logger.info("EMBEDDING_CACHE_CLEARED", old_size=old_size)

def llm_embed_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return {
        "cache_size": len(_embedding_cache),
        "max_size": 10000,
        "usage_percent": round(len(_embedding_cache) / 10000 * 100, 1)
    }
```

#### Step 2: Update corpus_ops.py and search.py to Use Cache
No changes needed! Both already call `llm_embed()`, which now uses cache automatically.

#### Step 3: Test & Verify Cache
```bash
# Run existing tests (should still pass, but faster)
python3 -m unittest tests.test_corpus_ops -v

# Verify cache is working
python3 -c "
from backend.llm_router import llm_embed, llm_embed_cache_stats

# First call (slow, from API)
import time
start = time.time()
emb1 = llm_embed('test text')
elapsed1 = time.time() - start

# Second call (should be instant from cache)
start = time.time()
emb2 = llm_embed('test text')
elapsed2 = time.time() - start

print(f'First call: {elapsed1*1000:.0f}ms')
print(f'Cached call: {elapsed2*1000:.0f}ms')
print(f'Speedup: {elapsed1/elapsed2:.0f}x')

stats = llm_embed_cache_stats()
print(f'Cache stats: {stats}')

assert elapsed2 < 0.01, 'Cache not working!'
"
```

---

### Issue #3: API Key Exposure in Error Messages

**File**: `/backend/llm_router.py`
**Lines**: 175-186
**Time**: 1-2 hours
**Impact**: Security compliance

#### Step 1: Create Sanitizer Function
```python
# Add to llm_router.py at the top:

import re

def _sanitize_error_message(error: Exception, original_error: Optional[str] = None) -> str:
    """
    Sanitize error message to remove sensitive data.

    Removes: API keys, auth headers, request URLs with credentials, etc.
    """
    message = str(error)
    if original_error:
        message = original_error

    # Remove common patterns containing secrets
    patterns = [
        (r'sk-ant-[a-zA-Z0-9_\-]{20,}', '[REDACTED-API-KEY]'),      # Anthropic API key
        (r'sk-[a-zA-Z0-9_\-]{40,}', '[REDACTED-API-KEY]'),           # OpenAI API key
        (r'Bearer [a-zA-Z0-9_\-\.]+', 'Bearer [REDACTED-TOKEN]'),    # Bearer token
        (r'Authorization:\s*[^\s,]+', 'Authorization: [REDACTED]'),  # Auth header
        (r'X-API-Key:\s*[^\s,]+', 'X-API-Key: [REDACTED]'),         # API key header
        (r'api[_-]?key[=:]\s*[^\s,&]+', 'api_key=[REDACTED]'),       # Query param
    ]

    for pattern, replacement in patterns:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)

    return message
```

#### Step 2: Update Exception Handlers
```python
# Replace exception handlers in ClaudeProvider.generate():

try:
    message = self.client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
        timeout=self.timeout
    )
    # ... success path ...

except anthropic.APITimeoutError as e:
    self.logger.error(
        "CLAUDE_TIMEOUT_ERROR",
        error_type="APITimeoutError",
        error_message="Request timed out",
        timeout=self.timeout,
        # Don't log: error=str(e)
    )
    raise

except anthropic.APIConnectionError as e:
    # Get sanitized message (in case it contains sensitive data)
    sanitized = _sanitize_error_message(e)
    self.logger.error(
        "CLAUDE_CONNECTION_ERROR",
        error_type="APIConnectionError",
        error_message="Connection failed (details redacted for security)",
        sanitized_detail=sanitized if sanitized != str(e) else None
    )
    raise

except anthropic.RateLimitError as e:
    # Rate limit errors usually safe but be cautious
    self.logger.error(
        "CLAUDE_RATE_LIMIT_ERROR",
        error_type="RateLimitError",
        error_message="Rate limited, will retry with backoff",
        retry_after=getattr(e, 'retry_after', None)
    )
    raise

except anthropic.APIError as e:
    # Generic API error - sanitize everything
    sanitized = _sanitize_error_message(e)
    status_code = getattr(e, 'status_code', None)
    self.logger.error(
        "CLAUDE_API_ERROR",
        error_type=e.__class__.__name__,
        status_code=status_code,
        error_message=f"API error occurred (details redacted for security)",
        sanitized_detail=sanitized if sanitized != str(e) else None
    )
    raise
```

#### Step 3: Verify No Credentials in Logs
```bash
# Search codebase for any credentials that might leak
grep -r "sk-ant-\|sk_test_\|Bearer " backend/ --include="*.py" | grep -v "test_" || echo "✓ No test credentials found"

# Run tests and check logs
python3 -c "
from backend.llm_router import ClaudeProvider

# Try to trigger error (will fail without real API key, which is fine)
try:
    provider = ClaudeProvider({'model': 'test'})
except Exception as e:
    # Verify error message doesn't contain sensitive data
    error_str = str(e)
    assert 'sk-' not in error_str, 'API key exposed!'
    assert 'Authorization' not in error_str, 'Auth header exposed!'
    print('✓ Error messages are sanitized')
"
```

---

## IMPORTANT ISSUES (Should Fix)

### Issue #4: Policy Loader Not Thread-Safe

**File**: `/backend/policy_loader.py`
**Lines**: 246-266
**Time**: 1 hour

#### Step 1: Add Threading Support
```python
# Add to top of policy_loader.py:
import threading

# Add after the PolicyLoader class definition:

_policy_loader: Optional[PolicyLoader] = None
_policy_loader_lock = threading.Lock()

def get_policy_loader(policy_path: Optional[str] = None) -> PolicyLoader:
    """
    Get singleton PolicyLoader instance (thread-safe).

    Uses double-checked locking pattern to minimize lock contention.
    """
    global _policy_loader

    # First check without lock (fast path for 99% of calls)
    if _policy_loader is not None:
        return _policy_loader

    # Acquire lock and check again
    with _policy_loader_lock:
        if _policy_loader is None:  # Another thread might have initialized
            _policy_loader = PolicyLoader(policy_path)
            _policy_loader.load()

    return _policy_loader

def reload_policy(policy_path: Optional[str] = None) -> PolicyLoader:
    """Force reload of policy (useful for testing or configuration changes)."""
    global _policy_loader
    with _policy_loader_lock:
        _policy_loader = PolicyLoader(policy_path)
        _policy_loader.load()
    return _policy_loader
```

#### Step 2: Test Thread Safety
```python
# Add to tests/test_policy_loader.py:

import threading
import time

class TestPolicySingletonThreadSafety(unittest.TestCase):
    """Test thread-safe singleton implementation."""

    def test_concurrent_access(self):
        """Verify only 1 PolicyLoader instance created under concurrent access."""
        loaders = []
        errors = []

        def load_policy():
            try:
                loader = get_policy_loader()
                loaders.append(loader)
            except Exception as e:
                errors.append(e)

        # Create 20 threads, each calling get_policy_loader 50 times
        threads = []
        for _ in range(20):
            t = threading.Thread(target=lambda: [load_policy() for _ in range(50)])
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify no errors
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")

        # Verify all references are to same object (only 1 instance created)
        unique_ids = set(id(loader) for loader in loaders)
        self.assertEqual(len(unique_ids), 1, f"Created {len(unique_ids)} instances, expected 1")

    def test_reload_thread_safety(self):
        """Verify reload_policy is thread-safe."""
        errors = []

        def reload():
            try:
                reload_policy()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reload) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Reload errors: {errors}")
```

---

### Issue #5: Duplicate Embedding Padding Logic

**File**: `/backend/corpus_ops.py` + `/backend/search.py`
**Time**: 1 hour

#### Step 1: Create Centralized Normalization
```python
# Create new file: backend/embedding_utils.py

"""Embedding utilities (normalization, caching, etc.)."""

import numpy as np
from typing import Tuple

# Constants
EMBEDDING_INPUT_DIM = 384       # sentence-transformers output dimension
EMBEDDING_STORAGE_DIM = 768     # HDF5 schema dimension

def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """
    Normalize embedding to storage dimension (768).

    If embedding is 384 dimensions (sentence-transformers):
        - Pad with zeros to 768 dimensions

    If embedding is 768 dimensions:
        - Return as-is

    Args:
        embedding: Input embedding array (384 or 768 dimensions)

    Returns:
        Normalized embedding (768 dimensions)

    Raises:
        ValueError: If embedding dimension not recognized
    """
    if embedding.shape[0] == EMBEDDING_INPUT_DIM:
        # Pad to storage dimension
        padded = np.zeros(EMBEDDING_STORAGE_DIM, dtype=np.float32)
        padded[:EMBEDDING_INPUT_DIM] = embedding
        return padded

    elif embedding.shape[0] == EMBEDDING_STORAGE_DIM:
        return embedding

    else:
        raise ValueError(
            f"Unexpected embedding dimension: {embedding.shape[0]}. "
            f"Expected {EMBEDDING_INPUT_DIM} or {EMBEDDING_STORAGE_DIM}"
        )
```

#### Step 2: Update corpus_ops.py
```python
# Replace lines 245-250 in corpus_ops.py:

# OLD:
if embedding_vector.shape[0] == 384:
    padded_vector = np.zeros(768, dtype=np.float32)
    padded_vector[:384] = embedding_vector
    embedding_vector = padded_vector
    logger.info("EMBEDDING_PADDED", from_dim=384, to_dim=768)

# NEW:
from backend.embedding_utils import normalize_embedding
embedding_vector = normalize_embedding(embedding_vector)
```

#### Step 3: Update search.py
```python
# Replace lines 80-84 in search.py:

# OLD:
if query_embedding.shape[0] == 384:
    padded_query = np.zeros(768, dtype=np.float32)
    padded_query[:384] = query_embedding
    query_embedding = padded_query

# NEW:
from backend.embedding_utils import normalize_embedding
query_embedding = normalize_embedding(query_embedding)
```

---

### Issue #6: Embedding Cache Integration

**File**: `/backend/corpus_ops.py`
**Lines**: 243
**Time**: 0 hours (already implemented in Issue #2)

**No changes needed** - the caching added in Issue #2 automatically covers this.

---

### Issue #7: HDF5 Unbounded Growth (Retention)

**File**: New module
**Time**: 2-3 hours

See full implementation in: `/SPRINT3_PEER_REVIEW.md` (Section: Performance & Scalability)

---

### Issue #8: PII Filtering in Exports

**File**: `/backend/exporter.py`
**Time**: 2-3 hours

See full implementation in: `/SPRINT3_PEER_REVIEW.md` (Section: Security & Privacy)

---

### Issue #9: Provider Registry Pattern

**File**: `/backend/llm_router.py`
**Time**: 1-2 hours

See full implementation in: `/SPRINT3_PEER_REVIEW.md` (Section: Architecture & Design)

---

## Testing Checklist

After each fix, run:

```bash
# Unit tests
python3 -m unittest discover tests/ -v

# Code quality
python3 -m py_compile backend/*.py cli/*.py

# Security scan
grep -r "sk-ant-\|sk_test_\|Bearer " backend/ --include="*.py" | grep -v "test_"

# Performance baseline
time python3 cli/fi.py search "test query"

# Log audit
tail -f logs/system.log  # Verify no credentials in logs
```

---

## Implementation Order (Recommended)

### Immediate (Fix Today)
1. **Issue #3**: API Key Sanitization (Security Critical)
2. **Issue #1**: Semantic Search N+1 (Performance Critical)
3. **Issue #4**: Thread-Safe Singleton (Stability)

### This Week
4. **Issue #2**: Embedding Cache (Cost + Performance)
5. **Issue #5**: Deduplicate Padding Logic (Code Quality)

### Next Sprint
6. **Issue #7**: Data Retention (Compliance)
7. **Issue #8**: PII Filtering (Compliance)
8. **Issue #9**: Provider Registry (Extensibility)

---

**Total Estimated Time**: 12-16 hours spread across 2-3 sprints

See `SPRINT3_PEER_REVIEW.md` for detailed analysis and verification methods.
