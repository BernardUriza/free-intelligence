# Free Intelligence · Kernel Context (v0.6)

**AURITY** = Advanced Universal Reliable Intelligence for Telemedicine Yield

Owner: Bernard Uriza Orozco
Version: 0.1.0 (Production Deployed)
Updated: 2025-11-17
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

## 📝 Recent Changes

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

Stack: **FastAPI** · **h5py** · **structlog** · **Next.js 16** · **Tailwind** · **Deepgram** · **Azure Whisper**
