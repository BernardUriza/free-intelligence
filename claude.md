# Free Intelligence · Kernel Context (v0.7)

**AURITY** = Advanced Universal Reliable Intelligence for Telemedicine Yield

Owner: Bernard Uriza Orozco
Version: 0.1.0 (Production Deployed)
Updated: 2025-11-20
TZ: America/Mexico_City

---

## 🌐 Production Deployment

**Live URL**: https://fi-aurity.duckdns.org/
**Backend API**: https://fi-aurity.duckdns.org/api/
**SSL**: Let's Encrypt (auto-renews)
**DNS**: DuckDNS (fi-aurity.duckdns.org → 104.131.175.65)

### Architecture
```
Browser (HTTPS:443) → Nginx (SSL termination) → {
  ├─ Static Frontend (Next.js)
  └─ /api/* → Backend (FastAPI:7001)
}
```

### CORS Configuration
Backend allows: `http://localhost:9000`, `http://localhost:9050`, `https://fi-aurity.duckdns.org`
Location: `backend/app/main.py` (line 125)

---

## 🏗️ Architecture Layering (CRITICAL)

### ⚠️ REGLA ABSOLUTA
🚫 `/internal/*` is **COMPLETELY PROHIBITED** for external access
- Frontend/curl NEVER call `/internal/*` directly
- InternalOnlyMiddleware returns 403 Forbidden
- If you see `/internal/*` in a URL = **ERROR**

### Valid Layers

**1️⃣ PUBLIC** (`/api/workflows/*`) = ONLY VALID ENTRY POINT
```
✅ POST   /api/workflows/aurity/stream                    # Upload chunk
✅ GET    /api/workflows/aurity/sessions/{id}/monitor    # Real-time progress
✅ POST   /api/workflows/aurity/sessions/{id}/checkpoint # Concatenate audio
✅ POST   /api/workflows/aurity/sessions/{id}/diarization # Start diarization
✅ POST   /api/workflows/aurity/sessions/{id}/soap       # Generate SOAP notes
✅ POST   /api/workflows/aurity/sessions/{id}/finalize   # Encrypt & finalize
```

**2️⃣ INTERNAL** (`/api/internal/*`) = FORBIDDEN DIRECT ACCESS
- Only called internally by PUBLIC routers
- Middleware blocks all external requests
- Contains atomic resource operations

**3️⃣ WORKERS** (ThreadPoolExecutor)
- 4 workers for transcription
- 2 workers for diarization
- No Docker, no Redis, no Celery (removed 2025-11-15)

---

## 🚀 Quick Start

### Development
```bash
make dev-all    # Backend (7001) + Frontend (9000) in one command
make test       # Run pytest suite
make type-check # Pyright type checking
```

### Production Deployment
```bash
# Frontend (rebuild + deploy)
cd apps/aurity && pnpm build
python3 scripts/deploy-scp.py

# Backend (update + restart)
python3 scripts/deploy-backend-cors-fix.py

# Complete HTTPS deployment
python3 scripts/setup-https-letsencrypt.py
```

---

## 📂 Core Structure

```
free-intelligence/
├─ backend/                          # FastAPI (Python 3.11+)
│  ├─ app/main.py                    # Entry point + CORS config
│  ├─ api/public/workflows/          # PUBLIC endpoints
│  ├─ api/internal/                  # INTERNAL endpoints (blocked)
│  ├─ workers/sync_workers.py        # ThreadPoolExecutor workers
│  └─ storage/task_repository.py     # HDF5 operations
│
├─ apps/aurity/                      # Next.js 16 (Static Export)
│  ├─ .env.production                # NEXT_PUBLIC_BACKEND_URL
│  ├─ next.config.static.js          # output: 'export'
│  └─ out/                           # Built static files
│
├─ storage/
│  └─ corpus.h5                      # HDF5 (append-only)
│     └─ /sessions/{id}/tasks/{TASK_TYPE}/
│        ├─ chunks/                  # Data chunks
│        └─ metadata                 # Job metadata
│
└─ scripts/
   ├─ deploy-scp.py                  # Deploy frontend via SCP
   ├─ deploy-backend-cors-fix.py     # Deploy backend
   ├─ setup-https-letsencrypt.py     # Setup SSL certificate
   └─ deploy-https-complete.py       # Full deployment
```

