# Audit User Tracking - Pending Migration

## Problem

60+ endpoints use `user_id="system"` instead of actual authenticated user.
This breaks audit trail compliance.

## Solution

1. Add `current_user: User = Depends(get_current_user)` to each endpoint
2. Replace `user_id="system"` with `user_id=current_user.id`

## Affected Files (by count)

| File | Occurrences | Priority |
|------|-------------|----------|
| `workflows.py` | 11 | HIGH |
| `diarization.py` | 6 | HIGH |
| `patients.py` | 10 | HIGH |
| `providers.py` | 8 | MEDIUM |
| `finalize.py` | 6 | MEDIUM |
| `tv_content_seeds.py` | 4 | LOW |
| `orders.py` | 4 | MEDIUM |
| `soap.py` | 3 | HIGH |
| `transcription.py` | 2 | MEDIUM |
| `audio.py` | 1 | MEDIUM |
| `transcription_sources.py` | 1 | LOW |
| `triage/router.py` | 2 | LOW |
| `exports/handlers.py` | 3 | LOW |

**Total: 61 occurrences**

## Import Pattern

```python
from backend.infrastructure.auth.adapters.fastapi_adapter import get_current_user, User

# In endpoint signature:
async def my_endpoint(
    ...,
    current_user: User = Depends(get_current_user),
):
    # Use current_user.id instead of "system"
    audit_service.log_action(
        action="something",
        user_id=current_user.id,  # NOT "system"
        ...
    )
```

## Estimated Effort

- **Time**: 4-6 hours
- **Risk**: Medium (may break unauthenticated access patterns)
- **Dependencies**: Ensure all callers pass auth tokens

---
Created: 2026-02-02
Status: PENDING (Mohs 9 - Corindón)
