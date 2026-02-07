# Vector Math Utilities

## Architecture Decision: CPU-Only Backend

**Date:** 2026-02-02
**Decision:** Backend uses CPU-only NumPy implementation
**Card:** Vector Math CPU/GPU Separation

### Rationale

1. **Backend never needs GPU**: RAG searches 10-1000 vectors max
2. **CPU batch is fast enough**: 1000 vectors in ~10ms
3. **Deployment savings**: Eliminates ~3GB PyTorch dependency
4. **Fi Monitor handles heavy workloads**: 10000+ vectors with GPU

### Deployment Targets

| Environment | GPU | Implementation | Library |
|------------|-----|----------------|---------|
| Backend (DO) | NO | cpu/vector_utils.py | NumPy |
| Fi Monitor (Windows) | YES | apps/fi-monitor/rag_service/main.py | PyTorch inline |
| Development (Mac) | YES (MPS) | cpu/vector_utils.py | NumPy |

### Performance Notes

CPU batch implementation (`cosine_similarity_batch`):
- 100 vectors: ~1ms
- 1000 vectors: ~10ms
- 10000 vectors: ~100ms

**Backend use case:** RAG search over 10-1000 documents → CPU is sufficient.

**For 10000+ vectors**, use Fi Monitor GPU service.

### Migration from Old Structure

**Before:**
```python
from backend.utils.math.vector_utils import cosine_similarity
```

**After (Option A - Explicit):**
```python
from backend.utils.math.cpu import cosine_similarity
```

**After (Option B - Convenience):**
```python
from backend.utils.math import cosine_similarity  # Re-exported from cpu/
```

The top-level `__init__.py` re-exports CPU functions for convenience.

### Testing

CPU-only tests run in CI/CD without GPU hardware:
```bash
pytest backend/utils/math/cpu/tests/  # Pure NumPy tests
pytest backend/tests/test_no_gpu_dependencies.py  # Verify NO torch
```

### Files

```
backend/utils/math/
├── __init__.py              # Re-exports CPU functions
├── cpu/
│   ├── __init__.py         # CPU module entry point
│   ├── vector_utils.py     # NumPy implementation
│   └── tests/
│       ├── __init__.py
│       └── test_vector_utils.py
└── README.md (this file)
```

**No `gpu/` directory** - Fi Monitor has independent implementation.

### Why No GPU Module?

- Backend (Digital Ocean) has NO GPU hardware
- Fi Monitor already has PyTorch inline implementation
- No code sharing needed (different deployment targets)
- Eliminates confusion about when to use GPU
- Simplifies CI/CD (no GPU required for tests)