### HDF5 Task Types
- **TRANSCRIPTION**: Whisper/Deepgram ASR (load-balanced)
- **DIARIZATION**: Speaker classification (Azure GPT-4)
- **SOAP_GENERATION**: Clinical notes extraction
- **EMOTION_ANALYSIS**: Patient emotion detection
- **ENCRYPTION**: AES-GCM-256 encryption

### Frontend Components (Key)

**Chat Widget** (`components/chat/`)
- **Architecture**: Modular design with 8+ sub-components
- **Modes**: `normal`, `expanded`, `minimized`, `fullscreen`
- **Features**:
  - Infinite scroll (load older messages)
  - Auto-scroll to bottom (100ms delay for DOM render)
  - Response modes: `explanatory` vs `concise`
  - Persistent storage per Auth0 user (`fi_chat_widget_{user.sub}`)
- **Config**: `config/chat.config.ts`, `config/chat-messages.config.ts`
- **UX Pattern**: Expand button hides when expanded, Minimize2 restores to normal

**User Management** (`components/admin/UserManagement.tsx`)
- **Route**: `/admin/users` (requires `FI-superadmin` role)
- **Features**: List users, assign roles, block/unblock, create users
- **Backend**: `/internal/admin/users` (JWT + role verification)

**GlobalPolicyBanner** (`components/policy/GlobalPolicyBanner.tsx`)
- **Display**: "100% Local • HIPAA Ready • Append-Only" principles
- **Behavior**: Auto-dismiss after 5s with fade-out transition
- **Reset**: Reappears on each page navigation (local state)

---

## 🔧 Configuration

### Environment Variables
```bash
# Backend
ALLOWED_ORIGINS="http://localhost:9000,...,https://fi-aurity.duckdns.org"
DEEPGRAM_API_KEY="..."  # STT service

# Frontend (.env.production)
NEXT_PUBLIC_BACKEND_URL=https://fi-aurity.duckdns.org
NEXT_PUBLIC_API_BASE=https://fi-aurity.duckdns.org
```

### Nginx Config (`/etc/nginx/sites-enabled/aurity`)
```nginx
server {
    listen 443 ssl;
    server_name fi-aurity.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/fi-aurity.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fi-aurity.duckdns.org/privkey.pem;

    root /opt/free-intelligence/apps/aurity/out;

    location /api/ {
        proxy_pass http://localhost:7001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 🔒 Security & Performance

### STT Load Balancing (2025-11-15)
Round-robin between Azure Whisper (3 RPM) and Deepgram (unlimited)
- **Performance**: 52s/chunk → 2.1s/chunk (25x faster)
- **Cost**: Deepgram $0.0043/min, 50k free minutes/month

### HTTPS Requirements
- Microphone access requires HTTPS (browser security policy)
- getUserMedia API blocked over HTTP (except localhost)
- WebSpeech API requires secure context

### Data Sovereignty
- HDF5 append-only (no mutations)
- All PHI encrypted with AES-GCM-256
- LAN-only backend (no cloud dependencies)

---

## 🔐 Auth0 RBAC (Role-Based Access Control)

### Configuration
- **Domain**: dev-1r4daup7ofj7q6gn.us.auth0.com
- **Audience**: https://api.fi-aurity.duckdns.org
- **Custom Claim**: `https://aurity.app/roles` (JWT token)
- **Action**: "Add Roles to Token" (Post-Login flow)

### Roles
- **FI-superadmin**: Full system access for user management and configuration
- **FI-admin**: Administrative access (future)

### User Management
**Location**: `/admin/users` (requires `FI-superadmin` role)
- List all Auth0 users
- Assign/remove roles
- Block/unblock users
- Create new users

