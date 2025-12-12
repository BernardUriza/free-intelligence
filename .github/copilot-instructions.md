# GitHub Copilot Instructions for AURITY / Free Intelligence

## Project Overview

**AURITY** (Advanced Universal Reliable Intelligence for Telemedicine Yield) is a production medical telemedicine system built with:
- **Backend**: Python 3.14 ONLY, FastAPI, HDF5 event sourcing
- **Frontend**: Next.js, TypeScript, React
- **Auth**: Auth0 with RBAC
- **Deployment**: DigitalOcean (app.aurity.io)

**Version**: 0.3.0 | **Owner**: Bernard Uriza Orozco

**CRITICAL**: This project uses **Python 3.14 exclusively**. All code must be compatible with Python 3.14 syntax and features. Use modern syntax (union types with `|`, `match/case`, etc.) and always include `from __future__ import annotations` for forward compatibility.

## Owner & Collaboration Style

- Identity: Bernard Uriza Orozco (Founder/Owner). Clinical-grade, reliability-first mindset.
- Personality: Direct, concise, and pragmatic. Prefers actionable fixes over long explanations.
- Communication: Spanish-friendly (concise español ok). Avoid emojis; use app icons and clinical tone.
- Expectations: Proactive changes with clear reasoning, minimal ceremony. Honor SOLID/DRY, security, and privacy.
- Workflow: Move fast but safely. If blocked, propose precise alternatives. Validate with quick tests (`curl`, small unit checks).
- UX Preferences: Clean, accessible UI; collapsable reasoning block; meta-first streaming; zero PHI leakage in logs.

## 📁 Path-Specific Instructions

For detailed, context-specific guidance, see:
- **Python Backend**: `.github/instructions/python-backend.instructions.md`
- **TypeScript Frontend**: `.github/instructions/typescript-frontend.instructions.md`
- **HDF5 Storage**: `.github/instructions/hdf5-storage.instructions.md`
- **Security/HIPAA**: `.github/instructions/security-hipaa.instructions.md`

