# Copilot Agent Guide (AURITY)

Version 0.4.0 • Python 3.14 • FastAPI + Next.js

## Architecture
- **Monorepo Structure**: Backend (Python/FastAPI) in `backend/`, Frontend (Next.js/TypeScript) in `apps/aurity/`, Shared packages in `packages/`
- **Three-Layer Architecture**: Public → Internal → Worker layers
  - Public routes: `/api/workflows/aurity/*` (CORS enabled, orchestration)
  - Internal routes: `/api/internal/*` (localhost-only in production, atomic resources)
  - Workers: ThreadPoolExecutor for CPU-intensive tasks (transcription: 4 workers, diarization: 2 workers)
- **Event-sourced Storage**: HDF5 in `storage/sessions/{session_id}.h5` (append-only, atomic write via `.h5.part` → fsync → rename, per-session SHA256 integrity)
- **Authentication**: Self-hosted JWT with RBAC (2 roles: `FI-superadmin`, `FI-clinician`); admin ops require `FI-superadmin`
- **Observability**: Prometheus counters/histograms; p95 targets: Public API ≤ 800ms, RealtimeTalk ≤ 5s, SOAP ≤ 1500ms

## Coding Conventions
- **Backend (Python 3.14 only)**:
  - `from __future__ import annotations` in every file
  - Modern type hints: `str | None` instead of `Optional[str]`
  - Pydantic DTOs, FastAPI DI, async I/O everywhere
  - Structured logging via `structlog` with correlation IDs (NO PHI/PII)
  - Match/case for state machines
- **Frontend (Next.js + TypeScript)**:
  - Absolute imports: `@/…` (configured in `tsconfig.json`)
  - Public API only: never call `/api/internal/*`
  - `AbortController` for request cleanup
  - Environment: `NEXT_PUBLIC_BACKEND_URL` for API base
- **Security**: Environment variables only for secrets; no hardcoded keys

## Key Patterns
- **Public Endpoint**: Add under `backend/api/public/workflows/`, depend on `get_current_user`, log `session_id/workflow_id`, return Pydantic model, register in `backend/app/main.py`
- **HDF5 Append-Only**: Write to temp `.part`, flush + fsync, atomic rename; never delete/overwrite historical datasets. Schema: `/sessions/{session_id}/tasks/{TASK_TYPE}/versions/{timestamp}`
- **Three-Layer Separation**:
  - Public: Orchestration (`/api/workflows/aurity/*`)
  - Internal: Atomic operations (`/api/internal/*`)
  - Workers: CPU tasks in ThreadPoolExecutor
- **Error Handling**: Structured exceptions, HTTPException with status codes, no PHI/PII in logs
- **Testing**: Pytest with fixtures, async tests marked `@pytest.mark.asyncio`

## Commands (dev/test/build)
- **Start all**: `PYTHONPATH=backend/src python -m fi_cli dev all` (backend :7001, frontend :9000 via turbo)
- **Backend tests**: `python3.14 -m pytest backend/tests/ -v --tb=short`
- **Type check (Python)**: `pyright backend/` (configured via `pyrightconfig.json`)
- **Frontend build**: `cd apps/aurity && pnpm build` or `pnpm build` (turbo monorepo)
- **Frontend dev**: `cd apps/aurity && pnpm dev` or `pnpm dev`
- **Code Quality**: `PYTHONPATH=backend/src python -m fi_cli coder lint-fix` (AI-powered linting)
- **Deploy (CI/CD only)**: `PYTHONPATH=backend/src python -m fi_cli deploy setup-backend-service` (production deployments)

**Note**: `fi_cli` is the unified interface for all system operations. Use `make` commands only for very specific development tasks not covered by fi_cli.

## File Map (start here)
- **Backend entry**: [backend/app/main.py](backend/app/main.py)
- **Public routes**: [backend/api/public/workflows](backend/api/public/workflows)
- **Internal routes**: [backend/api/internal](backend/api/internal)
- **Auth**: [backend/auth/jwt.py](backend/auth/jwt.py)
- **Storage**: [backend/storage](backend/storage)
- **Workers**: [backend/workers](backend/workers)
- **Observability**: [backend/observability](backend/observability)
- **Frontend app**: [apps/aurity/app](apps/aurity/app)
- **Shared packages**: [packages](packages)
- **Full context**: [apps/aurity/claude.md](apps/aurity/claude.md)

## API Examples
- **Frontend fetch (public)**:
  - `fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001'}/api/workflows/aurity/sessions`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' } }
  )`
- **Appointments page**: Uses public clinic APIs - see [apps/aurity/app/admin/appointments/page.tsx](apps/aurity/app/admin/appointments/page.tsx) and handlers `fetchClinics`, `fetchDoctors`, `fetchAppointments`.

## Security & HIPAA
- **NO PHI/PII in logs**: Never log `nombre`, `email`, `curp`, `telefono`, medical data, transcripts. Log only IDs and metrics.
- **Production policy**: No SSH edits; read-only ops only. All changes via PR + CI/CD.
- **RBAC**: Role claims in `https://aurity.app/roles`; `FI-superadmin` for admin ops.

## Streaming & Reasoning (LLM)
- **SSE Contract**: Emit `meta` (thinking) first if present, then content chunks, then clean stop + `[DONE]`. Do not log raw reasoning; attach to UI only.
- **Model Honor**: Honor requested `model` end-to-end; fall back gracefully if unavailable.

## Success Checklist
- Public-only endpoints from frontend; internal guarded.
- Append-only HDF5 writes with atomic rename.
- Python 3.14 compliance and async FastAPI.
- Structured logs with correlation IDs; Prometheus metrics.
- Env-based config; no secrets in code.
- `from __future__ import annotations` in every Python file.
- Absolute imports `@/…` in TypeScript.
- No PHI/PII exposure in logs or code.

Questions or gaps? Ping for clarifications on routes, storage invariants, or CI steps to refine this guide.