**Backend Endpoint**: `/internal/admin/users`
- **Protection**: JWT verification + role check
- **Implementation**: `backend/api/internal/admin/users.py`
- **JWT Verifier**: `backend/auth/jwt_verifier.py`

### Scripts
```bash
# Assign superadmin role to user
python3 scripts/assign_superadmin_role.py <email>

# Link two Auth0 accounts (same email)
python3 scripts/link_auth0_accounts.py
```

### Important Notes
- **Token refresh required**: After role assignment, user must logout and login again
- **Account linking**: Consolidates multiple login methods (Google OAuth + Email/Password) into single account
- **Development mode**: InternalOnlyMiddleware allows all requests in dev environment

---

## 📝 Recent Changes

**2025-11-20**: Frontend UX improvements + Auth0 RBAC + Chat voice recording
- Auth0 RBAC fully configured (FI-superadmin role)
- User Management page functional at `/admin/users`
- **Chat Widget voice recording**: Created useChatVoiceRecorder hook + VoiceMicButton component with VAD
  - Fixed missing voice props in `/chat/page.tsx` (ChatToolbar:172-180)
  - Root cause: Wrapper component wasn't passing `voiceRecording`, `onVoiceStart`, `onVoiceStop` props
  - Floating widget worked (ChatWidget.tsx had props), standalone `/chat/` page didn't
  - **False alarm**: Initially thought it was Turbopack HMR bug, but was just missing props
- Corrected module import paths (absolute `@/` paths for cross-directory imports)
- Chat Widget: expand button hides when expanded, Minimize2 restores to normal
- GlobalPolicyBanner: auto-dismiss after 5s with smooth fade-out
- Chat Widget: auto-scroll to bottom with smooth animation (100ms delay for DOM render)
- Scripts: `assign_superadmin_role.py`, `link_auth0_accounts.py`

**2025-11-17**: Production HTTPS deployment complete
- DuckDNS domain: fi-aurity.duckdns.org
- Let's Encrypt SSL certificate (auto-renewal)
- Nginx reverse proxy for API
- CORS configured for production origin

**2025-11-15**: Docker/Redis/Celery removed
- ThreadPoolExecutor replaces Celery queue
- No Docker overhead, simpler dev environment
- HDF5-backed status tracking (no Redis)
- `make dev-all` runs everything locally

**2025-11-15**: STT Load Balancer
- Intelligent round-robin (Azure Whisper ↔ Deepgram)
- 25x faster transcription
- Auto-detection of available providers

**2025-11-14**: HDF5 Task-Based Architecture
- Migrated from jobs/ to tasks/{TASK_TYPE}/
- 58 sessions migrated successfully
- Cleaner schema, better scalability

---

## 🔧 Troubleshooting

### Turbopack Cache Issues
**Symptom**: "Module not found" errors despite files existing on disk, or stale imports showing in errors

**Solution**: Nuclear cache clear
```bash
# Kill Next.js server
pkill -f "next dev"

# Clear ALL caches
cd apps/aurity
rm -rf .next .turbo node_modules/.cache .swc
find . -name '*.tsbuildinfo' -delete

# Restart
pnpm dev
```

**Root cause**: Turbopack's aggressive caching can persist stale module resolutions across file edits. The bundler reads from cache instead of actual files.

### Module Import Errors
**Pattern**: `Can't resolve './Component'` when file exists

**Solution**: Use absolute imports for cross-directory dependencies
```typescript
// ❌ BAD: Relative import across directories
import { UserDisplay } from './UserDisplay'  // From components/layout/

// ✅ GOOD: Absolute import
import { UserDisplay } from '@/components/auth/UserDisplay'
```

**Rule of thumb**:
- Same directory: relative `./Component`
- Different directory: absolute `@/path/to/Component`

### Auth0 403 Forbidden (User Management)
**Symptom**: HTTP 403 when accessing `/admin/users`

**Diagnosis**:
1. Check JWT token has roles: `jwt.io` → paste token → verify `https://aurity.app/roles` contains `FI-superadmin`
2. Check backend logs: `event='SUPERADMIN_ACCESS_DENIED'` means role missing

