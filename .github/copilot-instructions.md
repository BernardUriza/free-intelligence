# Copilot Agent Guide (AURITY)

Version 0.3.0 • Python 3.14 • FastAPI + Next.js

## Architecture
- Public → Internal → Worker layers. Public routes live under `/api/workflows/aurity/*`; internal under `/api/internal/*`; workers use thread pools for async tasks. Frontend must never call internal routes.
- Event-sourced storage in HDF5 at `storage/sessions/{session_id}.h5`: append-only, atomic write via `.h5.part` → fsync → rename, per-session SHA256 integrity.
- Auth0 JWT with RBAC; admin ops require `FI-superadmin`. Roles claim: `https://aurity.app/roles`.

## Coding Conventions
- Backend: Python 3.14 only. Begin modules with `from __future__ import annotations`. Use Pydantic DTOs, FastAPI DI, async I/O. Structured logging via `structlog` with IDs only (no PHI/PII).
- Frontend: Next.js + TypeScript with absolute imports (`@/…`). Public API base from `NEXT_PUBLIC_BACKEND_URL` and only `/api/workflows/aurity/*` endpoints. Use `AbortController` for cleanup and proper error handling.
- Secrets via env only. No hardcoded tokens/keys. CORS whitelist in `backend/app/main.py`.

## Key Patterns
- Public Endpoint (backend): add under `backend/api/public/workflows/`, depend on `get_current_user`, log `session_id/workflow_id`, return Pydantic model, register in `backend/app/main.py`.
- HDF5 append: write to temp `.part`, flush + fsync, atomic rename; never delete/overwrite historical datasets.
- Observability: Prometheus counters/histograms; p95 targets: Public API ≤ 800ms, RealtimeTalk ≤ 5s, SOAP ≤ 1500ms. Use correlation IDs and `measure_latency()` for perf logs.

## Commands (dev/test/build)
- Start all: `make dev-all` (backend :7001, frontend :9000)
- Backend tests: `pytest backend/tests/`
- Type check (Python): `pyright backend/`
- Frontend build: `cd apps/aurity && pnpm build`
- Deploy (CI/CD only): `make ci-deploy`

## File Map (start here)
- Backend entry: [backend/app/main.py](backend/app/main.py)
- Public routes: [backend/api/public/workflows](backend/api/public/workflows)
- Internal routes: [backend/api/internal](backend/api/internal)
- Auth: [backend/auth/jwt.py](backend/auth/jwt.py)
- Storage: [backend/storage](backend/storage)
- Observability: [backend/observability](backend/observability)
- Frontend app: [apps/aurity/app](apps/aurity/app)
- Full context: [apps/aurity/claude.md](apps/aurity/claude.md)

## API Examples
- Frontend fetch (public):
  - `fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001'}/api/workflows/aurity/sessions`,
    { method: 'POST', headers: { 'Content-Type': 'application/json' } }
  )`
- Appointments page uses public clinic APIs: see [apps/aurity/app/admin/appointments/page.tsx](apps/aurity/app/admin/appointments/page.tsx) and handlers `fetchClinics`, `fetchDoctors`, `fetchAppointments`.

## Security & HIPAA
- Never log PHI/PII (names, emails, phone, CURP, medical data, transcripts). Log only IDs and metrics.
- Strict production policy: no SSH edits; read-only ops only. All changes via PR + CI/CD.

## Streaming & Reasoning (LLM)
- SSE contract: emit meta (thinking) first if present, then content chunks, then clean stop + `[DONE]`. Do not log raw reasoning; attach to UI only.
- Honor requested `model` end-to-end; fall back gracefully if unavailable.

## Success Checklist
- Public-only endpoints from frontend; internal guarded.
- Append-only HDF5 writes with atomic rename.
- Python 3.14 compliance and async FastAPI.
- Structured logs with correlation IDs; Prometheus metrics.
- Env-based config; no secrets in code.

Questions or gaps? Ping for clarifications on routes, storage invariants, or CI steps to refine this guide.