## Quick Reference

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

    ## UX Reasoning & Streaming Guidelines (2025-12-12)

    ### Product & UX Principles
    - Reasoning Visibility: Render “Thinking” (model reasoning) as a collapsable block above assistant content.
    - Privacy by Default: Do not persist “Thinking” in logs/analytics; show only in UI for live sessions.
    - Accessibility: Keyboard navigable, ARIA-annotated toggle; avoid semantic ambiguity.
    - No Emojis: Use app’s icon set for visual affordances; keep typography clean.

    ### Streaming Contract (SSE)
    - Ordering: Emit `event: meta` with `{"thinking": "<string>"}` first when available; stream `content` chunks afterward; then `finish_reason: "stop"` and `data: [DONE]`.
    - No Placeholders: Do not emit placeholder meta or typing deltas; only send real provider signals.
    - Timeouts: If upstream doesn’t return content within the configured guard, finish cleanly with `stop` + `[DONE]` and a concise message.
    - Performance: Chunk size ≥ 60 chars, no artificial delays; cap initial `max_tokens` for `qwen3*` (e.g., 128) to reduce latency.

    ### Frontend UI Guidelines
    - ReasoningBlock: Collapsable component placed before assistant content; default collapsed; preserves whitespace; uses app icons (e.g., “insight” icon) for the toggle.
    - Message Anatomy (Reusable Naming):
      - Header: role, timestamp, indicators (streaming/finished).
      - Meta: optional `thinking` block (collapsable).
      - Body: streamed `content` concatenated in order.
      - Footer: actions (copy, cite), status indicators (done/timeout).
    - State Management:
      - On `event: meta`: attach `thinking` to the current assistant message; do not append to `content`.
      - On `data` with `delta.content`: append to `content` buffer.
      - On final `finish_reason`: mark message complete; stop stream.
    - Error UX: Show concise inline status (e.g., “El modelo tardó más de lo esperado…”), keep session responsive, allow retry.

    ### Backend Architecture (SOLID/DRY)
    - Three-Layer Rule: Frontend must only call `/api/workflows/aurity/*`; internal routes remain private.
    - Provider Logic:
      - Qwen3: use generate endpoint with `think:true`; map provider `thinking` to `metadata.thinking`; never log the raw reasoning.
      - Respect `model` override passed via public → internal → provider; policy defaults are advisory.
    - Streaming Endpoint:
      - Emit role chunk, real meta only if present, content chunks, final stop, `[DONE]`.
      - Guard with `asyncio.wait_for`; on timeout or empty response, finish gracefully.
    - Code Quality:
      - Python 3.14, `from __future__ import annotations`.
      - Type-safe DTOs; clear dependency injection; redaction for sensitive data.
      - No PHI/PII in logs; structured logging with request_id; environment-based secrets.

    ### Security & Compliance
    - Zero Trust: Auth0 JWT with RBAC; no internal route exposure.
    - PHI Safety: Never log names/emails/medical data; use hash/length for diagnostics.
    - Config Hygiene: All secrets via env; no hardcoding.

    ### Testing & Validation
    - SSE Curl: Validate meta-first ordering and clean termination:
      - `curl -N -s -X POST "${BACKEND_URL}/api/workflows/aurity/assistant/chat/stream" -H "Content-Type: application/json" -d '{"model":"qwen3:4b","persona":"clinical_advisor","messages":[{"role":"user","content":"Explica qué es la fiebre"}],"stream":true}'`
    - Internal Debug: Confirm model and presence of `thinking` via `/internal/llm/chat/debug`.

    ### Curl Recipes (zsh-friendly)
    - Stream Assistant (SSE, meta first):
      - `curl -N -s -X POST "${BACKEND_URL:-http://localhost:7001}/api/workflows/aurity/assistant/chat/stream" -H "Content-Type: application/json" -d '{"model":"qwen3:4b","persona":"clinical_advisor","messages":[{"role":"user","content":"Explica qué es la fiebre"}],"stream":true}'`
    - Stream + Inspect first lines:
      - `curl -N -s -X POST "${BACKEND_URL:-http://localhost:7001}/api/workflows/aurity/assistant/chat/stream" -H "Content-Type: application/json" -d '{"model":"qwen3:4b","persona":"clinical_advisor","messages":[{"role":"user","content":"Explica qué es la fiebre"}],"stream":true}' | sed -n '1,60p'`
    - Internal Debug (thinking vs response):
      - `curl -s -X POST "${BACKEND_URL:-http://localhost:7001}/internal/llm/chat/debug" -H "Content-Type: application/json" -d '{"persona":"clinical_advisor","message":"¿Qué es la fiebre?","context":{"model":"qwen3:4b"},"provider":"ollama"}' | jq '{thinking, response, model, provider, latency_ms, metadata_keys}'`
    - Timeout Path Validation:
      - Expect role → optional meta → concise timeout message → stop → `[DONE]` within configured seconds.
    - Notes:
      - Use `-N` to disable buffering; `-s` for silent progress; pipe to `sed`/`jq` to inspect.
      - On macOS zsh, quote JSON payloads with single quotes; escape inner quotes properly.

    ### Content & Style
    - Tone: Clinical, clear, precise; no emojis.
    - Icons: Use app’s icon components for affordances (collapse/expand, copy, status).
    - Reusability: Follow the message anatomy naming across components, tests, and telemetry.

    ### Success Criteria
    - Meta-first reasoning appears as a collapsable block with no placeholders.
    - Stream never hangs: always finishes with stop + `[DONE]` or returns content quickly.
    - Requested model (`qwen3*`) honored end-to-end when specified.
    - No PHI in logs; UI responsive and accessible.

    ## Additional Context & Guardrails (2025-12-12)

    ### Architecture Guardrails
    - Three-Layer Enforcement: PUBLIC `/api/workflows/aurity/*` → INTERNAL `/api/internal/*` → WORKER pool. The frontend must never call internal routes directly.
    - Dependency Injection: Access Auth, Persona, Memory, and Provider via injected services; avoid tight coupling or singletons leaking across layers.
    - DRY: Centralize streaming, persona prompts, and provider routing; prefer shared helpers over duplicating logic per endpoint.

    ### Provider & Model Selection
    - Qwen3 `thinking`: Use Ollama `/api/generate` with `think:true` to surface reasoning cleanly; map to `LLMResponse.metadata.thinking`.
    - Model Override: Honor `request.model` end-to-end (public → internal → provider). Policy defaults are advisory, not mandatory.
    - Fallback Models: If `qwen3*` unavailable, gracefully fall back (e.g., `qwen2:1.5b-instruct`) and disable `thinking` block; still stream content promptly.

    ### Logging, Privacy, and PHI
    - Structured Logging: Use `request_id` and redact content; log lengths/hashes, not raw text.
    - No PHI: Never log names, emails, medical content, or raw reasoning. Prefer `hash8`, `length`, and `truncated_preview` (≤ 60 chars) when necessary.
    - Error Redaction: Sanitize API keys and bearer tokens; keep errors concise and actionable.

    ### Frontend Components & Naming
    - Components: `ReasoningBlock`, `MessageHeader`, `MessageBody`, `MessageFooter` with consistent props and test IDs.
    - Accessibility: Toggle is focusable; `aria-expanded`, `aria-controls`; keyboard navigation (Enter/Space); no emoji usage.
    - State: `message.metadata.thinking` attached via `event: meta`; `message.content` grows via streamed deltas; final stop marks completion.

    ### Performance & Resilience
    - Stream Chunking: ≥ 60 chars; avoid artificial delays; flush quickly.
    - Token Caps: For `qwen3*`, start with `max_tokens <= 128`; adjust based on latency.
    - Timeout Guards: Use `asyncio.wait_for` around internal calls; on timeout, stream a brief message and finish cleanly.
    - Empty Response Handling: If only `thinking` arrives, emit meta then finish (`stop` + `[DONE]`) without hanging.

    ### Testing Recipes
    - SSE Happy Path: Meta-first, then content, then stop + `[DONE]`.
    - SSE Timeout Path: Role → (optional meta) → concise timeout message → stop + `[DONE]`.
    - Internal Debug: `/internal/llm/chat/debug` confirms `model` and `thinking` propagation.
    - Frontend E2E: Verify `ReasoningBlock` renders real thinking only; ensure copy actions and status indicators work.

    ### Failure Modes & Mitigations
    - Model Mismatch: If internal flow picks a different model, ensure context `model` wins; log both requested/effective.
    - Provider Unavailable: Circuit breaker in Ollama; show concise UI status and allow retry.
    - Long Thinking, No Content: Emit real meta only; finish cleanly if content doesn’t arrive within timeout.

    ### Style & Tone
    - Clinical, direct, precise; short sentences; no marketing.
    - Icons from app library for affordances; no emojis.
    - Reusable naming across components, tests, telemetry for maintainability.
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