**Solution**:
```bash
# Assign role
python3 scripts/assign_superadmin_role.py <email>

# User must logout and login again for new token
```

### Chat Widget Not Scrolling
**Symptom**: Messages appear but don't auto-scroll to bottom

**Solution**: Auto-scroll must use component's internal `ref`, not `getElementById` from parent
- ✅ Implemented in `ChatWidgetMessages.tsx` using `scrollContainerRef`
- ❌ Don't use `document.getElementById()` from `ChatWidget.tsx`

### Port Already in Use
```bash
# Find process using port 9000
lsof -ti:9000

# Kill it
kill -9 $(lsof -ti:9000)

# Or use pkill
pkill -f "next dev"
```

---

## 🧰 Essential Commands

```bash
# Development
make dev-all                # Start everything (recommended)
make run                    # Backend only
pnpm dev                    # Frontend only (from apps/aurity)

# Testing
make test                   # Backend tests
pnpm test                   # Frontend tests
make type-check             # Quick type check (2s)
make type-check-all         # Complete check (15s)

# Production
pnpm build                  # Build static frontend
python3 scripts/deploy-https-complete.py  # Full deployment

# Trello CLI v2.2.0
trello quick-start <card_id>   # Move to In Progress
trello quick-test <card_id>    # Move to Testing
trello quick-done <card_id>    # Move to Done
```

---

## 🪦 Deprecated (Archived)

**Docker/Celery/Redis** (removed 2025-11-15)
- Location: `docs/archive/deprecated-docker-redis/`
- Replaced by: ThreadPoolExecutor + HDF5 status tracking
- Files: `backend/workers/transcription_tasks.py`, `diarization_tasks.py` (marked deprecated)

**Old HDF5 Schema** (migrated 2025-11-14)
- `/jobs/`, `/production/` → `/sessions/{id}/tasks/{TASK_TYPE}/`
- Backward compatibility maintained via wrapper layer

---

## 🎯 Communication Guidelines

- **NO_MD=1**: No markdown files > 150 lines (except README.md, CLAUDE.md)
- Respond in chat: technical bullets (10-15 lines), no fluff
- Create files only for permanent documentation → executable artifacts
- Style: precise, cite paths/commits when applicable

---

## 🏷️ Conventions

- **Session IDs**: `session_YYYYMMDD_HHMMSS`
- **Commits**: Conventional Commits + Task ID
- **Trello**: `FI-[AREA]-[TYPE]-[NUM]: Title` (priority via labels)

---

## 💡 Development Best Practices

### Import Patterns
```typescript
// ✅ CORRECT: Absolute imports for cross-directory
import { UserDisplay } from '@/components/auth/UserDisplay'
import { ChatConfig } from '@/config/chat.config'

// ✅ CORRECT: Relative imports within same directory
import { ChatEmptyState } from './ChatEmptyState'
import { ChatMessageList } from './ChatMessageList'

// ❌ WRONG: Relative import across directories
import { UserDisplay } from '../auth/UserDisplay'  // Fragile, breaks on refactor
```

### Component Patterns
- **Refs over getElementById**: Use React refs for DOM access within components
- **State colocation**: Keep state close to where it's used (avoid prop drilling)
- **Config files**: Centralize configuration in `/config` directory
- **Modular components**: Break down large components into focused sub-components

### Cache Management
- **After large refactors**: Nuclear cache clear (`.next`, `.turbo`, `.swc`)
- **After dependency updates**: `pnpm install` + cache clear
- **Persistent errors**: Check browser console for client-side errors vs server logs

### Auth0 Patterns
- **Token refresh**: Always logout/login after role changes
- **Custom claims**: Use namespaced claims (`https://aurity.app/roles`)
- **Actions**: Deploy Actions via dashboard, verify in Auth0 logs

---

Stack: **FastAPI** · **h5py** · **structlog** · **Next.js 16 (Turbopack)** · **Tailwind** · **Auth0** · **Deepgram** · **Azure Whisper**
