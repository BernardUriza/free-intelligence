# AURITY Backend API Architecture

**Last Updated**: 2025-12-08
**Status**: Production
**Owner**: Backend Team

---

## Table of Contents
1. [Overview](#overview)
2. [Three-Layer Architecture](#three-layer-architecture)
3. [API Endpoints](#api-endpoints)
4. [Router Organization](#router-organization)
5. [Security & RBAC](#security--rbac)
6. [Developer Guidelines](#developer-guidelines)

---

## Overview

AURITY backend follows a **strict three-layer architecture** to enforce separation of concerns and security boundaries:

### Core Principles
1. **Layer Isolation**: PUBLIC → INTERNAL → WORKER (no layer skipping)
2. **Single Responsibility**: Each router handles one functional domain
3. **Type Safety**: Pydantic models for all requests/responses
4. **Immutability**: HDF5 append-only storage (event sourcing)
5. **Security**: RBAC + InternalOnlyMiddleware + Auth0 JWT

### Technology Stack
- **Framework**: FastAPI 0.100+
- **Auth**: Auth0 (OAuth2 + OIDC)
- **Storage**: HDF5 (clinical data), PostgreSQL (patients/providers)
- **AI**: Anthropic Claude (assistant), Deepgram (transcription)
- **Language**: Python 3.14 (ONLY)

---

## Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  PUBLIC LAYER (/api/*)                                       │
│  ─────────────────────────────────────────────────────────  │
│  - CORS enabled                                              │
│  - Frontend-facing                                           │
│  - Orchestration logic only                                  │
│  - Calls INTERNAL layer for atomic operations                │
│  - Examples: /api/workflows/aurity/sessions                  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  INTERNAL LAYER (/internal/*)                                │
│  ─────────────────────────────────────────────────────────  │
│  - Localhost-only in production (InternalOnlyMiddleware)     │
│  - Atomic operations (single responsibility)                 │
│  - Called by PUBLIC layer or WORKER layer                    │
│  - Examples: /internal/sessions, /internal/transcribe        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  WORKER LAYER (ThreadPoolExecutor)                           │
│  ─────────────────────────────────────────────────────────  │
│  - Background tasks (diarization, LLM processing)            │
│  - No HTTP exposure                                          │
│  - Calls INTERNAL layer for data persistence                 │
│  - Examples: DiarizationWorker, SOAPWorker                   │
└─────────────────────────────────────────────────────────────┘
```

### ❌ CRITICAL RULE
**Frontend and external clients MUST ONLY call `/api/*` endpoints.**

```python
# ❌ FORBIDDEN (frontend calling internal API)
fetch('/api/internal/sessions/123')  # SECURITY VIOLATION

# ✅ CORRECT (frontend calling public API)
fetch('/api/workflows/aurity/sessions/123')
```

---

## API Endpoints

### Public API Structure

All public endpoints are mounted under `/api`:

```
/api
├── /workflows/aurity/*           # AURITY medical workflows
│   ├── /stream                   # Audio transcription
│   ├── /jobs/{session_id}        # Transcription status
│   ├── /sessions                 # Session listing
│   ├── /sessions/{id}/*          # Session operations
│   ├── /assistant/*              # AI assistant endpoints
│   ├── /soap/*                   # SOAP notes CRUD
│   ├── /timeline/*               # Longitudinal memory
│   └── /kpis                     # System metrics
│
├── /patients                     # Patient demographics (PostgreSQL)
├── /providers                    # Provider credentials (PostgreSQL)
├── /audit                        # Audit logs (HIPAA)
├── /policy                       # Policy configuration
├── /admin/personas               # AI persona management
├── /system/health                # System health check
├── /tts                          # Text-to-speech
├── /checkin                      # Patient check-in
├── /payments                     # Stripe payments
├── /clinics                      # Clinic/doctor management
└── /notifications                # SMS/email notifications
```

### Internal API Structure

All internal endpoints are mounted under `/internal` (localhost-only in production):

```
/internal
├── /audit                        # Audit logging operations
├── /diarization                  # Speaker diarization
├── /exports                      # Export generation
├── /kpis                         # KPI calculations
├── /sessions                     # Session atomic operations
├── /transcribe                   # Transcription processing
├── /triage                       # Triage buffer management
└── /llm                          # LLM provider abstraction
```

---

## Router Organization

### File Structure

```
backend/api/
├── __init__.py
├── public/                       # PUBLIC LAYER
│   ├── __init__.py
│   ├── audit.py                  # /api/audit/*
│   ├── patients.py               # /api/patients
│   ├── providers.py              # /api/providers
│   ├── policy.py                 # /api/policy
│   ├── personas_admin.py         # /api/admin/personas
│   ├── tts.py                    # /api/tts
│   ├── checkin.py                # /api/checkin
│   ├── payments.py               # /api/payments
│   ├── clinics.py                # /api/clinics
│   ├── notifications.py          # /api/notifications
│   ├── system/
│   │   ├── __init__.py
│   │   └── router.py             # /api/system/*
│   └── workflows/                # AURITY medical workflows
│       ├── __init__.py
│       ├── router.py             # Main aggregator (/workflows/aurity)
│       ├── transcription.py      # Audio upload + streaming
│       ├── sessions.py           # Session lifecycle
│       ├── soap.py               # SOAP notes CRUD
│       ├── assistant.py          # AI chat endpoints
│       ├── assistant_history.py  # Conversation search
│       ├── assistant_websocket.py # Real-time chat
│       ├── timeline.py           # Session listing
│       ├── longitudinal_memory.py # Unified memory API
│       ├── evidence.py           # Evidence pack generation
│       ├── documents.py          # Knowledge base
│       ├── orders.py             # Medical orders
│       ├── kpis.py               # System metrics
│       ├── widget_configs.py     # TV widget configs
│       ├── tv_content_seeds.py   # TV content management
│       ├── waiting_room.py       # Waiting room queue
│       ├── clinic_media.py       # Clinic media assets
│       └── emotional_analysis.py # Emotional context
│
└── internal/                     # INTERNAL LAYER
    ├── __init__.py
    ├── admin/
    │   └── users.py              # Auth0 user management
    ├── audit/
    │   └── router.py             # /internal/audit/*
    ├── diarization/
    │   ├── __init__.py
    │   └── status.py             # /internal/diarization/*
    ├── sessions/
    │   ├── __init__.py
    │   ├── router.py             # /internal/sessions/*
    │   ├── checkpoint.py         # Incremental audio concat
    │   ├── checkpoint_logic.py
    │   ├── checkpoint_models.py
    │   └── finalize.py           # Encryption + diarization
    ├── timeline/
    │   └── router.py             # /internal/timeline/*
    ├── transcribe/
    │   └── router.py             # /internal/transcribe/*
    ├── triage/
    │   └── router.py             # /internal/triage/*
    ├── kpis/
    │   └── router.py             # /internal/kpis/*
    └── llm/
        ├── __init__.py
        ├── router.py             # /internal/llm/*
        ├── chat.py               # Chat completions
        ├── structured.py         # Structured output
        └── schemas.py            # Pydantic models
```

### Router Mounting Pattern

All routers follow this pattern in `backend/app/main.py`:

```python
# PUBLIC API (CORS enabled)
public_app = FastAPI(title="Public API")
public_app.add_middleware(TracingMiddleware)
public_app.add_middleware(CORSMiddleware, ...)
public_app.add_middleware(IdempotencyMiddleware, ...)

# Include public routers
public_app.include_router(auth_router)
public_app.include_router(workflows.router)  # /workflows/aurity
public_app.include_router(patients.router)   # /patients
# ... etc

# INTERNAL API (localhost-only)
internal_app = FastAPI(title="Internal API")
internal_app.add_middleware(TracingMiddleware)
internal_app.add_middleware(InternalOnlyMiddleware)  # 🔒 CRITICAL

# Include internal routers
internal_app.include_router(sessions.router, prefix="/sessions")
internal_app.include_router(transcribe.router, prefix="/transcribe")
# ... etc

# Mount sub-apps
app.mount("/api", public_app)
app.mount("/internal", internal_app)
```

### Workflow Sub-Router Pattern

The AURITY workflows follow a modular SOLIS architecture:

```python
# backend/api/public/workflows/router.py
router = APIRouter(prefix="/workflows/aurity", tags=["workflows-aurity"])

# Include sub-routers (each handles one domain)
router.include_router(transcription.router, tags=["Transcription"])
router.include_router(sessions.router, tags=["Sessions"])
router.include_router(soap.router, tags=["SOAP Notes"])
router.include_router(assistant.router, tags=["AI Assistant"])
# ... etc
```

**Benefits**:
- Each sub-router is ~200-500 lines (vs 2175 line monolith)
- Independent testing
- Clear responsibility boundaries
- Easy to add new workflows

---

## Security & RBAC

### Auth0 Integration (HIPAA G-003)

All protected endpoints use JWT authentication:

```python
from backend.auth.jwt import get_current_user, require_roles

@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user)  # ✅ Auth required
):
    # User authenticated
    pass

@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    user: User = Depends(require_roles(["FI-superadmin"]))  # ✅ Role check
):
    # Only superadmins can delete users
    pass
```

### Role Hierarchy

Defined in `backend/auth/jwt.py`:

```python
ROLES = {
    "FI-superadmin": ["FULL_ACCESS"],  # God mode
    "ADMIN": ["MANAGE_USERS", "MANAGE_CLINICS"],
    "MEDICO": ["CREATE_SESSIONS", "VIEW_PATIENTS"],
    "STAFF": ["VIEW_SESSIONS"],
}
```

### CORS Configuration

**Production** (strict):
```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS")  # Must be explicitly set
# Example: "https://app.aurity.io,https://staging.aurity.io"
```

**Development** (permissive):
```python
allowed_origins = [
    "http://localhost:9000",   # Aurity frontend
    "http://localhost:3000",   # Next.js dev
]
```

### InternalOnlyMiddleware

Blocks external access to `/internal/*` in production:

```python
# backend/middleware/internal_only.py
class InternalOnlyMiddleware:
    async def __call__(self, scope, receive, send):
        if not self._is_localhost(client_host):
            # 403 Forbidden
            raise HTTPException(status_code=403)
```

---

## Developer Guidelines

### Adding a New Public Endpoint

1. **Choose the right file**:
   - General CRUD → `backend/api/public/{resource}.py`
   - Workflow-specific → `backend/api/public/workflows/{workflow}.py`

2. **Define Pydantic models**:
   ```python
   from pydantic import BaseModel, Field

   class CreateSessionRequest(BaseModel):
       patient_id: str = Field(..., min_length=1)
       provider_id: str

   class SessionResponse(BaseModel):
       session_id: str
       status: str
       created_at: str
   ```

3. **Create the endpoint**:
   ```python
   from fastapi import APIRouter, Depends, HTTPException
   from backend.auth.jwt import get_current_user

   router = APIRouter(prefix="/sessions", tags=["Sessions"])

   @router.post("", response_model=SessionResponse, status_code=201)
   async def create_session(
       request: CreateSessionRequest,
       user: User = Depends(get_current_user)
   ):
       logger.info("session_created", session_id=session_id)  # No PHI
       # Implementation
       return SessionResponse(...)
   ```

4. **Register in `main.py`**:
   ```python
   from backend.api.public import my_router
   public_app.include_router(my_router.router)
   ```

5. **Test**:
   ```bash
   # Unit test
   pytest backend/tests/api/public/test_my_router.py

   # Integration test (local)
   curl -X POST http://localhost:7001/api/sessions \
     -H "Content-Type: application/json" \
     -d '{"patient_id":"P123","provider_id":"D456"}'
   ```

### Adding a New Internal Endpoint

Same pattern, but:
1. File goes in `backend/api/internal/{resource}/`
2. Mount under `internal_app` in `main.py`
3. **NEVER** call from frontend
4. Document why it's internal-only (performance, security, etc.)

### Do's and Don'ts

✅ **DO**:
- Use Pydantic for request/response validation
- Add Auth0 JWT dependency for protected endpoints
- Log events without PHI: `logger.info("action", session_id=id)`
- Return proper HTTP status codes (201 for creation, 204 for deletion)
- Use `async def` for I/O-bound endpoints
- Add OpenAPI tags for documentation
- Write docstrings with examples

❌ **DON'T**:
- Call `/internal/*` from frontend
- Log PHI/PII (emails, names, medical data)
- Hardcode secrets (use environment variables)
- Use blocking I/O in async endpoints
- Skip input validation
- Return raw exceptions (use HTTPException)
- Modify HDF5 data (append-only!)

### Testing Checklist

Before shipping a new endpoint:
- [ ] Pydantic models defined
- [ ] Auth dependency added (if protected)
- [ ] No PHI in logs
- [ ] OpenAPI tags added
- [ ] Unit tests written
- [ ] Integration tests pass
- [ ] Documented in this file
- [ ] No `print()` statements (use logger)
- [ ] Proper error handling (try/except → HTTPException)
- [ ] CORS tested (if public)

---

## Middleware Stack

Middleware is applied in order (outermost to innermost):

```python
# PUBLIC APP
1. TracingMiddleware        # Distributed tracing (P2)
2. CORSMiddleware            # Cross-origin requests
3. IdempotencyMiddleware     # Prevent duplicate POSTs

# INTERNAL APP
1. TracingMiddleware         # Distributed tracing (P2)
2. InternalOnlyMiddleware    # Localhost-only in production 🔒
```

**Order matters**: Tracing must be outermost to capture all requests.

---

## API Documentation

### Auto-Generated Docs

- **Swagger UI**: `http://localhost:7001/docs`
- **ReDoc**: `http://localhost:7001/redoc`
- **OpenAPI JSON**: `http://localhost:7001/openapi.json`

### Health Check

```bash
curl http://localhost:7001/health
# {"status":"ok"}
```

### Root Discovery

```bash
curl http://localhost:7001/
# {
#   "service": {...},
#   "api": {
#     "public": {...},
#     "internal": {...}
#   },
#   "examples": {...}
# }
```

---

## Recent Changes

### 2025-12-08 - Backend Documentation
- **Created**: Comprehensive backend architecture documentation
- **Verified**: No frontend violations of three-layer rule
- **Documented**: Router organization, security patterns, developer guidelines

### 2025-11-15 - SOLIS Modular Architecture
- **Refactored**: Monolithic workflows router into modular sub-routers
- **Created**: `backend/api/public/workflows/` directory structure
- **Reduced**: File sizes from 2175 lines to ~200-500 lines each

### 2025-11-14 - Pruned Unused Endpoints
- **Removed**: FI-STRIDE deprecated routes
- **Cleaned**: AURITY-only codebase
- **Updated**: Documentation to reflect current state

---

## Support

Questions about backend architecture? Ask in #backend channel or tag @backend-team.

Found a bug? File an issue with tag `backend`.

Need to add a new workflow? See [Developer Guidelines](#developer-guidelines) above.
