# Free Intelligence · Quick Reference (v0.7.3)

**AURITY — Advanced Universal Reliable Intelligence for Telemedicine Yield**

**Owner:** Bernard Uriza Orozco  
**Version:** 0.1.1 (Production)  
**Updated:** 2026-01-20  
**TZ:** America/Mexico_City

---

## 🚀 Quick Start

```bash
# Development
make dev-all              # Backend (7001) + Frontend (9000)
make test                 # pytest
pnpm dev                  # Next.js only

# Production Deploy
git push origin dev       # → PR to main → CI/CD auto-deploy

# Desktop Builds
gh workflow run build-desktop.yml -f platform=windows
```

## 📂 Project Structure

```
free-intelligence/
├── backend/              # FastAPI + HDF5 storage
│   ├── app/main.py      # CORS/entry
│   ├── api/
│   │   ├── public/workflows/     # PUBLIC API
│   │   └── internal/             # INTERNAL (blocked)
│   └── workers/         # ThreadPoolExecutor
├── apps/
│   ├── aurity/          # Next.js frontend (production)
│   ├── aurity-desktop/  # Tauri desktop app
│   └── fi-monitor/      # Windows monitor app
└── .claude/
    ├── CLAUDE.md        # This file (quick reference)
    └── rules/           # 📚 Detailed docs by topic
```

## 🔗 Quick Links

- **Production:** https://app.aurity.io
- **Backend:** https://app.aurity.io/api/
- **Detailed Docs:** `.claude/rules/` (organized by topic)
- **CI/CD:** `.github/workflows/`

## 📚 Documentation Organization

Detailed documentation is organized in `.claude/rules/`:

```
.claude/rules/
├── ci-cd/
│   ├── windows-builds.md     # Debugging journey (8 errors + fixes)
│   ├── github-actions.md     # Workflows, AI Gatekeeper
│   └── deployment.md         # Production deploy
├── development/
│   ├── bernard-workflow.md   # 🎯 How to work with Bernard
│   ├── git-workflow.md       # 2-branch model (dev/main)
│   ├── python-314.md         # Python 3.14 requirements
│   └── code-style.md         # Conventions, commits
├── security/
│   ├── credentials.md        # ZERO TOLERANCE secret policy
│   ├── ssh-policy.md         # Production access rules
│   └── incidents.md          # Security incident log
├── integrations/
│   ├── browser-mcps.md       # Chrome DevTools, Browser Tools
│   ├── ollama.md             # LLM setup, smoke tests
│   └── cloudflare.md         # Tunnel, observability
└── architecture/
    ├── aurity-cloud.md       # Production topology
    ├── desktop-app.md        # Tauri, PyInstaller
    └── layering.md           # PUBLIC → INTERNAL → WORKER
```

## ⚡ Executive Kernel

- **Single Entry:** PUBLIC → INTERNAL → WORKER (no excepciones)
- **Only PUBLIC routes** bajo `/api/workflows/aurity/*`
- **Append-only** en datos clínicos (HDF5); integridad por sha256
- **Zero trust** entre capas; RBAC Auth0 en ADMIN
- **SLOs explícitos;** observabilidad por defecto; kill-switch listo

## 🌐 Production Environment

- **Live:** https://app.aurity.io/
- **Backend:** https://app.aurity.io/api/
- **SSL:** Let's Encrypt (auto-renew)
- **DNS:** app.aurity.io → 104.131.175.65
- **Topology:** Nginx (SSL) → Next.js (static) + FastAPI (7001)

## 🔑 Core Principles

1. **Bernard Workflow:** Simplicidad, enfoque, no tangentes → Ver `.claude/rules/development/bernard-workflow.md`
2. **Git Flow:** Always work in `dev`, PR to `main` → Ver `.claude/rules/development/git-workflow.md`  
3. **Security:** ZERO TOLERANCE for hardcoded secrets → Ver `.claude/rules/security/credentials.md`
4. **Production:** NO manual edits, CI/CD only → Ver `.claude/rules/security/ssh-policy.md`

## 🐛 Troubleshooting

- **Windows Builds:** Ver `.claude/rules/ci-cd/windows-builds.md`
- **Git Issues:** Ver `.claude/rules/development/git-workflow.md`
- **Security:** Ver `.claude/rules/security/`
- **Turbopack:** Limpiar `.next .turbo .swc node_modules/.cache` y reiniciar
- **Puertos:** `lsof -ti:9000 | xargs kill -9`

## 🏷️ Conventions

- **Commits:** Conventional Commits (feat/fix/docs/chore)
- **Branches:** dev (work) + main (production only)
- **PRs:** Require AI Gatekeeper (GPT-5) approval
- **Docs:** Keep CLAUDE.md brief, details in `.claude/rules/`

---

**Este kernel context existe para que cualquier persona (humana o máquina) entienda cómo se mueve el sistema en 2 minutos: entradas, límites, garantías y rutas de escape.**

**Para detalles específicos, ver `.claude/rules/` organizado por tema.**
