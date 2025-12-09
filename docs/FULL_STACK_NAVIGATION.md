# AURITY Full-Stack Navigation Reference

**Last Updated**: 2025-12-08
**Status**: Production

---

## Quick Reference

This document provides a unified view of frontend routes and their corresponding backend API endpoints.

## Frontend → Backend Mapping

| Frontend Route | Backend API Endpoints | Auth Required | Notes |
|---------------|----------------------|---------------|-------|
| `/` | N/A | No | SlimIndexHub (or redirect to /chat) |
| `/chat` | `/api/workflows/aurity/assistant/*` | Optional | Works anonymous or authenticated |
| `/medical-ai` | `/api/workflows/aurity/sessions/*`<br>`/api/workflows/aurity/soap/*`<br>`/api/patients` | Yes (MEDICO/ADMIN) | Full medical workflow |
| `/dashboard` | `/api/workflows/aurity/kpis`<br>`/api/workflows/aurity/waiting-room/*`<br>`/api/clinics` | No | TV mode available |
| `/timeline` | `/api/workflows/aurity/timeline/memory`<br>`/api/workflows/aurity/sessions` | Yes | Longitudinal memory |
| `/policy` | `/api/policy` | No | Read-only policy viewer |
| `/audit` | `/api/audit/logs`<br>`/api/audit/stats` | Yes | Audit log viewer |
| `/admin/personas` | `/api/admin/personas` | Yes (ADMIN) | AI persona management |
| `/admin/clinics` | `/api/clinics` | Yes (ADMIN) | Clinic/doctor CRUD |
| `/admin/appointments` | `/api/appointments` | Yes (ADMIN) | Bryntum scheduler |
| `/onboarding` | `/api/workflows/aurity/assistant/*` | No | Demo flow |
| `/checkin` | `/api/checkin` | No | Patient kiosk (QR access) |
| `/checkin/chat` | `/api/checkin/chat` | No | Conversational check-in |
| `/profile` | `/api/auth/profile` | Yes | User profile |
| `/config` | `/api/admin/users` | Yes (SUPERADMIN) | System config |

---

## Critical Rules

### Frontend
1. **ONLY** call `/api/*` endpoints (never `/internal/*`)
2. All pages use `PageHeader` from centralized config
3. All routes accessible via global menu or back button
4. Keyboard shortcuts for power users (1-9, C, O, R)

### Backend
1. PUBLIC layer (`/api/*`) for orchestration
2. INTERNAL layer (`/internal/*`) for atomic operations
3. WORKER layer for background tasks
4. Never expose INTERNAL to external clients

---

## Common Workflows

### 1. Create Medical Session
**Frontend**: `/medical-ai`
```typescript
// 1. Select patient
GET /api/patients

// 2. Create session
POST /api/workflows/aurity/sessions
{
  "patient_id": "P123",
  "provider_id": "D456"
}

// 3. Upload audio chunks
POST /api/workflows/aurity/stream
FormData: { session_id, chunk_number, audio_file }

// 4. Check transcription status
GET /api/workflows/aurity/jobs/{session_id}

// 5. Get SOAP note
GET /api/workflows/aurity/sessions/{session_id}/soap

// 6. Finalize session
POST /api/workflows/aurity/sessions/{session_id}/finalize
```

### 2. AI Chat (Anonymous)
**Frontend**: `/chat`
```typescript
// Stream chat completion
POST /api/workflows/aurity/assistant/chat/stream
{
  "message": "¿Cuáles son los síntomas de diabetes?",
  "persona": "general_assistant",
  "response_mode": "explanatory"
}
```

### 3. View Timeline
**Frontend**: `/timeline`
```typescript
// Get paginated events
GET /api/workflows/aurity/timeline/memory?event_type=all&limit=50&offset=0

// Filter by date range
GET /api/workflows/aurity/timeline/memory?start_date=2025-01-01&end_date=2025-12-08
```

### 4. Admin: Manage Clinics
**Frontend**: `/admin/clinics`
```typescript
// List clinics
GET /api/clinics

// Create clinic
POST /api/clinics
{
  "name": "Clínica Centro",
  "address": "Av. Principal 123"
}

// Get doctors for clinic
GET /api/clinics/{clinic_id}/doctors

// Generate QR code
GET /api/checkin/qr/{clinic_id}
```

---

## Navigation Shortcuts

