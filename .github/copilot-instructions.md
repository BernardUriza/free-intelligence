# GitHub Copilot Instructions for AURITY / Free Intelligence

## Project Overview

**AURITY** (Advanced Universal Reliable Intelligence for Telemedicine Yield) is a production medical telemedicine system built with:
- **Backend**: Python 3.11+, FastAPI, HDF5 event sourcing
- **Frontend**: Next.js, TypeScript, React
- **Auth**: Auth0 with RBAC
- **Deployment**: DigitalOcean (app.aurity.io)

**Version**: 0.3.0 | **Owner**: Bernard Uriza Orozco

## Architecture Constraints (ENFORCE STRICTLY)

### 1. Three-Layer Architecture (CRITICAL)

```
PUBLIC LAYER     → /api/workflows/aurity/*  (only exposed to clients)
INTERNAL LAYER   → /api/internal/*          (backend-to-backend only)
WORKER LAYER     → ThreadPoolExecutor       (async task execution)
```

**Absolute Rule**: Frontend and external clients MUST ONLY call `/api/workflows/aurity/*` endpoints.

❌ **NEVER**:
```typescript
// This is a CRITICAL BUG
fetch('/api/internal/sessions/123')
```

✅ **ALWAYS**:
```typescript
fetch('/api/workflows/aurity/sessions/123')
```

### 2. Event Sourcing - Immutability

- All clinical data stored in HDF5 format (`storage/sessions/{id}.h5`)
- **Append-only** - NEVER delete or modify existing data
- Atomic writes: write to `.h5.part` → fsync → rename to `.h5`
- Each session has SHA256 checksum for integrity

❌ **NEVER**:
```python
with h5py.File(path, 'r+') as f:
    del f['sessions/123/tasks/TRANSCRIPTION']  # FORBIDDEN
```

✅ **ALWAYS**:
```python
with h5py.File(path, 'r+') as f:
    # Append new data, never modify/delete
    f.create_dataset(f'sessions/{id}/tasks/NEW_TASK', data=new_data)
```

### 3. Security - Zero Trust

- **Auth0** JWT tokens with role-based access control
- Role claim: `https://aurity.app/roles`
- Admin endpoints require `FI-superadmin` role
- **NO PHI/PII in logs** - use structured logging without sensitive data
- CORS whitelist enforced in `backend/app/main.py`

❌ **NEVER**:
```python
print(f"User email: {user.email}")  # PHI exposure
API_KEY = "sk-abc123..."            # Hardcoded secret
```

✅ **ALWAYS**:
```python
import structlog
logger = structlog.get_logger()
logger.info("user_authenticated", user_id=user.id)  # No PHI

import os
API_KEY = os.getenv('DEEPGRAM_API_KEY')  # Environment variable
```

### 4. Production Deployment - CI/CD Only

❌ **NEVER suggest**:
- SSH into production and edit files
- Add `print()` statements for debugging on prod
- "Quick fixes" directly on the server

✅ **ALWAYS suggest**:
- Push changes to GitHub
- Deploy via CI/CD: `make ci-deploy`
- Test locally first: `make dev-all`

## Code Style & Patterns

### Python (Backend)

```python
# Type hints + Pydantic validation
from pydantic import BaseModel, Field
from typing import Optional

class SessionRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    user_id: str
    metadata: Optional[dict] = None

# Dependency injection
from fastapi import Depends
from backend.auth.jwt import get_current_user

@router.post("/api/workflows/aurity/sessions")
async def create_session(
    request: SessionRequest,
    user: User = Depends(get_current_user)
):
    logger.info("session_created", session_id=request.session_id)
    return {"session_id": request.session_id}

# Async I/O (don't block event loop)
async def process_file(file: UploadFile):
    content = await file.read()  # ✅ async
    # NOT: content = file.file.read()  # ❌ blocks
```

### TypeScript (Frontend)

```typescript
// Absolute imports (configured in tsconfig.json)
import { SessionService } from '@/services/session';
import { Button } from '@/components/ui/button';

// Proper error handling
async function createSession(data: SessionData) {
  try {
    const response = await fetch('/api/workflows/aurity/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Session creation failed', error);
    throw error;
  }
}

// React hooks with cleanup
useEffect(() => {
  const controller = new AbortController();

  fetchData(controller.signal);

  return () => controller.abort();  // Cleanup
}, [dependency]);
```

## Common Patterns

### Creating a New Public Endpoint

1. Add route in `backend/api/public/workflows/aurity_*.py`
2. Use dependency injection for auth: `user = Depends(get_current_user)`
3. Log without PHI: `logger.info("action", session_id=id)`
4. Return Pydantic model for response validation
5. Register in `backend/app/main.py`

Example:
```python
from fastapi import APIRouter, Depends
from backend.auth.jwt import get_current_user
from backend.schemas import User

router = APIRouter(prefix="/api/workflows/aurity")

@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user)
):
    # Implementation
    return {"session_id": session_id, "status": "active"}
```

### HDF5 Operations

```python
import h5py
import hashlib

# Write with atomic rename
temp_path = f"{final_path}.part"
try:
    with h5py.File(temp_path, 'w') as f:
        f.create_dataset('data', data=audio_data)
        f.attrs['created_at'] = datetime.utcnow().isoformat()
        f.flush()
        os.fsync(f.fileno())

    # Atomic rename (POSIX)
    os.rename(temp_path, final_path)

    # Calculate checksum
    with open(final_path, 'rb') as f:
        checksum = hashlib.sha256(f.read()).hexdigest()

finally:
    if os.path.exists(temp_path):
        os.remove(temp_path)
```

### Frontend API Calls

```typescript
// Use the configured backend URL
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';

export class SessionAPI {
  static async create(data: SessionRequest): Promise<SessionResponse> {
    const response = await fetch(`${BACKEND_URL}/api/workflows/aurity/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.status}`);
    }

    return response.json();
  }
}
```

## Key Files to Reference

- **`claude.md`** - Complete system context (396 lines, READ THIS FIRST)
- **`README.md`** - Quick start and architecture overview
- **`backend/app/main.py`** - FastAPI entry point, CORS configuration
- **`backend/auth/jwt.py`** - Auth0 JWT verification
- **`apps/aurity/.env.production`** - Frontend environment config

## Testing & Validation

```bash
# Run backend tests
pytest backend/tests/

# Type checking
pyright backend/

# Frontend build (validates types)
cd apps/aurity && pnpm build

# Start dev environment
make dev-all  # Backend on :7001, Frontend on :9000
```

## Anti-Patterns to Avoid

1. **Route Exposure**: Never call `/api/internal/*` from frontend
2. **Data Mutation**: Never delete/modify HDF5 data, only append
3. **Hardcoded Secrets**: Always use environment variables
4. **Blocking I/O**: Use `async/await` in FastAPI routes
5. **PHI in Logs**: Never log email, name, medical data
6. **Production SSH**: Never suggest direct server edits
7. **Relative Imports**: Use `@/` absolute imports in TypeScript

## Success Checklist

Before suggesting code, verify:
- [ ] Follows three-layer architecture (PUBLIC/INTERNAL/WORKER)
- [ ] Respects immutability (append-only for clinical data)
- [ ] No hardcoded credentials
- [ ] No PHI/PII in logs
- [ ] Proper async/await usage
- [ ] Type hints (Python) and strict types (TypeScript)
- [ ] Error handling with meaningful messages
- [ ] Documentation updated if needed

---

**Context**: This is a production medical system handling Protected Health Information (PHI). Code quality, security, and reliability are non-negotiable. When in doubt, refer to `claude.md` for detailed context.