## Kernel Context Highlights (from `claude.md`)

- **Layering & Routes**: PUBLIC `/api/workflows/aurity/*` only; INTERNAL `/api/internal/*` blocked by `InternalOnlyMiddleware`; WORKER via `ThreadPoolExecutor`.
- **Production URLs**: Frontend `https://app.aurity.io`; Backend base `https://app.aurity.io/api/`; Nginx terminates SSL and proxies `/api/*` to FastAPI:7001.
- **CORS**: Allowed origins include `http://localhost:9000`, `http://localhost:9050`, `https://app.aurity.io` (see `backend/app/main.py`).
- **Storage (HDF5) Invariants**: One `.h5` per session; append-only; SHA256 integrity per session; atomic write via `.h5.part` → fsync → rename; SWMR for live read optional; task types include TRANSCRIPTION, DIARIZATION, SOAP_GENERATION, EMOTION_ANALYSIS, ENCRYPTION.
- **RealtimeTalk Pipeline**: Frontend uploads audio; worker performs ASR→LLM→TTS, persists to `talk-<sid>.h5.part`; finalize consolidates messages to longitudinal H5 and deletes temp. Events: `user.audio`, `asr.partial`, `asr.final`, `assistant.delta`, `assistant.text`, `tts.audio`, `interrupt`.
- **Security Policies**:
  - Zero Trust + RBAC (Auth0) with roles claim `https://aurity.app/roles`; ADMIN requires `FI-superadmin`.
  - Production SSH: strictly read-only; no edits, installs, or quick fixes; all deploys via CI/CD. Claude must never suggest direct prod changes; always suggest GitHub + CI.
  - Secret Management: never commit or document real keys/tokens; use env vars and `.env.example`; sanitize logs and errors; rotate if exposure suspected.
- **SLOs & Observability**: PUBLIC API p95 ≤ 800ms (<1% errors); RealtimeTalk p95 ≤ 5s; SOAP Gen p95 ≤ 1500ms. Dashboards and alerts enforce SLOs; tracing uses `workflow_id`, `session_id`, `idempotency_key`.
- **Dev & Ops**: `make dev-all`, `make test`, `make type-check`, `pnpm dev`; production deploy via scripts under `/scripts` (reverse proxy, HTTPS setup).
- **Repo Layout**: FastAPI entry at `backend/app/main.py`; PUBLIC routes in `backend/api/public/workflows`; INTERNAL in `backend/api/internal`; HDF5 ops in `backend/storage`.
- **Frontend Primitives**: Chat widget supports modes, autoscroll, response_mode; uses absolute imports `@/`; banner communicates policy.
- **Troubleshooting**: Clear caches, enforce absolute imports, verify Auth0 role claim, use local refs for scroll, free ports.
- **Conventions & Communication**: Prefer technical bullets, executable docs, Conventional Commits + Task IDs; keep markdown length reasonable except for key files.

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