### Keyboard Shortcuts (Frontend)
- `C` → `/chat` (Free Intelligence Chat)
- `1` → `/medical-ai` (Medical AI Workflow)
- `2` → `/dashboard` (Panel de Control)
- `3` → `/timeline` (Memoria Longitudinal)
- `4` → `/policy` (Policy)
- `5` → `/audit` (Audit Log)
- `8` → `/admin/personas` (AI Personas)
- `9` → `/admin/clinics` (Clínicas)
- `0` → `/admin/appointments` (Agenda de Citas)
- `O` → `/onboarding` (Onboarding Demo)
- `R` → `/checkin/chat` (FI Receptionist)

### API Quick Test (Backend)
```bash
# Health check
curl http://localhost:7001/health

# API discovery
curl http://localhost:7001/

# Test AI assistant
curl -X POST http://localhost:7001/api/workflows/aurity/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hola","persona":"general_assistant"}'

# List sessions
curl http://localhost:7001/api/workflows/aurity/sessions

# Get system health
curl http://localhost:7001/api/system/health
```

---

## Environment Variables

### Frontend (`apps/aurity/.env.production`)
```bash
NEXT_PUBLIC_API_BASE=https://api.aurity.io  # Backend URL
NEXT_PUBLIC_AUTH0_DOMAIN=aurity.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=xxx
NEXT_PUBLIC_AUTH0_AUDIENCE=https://api.aurity.io
```

### Backend (`backend/.env`)
```bash
# Required
CLAUDE_API_KEY=sk-ant-xxx           # Anthropic Claude
DEEPGRAM_API_KEY=xxx                # Deepgram transcription
DATABASE_URL=postgresql://xxx        # PostgreSQL
AUTH0_DOMAIN=aurity.auth0.com
AUTH0_API_AUDIENCE=https://api.aurity.io

# Optional
ALLOWED_ORIGINS=https://app.aurity.io  # CORS whitelist (production)
ENVIRONMENT=production                  # development|staging|production
```

---

## File Locations

### Frontend Navigation
- **Page Header Configs**: `apps/aurity/config/page-headers.ts`
- **Route Definitions**: `apps/aurity/lib/navigation.ts`
- **PageHeader Component**: `apps/aurity/components/layout/PageHeader.tsx`
- **AppNavigation Menu**: `apps/aurity/components/layout/AppNavigation.tsx`
- **Documentation**: `apps/aurity/docs/NAVIGATION.md`

### Backend API
- **Main App**: `backend/app/main.py`
- **Public Routers**: `backend/api/public/`
- **Internal Routers**: `backend/api/internal/`
- **Auth Middleware**: `backend/auth/jwt.py`
- **Documentation**: `backend/docs/API_ARCHITECTURE.md`

---

## Development Workflow

### Starting the Stack

```bash
# Backend (port 7001)
cd /Users/bernardurizaorozco/Documents/free-intelligence
make dev-backend

# Frontend (port 9000)
cd apps/aurity
pnpm dev
```

### Testing Changes

```bash
# Frontend type check
cd apps/aurity
pnpm typecheck

# Backend tests
cd /Users/bernardurizaorozco/Documents/free-intelligence
pytest backend/tests/

# E2E tests
cd apps/aurity
pnpm playwright test
```

### Deployment

```bash
# Frontend (DigitalOcean)
cd apps/aurity
pnpm build
# Deploy via CI/CD

# Backend (DigitalOcean)
make ci-deploy  # From root
```

---

## Troubleshooting

### Frontend Can't Reach Backend
1. Check `NEXT_PUBLIC_API_BASE` in `.env.production`
2. Verify CORS settings in `backend/app/main.py`
3. Check `ALLOWED_ORIGINS` environment variable

### Auth0 Token Issues
1. Verify `AUTH0_DOMAIN` and `AUTH0_API_AUDIENCE` match
2. Check JWT token in browser DevTools → Application → Cookies
3. Verify role claim: `https://aurity.app/roles`

### 403 Forbidden on Internal Endpoints
**This is expected!** Internal endpoints are blocked by `InternalOnlyMiddleware` in production.
- Solution: Use public orchestrator endpoints instead

### Route Not Found (404)
1. **Frontend**: Check route exists in `apps/aurity/app/*/page.tsx`
2. **Backend**: Verify router registered in `backend/app/main.py`
3. Check for typos in URL paths

---

## Support

- **Frontend Issues**: #frontend channel or @frontend-team
- **Backend Issues**: #backend channel or @backend-team
- **Full-Stack Issues**: #engineering or @engineering-lead

---

**Remember**: Consistency is key. Follow the patterns, use the tools, and document your changes.
