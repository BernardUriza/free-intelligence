# Free Intelligence

**AURITY** = **A**dvanced **U**niversal **R**eliable **I**ntelligence for **T**elemedicine **Y**ield

**Version**: 1.0.0 (Production)
**Live**: https://app.aurity.io
**Owner**: Bernard Uriza Orozco
**Architecture**: GPU-First, No Compromises

---

## 🎯 What is Free Intelligence?

**GPU-accelerated AI system for healthcare** - like Cyberpunk 2077, no GPU = no play.

Sistema de **inteligencia médica con RAG GPU**, diseñado para performance óptima sin degradación:
- 📊 **RAG embeddings**: GPU-only (20-50ms), no CPU fallback (100-150ms unacceptable)
- 🧠 **LLM inference**: Local Ollama on GPU (Qwen3:1.7b)
- 🔒 **HIPAA on-prem**: Datos locales, HDF5 append-only, zero cloud PHI
- 🚀 **Production-grade**: Live at app.aurity.io, 99%+ uptime

**Key Difference:**
- ❌ Generic systems: CPU fallbacks, degraded performance
- ❌ Cloud SaaS: PHI in transit, vendor lock-in, latency
- ✅ **AURITY**: GPU-first architecture, on-prem data, optimal UX

> "El usuario prefiere no ver nada que ver gráficos chafos"

---

## 💻 System Requirements

Like modern gaming - **GPU required, no compromises**.

### Minimum Specs (Production)

```
FI Cloud (Production Server)
═══════════════════════════════
• Droplet: DigitalOcean 1GB RAM
• OS: Ubuntu 22.04 LTS
• Python: 3.14
• No GPU needed (backend only)

FI Monitor (GPU Service) ⚡ REQUIRED
═══════════════════════════════════
• GPU: NVIDIA RTX 3050+ / AMD equivalent
• RAM: 8GB minimum
• Storage: 50GB SSD
• Internet: 10 Mbps upload (Cloudflare Tunnel)
• OS: Windows 10/11, macOS 12+, Linux

Why GPU Required?
─────────────────
• RAG embeddings CPU: 100-150ms ❌ (unacceptable UX)
• RAG embeddings GPU: 20-50ms ✅ (production-grade)
• Ollama inference: Requires GPU for acceptable latency
• No fallback: System won't start without GPU service

Like Cyberpunk 2077:
─────────────────────
✅ RTX 3060+ → Full experience
✅ GTX 1660+ → Acceptable (entry-level)
❌ CPU-only → System won't run
```

### Tested Configurations

| Hardware | GPU | Performance | Status |
|----------|-----|-------------|--------|
| Windows PC (i9+RTX4060) | 8GB VRAM | 20-30ms embeddings | ✅ Production |
| Mac M1 Pro | 16GB unified | 40-50ms (MPS) | ✅ Development |
| Mac M1 Air | 8GB unified | 50-80ms (MPS) | ⚠️ Entry-level |
| Cloud GPU (RunPod RTX4090) | 24GB VRAM | 15-25ms | ✅ Alternative |
| CPU-only server | N/A | System offline | ❌ Unsupported |

---

## 🏗️ Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                 FI Cloud (app.aurity.io)                   │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Next.js Frontend (Static Export)                    │ │
│  │  • Auth0 RBAC                                        │ │
│  │  • Chat UI (RAG-powered)                             │ │
│  │  • Admin Dashboard                                   │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  FastAPI Backend (Python 3.14)                       │ │
│  │  • RAG Search (GPU embeddings via Monitor)          │ │
│  │  • Document Storage (HDF5 corpus.h5)                │ │
│  │  • HIPAA-compliant data layer                       │ │
│  │  • User isolation (owner_user_id)                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                          ↕ HTTPS                           │
└────────────────────────────────────────────────────────────┘
                           ↕ Cloudflare Tunnel
┌────────────────────────────────────────────────────────────┐
│             FI Monitor (Local GPU Service)                 │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  HTTP Gateway (Port 11400)                           │ │
│  │  • Routes /rag/* → RAG Service                       │ │
│  │  • Routes /api/* → Ollama                            │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  RAG Service (Port 11435) - GPU Embeddings          │ │
│  │  • sentence-transformers/all-MiniLM-L6-v2           │ │
│  │  • CUDA/MPS acceleration                            │ │
│  │  • 20-50ms latency                                   │ │
│  └──────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Ollama (Port 11434) - LLM Inference                │ │
│  │  • Qwen3:1.7b (1.7B params)                          │ │
│  │  • GPU-accelerated                                   │ │
│  │  • Local, no cloud API calls                        │ │
│  └──────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

**GPU-Only Philosophy:**
```
FI Monitor UP → Chat works (LLM + RAG embeddings) ✅
FI Monitor DOWN → Chat offline (fail fast, clear error) ❌

No CPU fallback, no degraded mode, no "it works but slow"
```

---

## 🚀 Quick Start

### Development (Local)

```bash
# 1. Install dependencies
make install

# 2. Start backend
make dev-all

# 3. Start frontend (separate terminal)
cd apps/aurity
pnpm install
pnpm dev

# Backend: http://localhost:7001
# Frontend: http://localhost:9000
```

### Production Deployment

```bash
# Automated deployment (via GitHub Actions)
git push origin main  # Triggers CI/CD pipeline

# Manual deployment (emergency only)
ssh root@104.131.175.65
cd /opt/free-intelligence
git pull
./scripts/deploy.sh
```

**Live URL**: https://app.aurity.io

---

## 📦 Monorepo Structure

```
free-intelligence/
├── backend/                    # 🐍 Python 3.14 (FastAPI)
│   ├── src/
│   │   ├── fi_assistant/      # RAG + LLM integration
│   │   │   └── services/
│   │   │       └── monitor_client.py  # GPU embedding client
│   │   ├── fi_storage/        # HDF5 document storage
│   │   │   └── infrastructure/
│   │   │       └── hdf5/
│   │   │           └── document_repository.py  # HIPAA-compliant
│   │   ├── fi_auth/           # Auth0 JWT + RBAC
│   │   └── fi_document/       # Document upload/search
│   └── storage/
│       └── corpus.h5          # Single-file storage (all PDFs + embeddings)
│
├── apps/
│   ├── aurity/                # 🌐 Next.js Frontend
│   │   ├── app/              # Next.js 14 app router
│   │   ├── components/       # React components
│   │   └── .env.production   # Production config
│   │
│   └── fi-monitor/            # 🎮 GPU Service (Tauri Desktop App)
│       ├── src-tauri/        # Rust (process management)
│       ├── rag_service/      # Python GPU embeddings
│       └── gateway/          # HTTP router (port 11400)
│
├── .github/workflows/
│   ├── deploy-production.yml  # Auto-deploy to app.aurity.io
│   └── build-desktop.yml     # Build FI Monitor (Win/Mac/Linux)
│
├── docs/                      # 📚 Documentation
└── test_rag_integration.py   # Integration tests
```

---

## 🧪 Testing

### Backend Tests
```bash
# Unit tests
pytest backend/tests/

# Type checking
pyright backend/

# RAG Integration tests (requires FI Monitor running)
PYTHONPATH=backend/src python3 test_rag_integration.py
```

### Frontend Tests
```bash
cd apps/aurity
pnpm test          # Jest tests
pnpm type-check    # TypeScript
pnpm lint          # ESLint
```

### Manual E2E Testing
```bash
# 1. Start FI Monitor (GPU service)
# Open FI Monitor app → Auto-starts Ollama + RAG + Tunnel

# 2. Verify GPU service
curl http://localhost:11435/rag/health
# Expected: {"status":"ok","device":"cuda"}

# 3. Upload document + RAG query
curl -X POST https://app.aurity.io/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"

curl -X POST https://app.aurity.io/api/assistant/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"messages":[{"role":"user","content":"¿Qué dice el documento?"}]}'
```

---

## 🔧 Development Workflow

### Git Workflow (Trunk-Based)

```bash
# All work happens in dev branch
git checkout dev
git add .
git commit -m "feat: description"
git push origin dev

# Create PR to main (triggers CI/CD)
gh pr create --base main --head dev --title "Release: v1.0.1"

# After PR approval → Auto-deploy to production
```

**Protected Branches:**
- `main` - Production (auto-deploy to app.aurity.io)
- `dev` - Development (CI checks only)

### CI/CD Pipeline

```
PR to main:
  1. ✅ Python syntax check
  2. ✅ Critical imports validation
  3. ✅ Frontend build (Next.js)
  4. ⏭️ Lint warnings (non-blocking)

Merge to main:
  1. 🚀 Deploy frontend (rsync → DigitalOcean)
  2. 🚀 Deploy backend (pip install + restart uvicorn)
  3. 🚀 Reload nginx
  4. ✅ Health check (curl https://app.aurity.io)
  5. 🏷️ Create git tag (deploy-YYYYMMDD-HHMMSS)
```

---

## 🔒 Security & Compliance

### HIPAA Compliance

- ✅ **Data Residency**: On-prem HDF5 storage (no cloud PHI)
- ✅ **User Isolation**: `owner_user_id` filter on all queries
- ✅ **Encryption**: AES-GCM-256 at-rest, HTTPS in-transit
- ✅ **Audit Trail**: All document access logged with user_id
- ✅ **RBAC**: Auth0 roles (`FI-superadmin`, `FI-doctor`, etc.)

### Auth0 Integration

```typescript
// JWT contains roles claim
const roles = user['https://aurity.app/roles'] as string[];

// Backend validates JWT + roles
@router.get("/documents")
async def list_documents(
    current_user: User = Depends(get_current_user)
):
    # Only returns documents owned by current_user
    return document_repository.list_documents(user_id=current_user.user_id)
```

---

## 📊 Performance Metrics

### RAG Embeddings (GPU vs CPU)

| Device | Latency (avg) | Acceptable? |
|--------|---------------|-------------|
| RTX 4060 (CUDA) | 20-30ms | ✅ Production |
| M1 Pro (MPS) | 40-50ms | ✅ Production |
| CPU (sentence-transformers) | 100-150ms | ❌ Unacceptable |

### Chat SLO

- p95 latency: ≤ 800ms (end-to-end)
- RAG search: ≤ 200ms
- LLM inference: ≤ 500ms
- Error rate: < 1%

### Storage

- HDF5 compression: ~70% reduction (gzip level 4)
- Single file: `backend/storage/corpus.h5`
- Backup: Simple file copy (atomic, consistent)

---

## 🎯 Roadmap

### Current (v1.0 - Production)
- ✅ RAG GPU embeddings (FI Monitor)
- ✅ HIPAA-compliant storage (HDF5)
- ✅ User isolation (Auth0 + owner_user_id)
- ✅ Production deployment (app.aurity.io)
- ✅ GPU-only architecture (no CPU fallback)

### Next (v1.1)
- [ ] Multi-tenant clinics (clinic_id isolation)
- [ ] Document sharing (shared_with field)
- [ ] Azure Blob tunnel discovery (auto-detect FI Monitor)
- [ ] Performance dashboard (embedding latency, cache hits)
- [ ] Mobile app (React Native + Auth0)

---

## 📚 Stack Tecnológico

**Backend:**
- Python 3.14, FastAPI, Uvicorn
- HDF5 (h5py) - Single-file storage
- sentence-transformers (GPU embeddings)
- Auth0 (JWT + RBAC)
- structlog (structured logging)

**Frontend:**
- Next.js 14 (Static Export)
- React 18, TypeScript
- Tailwind CSS
- Auth0 SDK

**GPU Service (FI Monitor):**
- Tauri (Rust) - Desktop app framework
- Python (FastAPI) - RAG service + Gateway
- Ollama - Local LLM (Qwen3:1.7b)
- Cloudflare Tunnel - Secure exposure

**Infrastructure:**
- DigitalOcean (app.aurity.io)
- Nginx (reverse proxy + SSL)
- Let's Encrypt (SSL certs)
- GitHub Actions (CI/CD)

---

## 🤝 Contributing

Proyecto personal de Bernard Uriza Orozco. Contribuciones externas no aceptadas.

**Filosofía:**
> "GPU-first, no compromises. Like modern gaming - works perfectly or doesn't work at all."

---

## 📄 License

Private project. All rights reserved © 2026 Bernard Uriza Orozco.

---

## 🔗 Links

- **Production**: https://app.aurity.io
- **Documentation**: `docs/README.md`
- **Architecture**: `.claude/CLAUDE.md`
- **GPU Integration Tests**: `test_rag_integration.py`

---

**Free Intelligence: GPU-Accelerated AI for Healthcare** 🧠⚡

*"El usuario prefiere no ver nada que ver gráficos chafos"*
