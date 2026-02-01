# Free Intelligence Documentation

**Project:** AURITY — Advanced Universal Reliable Intelligence for Telemedicine Yield
**Owner:** Bernard Uriza Orozco
**Version:** 0.1.1 (Production)
**Updated:** 2026-01-31 (Hong Kong Transformation)

---

## 🚀 Quick Start

```bash
# Development
make dev-all              # Cloud-dev (~60s startup, production parity)
make dev-all-local        # Local-only (~30s startup, faster iterations)
make dev-kill             # Kill all dev processes
make test                 # pytest

# Production Deploy
git push origin dev       # → PR to main → CI/CD auto-deploy

# Desktop Builds
gh workflow run build-desktop.yml -f platform=windows
```

**See:** [quick-start/](quick-start/) for detailed setup guides

---

## 📚 Documentation Structure

```
.claude/
├── README.md (you are here)     # Navigation hub
├── quick-start/                 # Getting started guides
├── development/                 # Workflows, version mgmt, Python 3.14
├── architecture/                # Backend refactor, multi-tenancy, desktop
├── operations/ci-cd/            # Windows builds, optimizations, testing
├── security/                    # Credentials, SSH policy
├── integrations/                # Browser MCPs
├── guides/                      # Mentor mode, insult mode
└── history/                     # Archived learnings (2025)
```

---

## 🎯 Core Principles

### 1. Bernard's Workflow
**Simplicity, focus, no tangents, fast results.**

- Work in `dev` branch ALWAYS
- Minimal changes only
- Verify → Commit → Push → PR → DONE
- **Never** go on tangents or offer unsolicited "improvements"

**See:** [development/workflow.md](development/workflow.md)

### 2. Git Flow (2-Branch Model)
- **dev** → Active development (multi-feature, multi-agent)
- **main** → Production (protected, requires PR + CI)
- **Critical:** Sync dev with main after EVERY merge

**See:** [development/workflow.md#git-workflow](development/workflow.md)

### 3. Security (ZERO TOLERANCE)
- **No hardcoded secrets** (API keys, passwords, tokens)
- **No manual production edits** (CI/CD only)
- **SSH for audits only** (read-only operations)

**See:** [security/](security/)

### 4. Version Management
- **Single Source of Truth:** `apps/*/src-tauri/tauri.conf.json`
- Run `pnpm version:sync` after version changes
- CI/CD validates consistency (blocks builds if mismatched)

**See:** [development/version-management.md](development/version-management.md)

---

## 🏗️ Architecture

### Production Environment
- **Live:** https://app.aurity.io/
- **Backend:** https://app.aurity.io/api/
- **Topology:** Nginx (SSL) → Next.js (static) + FastAPI (7001)

### Backend Structure (Clean Architecture)
```
backend/
├── infrastructure/     # Auth, workers, observability (Phase 2.2 ✅)
├── services/          # Business logic (Phase 1 ✅ - 8 services extracted)
├── api/               # HTTP layer (routers)
├── repositories/      # Data access (interfaces defined ✅)
└── core/              # Legacy (71 files, DI refactor pending)
```

**Status:** Phase 2.2 Complete (Infrastructure extracted)
**Next:** Phase 2.3 (DI Refactor) - 5 hours estimated

**See:** [architecture/backend-refactor.md](architecture/backend-refactor.md)

---

## 🛠️ Development

### Cloud-Dev Mode
Replicates production architecture locally with cloudflared tunnel.

**When to use:**
- Testing tunnel-related features
- Validating production parity
- Working on fi-monitor integration

**When to use local mode:**
- Quick UI iterations
- Backend logic unrelated to tunnels
- Faster feedback loop (~30s vs ~60s)

**See:** [development/workflow.md#cloud-dev-mode](development/workflow.md)

### Version Management
```bash
# Check consistency
pnpm version:check

# Sync all files
pnpm version:sync

# Install pre-commit hook (optional)
pnpm version:install-hook
```

**See:** [development/version-management.md](development/version-management.md)

---

## 🚢 CI/CD & Deployment

### Windows Builds Journey
**17 errors resolved** across 3 days (PyInstaller → Rust → Signing → NSIS).

Key learnings:
- Cross-platform modules (fcntl → portalocker)
- Ed25519 signing (zero cost, SmartScreen warnings OK)
- Build optimizations (sccache, cargo incremental, cache layers)

**See:** [operations/ci-cd/windows-builds.md](operations/ci-cd/windows-builds.md)

### Build Optimizations
5 quick wins → **35-48% faster builds** (23 min → 12-15 min):
- sccache v0.0.9 (GHA cache enabled)
- Cargo incremental compilation
- PyInstaller build cache
- Separated cache layers (cargo deps vs sccache)
- Concurrency groups (cancel redundant builds)

**See:** [operations/ci-cd/build-optimizations.md](operations/ci-cd/build-optimizations.md)

---

## 🔐 Security

### Credentials Policy (ZERO TOLERANCE)
**Never commit:**
- API keys (Azure, AWS, Deepgram, OpenAI, Auth0)
- Passwords or tokens
- Database connection strings with credentials
- Any string matching: `sk-*`, `api_*`, `key=*`, `token=*`

**Always use:** `.env` files (gitignored), secret managers

**See:** [security/credentials.md](security/credentials.md)

### Production SSH Policy (ENFORCED)
**Allowed:** Read-only operations (tail logs, view files, ps, curl health)
**Forbidden:** vim, nano, git commit, pip install, systemctl restart

**Correct process:** Push to GitHub → PR → CI/CD auto-deploy

**See:** [security/ssh-policy.md](security/ssh-policy.md)

---

## 🧩 Integrations

### Browser MCPs
- **Chrome DevTools MCP** - Automated browser testing (clicks, navigation, screenshots)
- **Browser Tools MCP** - Console logs, network requests, audits

**See:** [integrations/browser-mcps.md](integrations/browser-mcps.md)

---

## 📖 Guides

### Mentor Mode 🔥
Demanding, direct feedback in Spanish with constant improvement challenges.

**Activate:** "activa mentor mode" or "modo mentor"

**See:** [guides/mentor.md](guides/mentor.md)

### El Revisor Agresivo
Prompt for aggressive personality engineering (code reviews).

**See:** [guides/insult.md](guides/insult.md)

---

## 📜 History & ADRs

### Backend Refactor Journey
- **Phase 1:** Service extraction (77% reduction, 7→3 levels)
- **Phase 2.1:** Interface definitions (8 interfaces, Clean Architecture)
- **Phase 2.2:** Infrastructure extraction (75 files moved)
- **Phase 2.3:** DI refactor (pending - Service Locator elimination)

**See:** [architecture/backend-refactor.md](architecture/backend-refactor.md)

### Multi-Tenancy
- **Phase 1:** Auth0 clinic_id extraction (complete ✅)
- **Phase 2:** Repository filtering (documented, pending - 19 files)

**See:** [architecture/multi-tenancy-phase2.md](architecture/multi-tenancy-phase2.md)

### Archived Learnings (2025)
- Next.js static export quirks
- asyncio timeout with httpx
- SQLite UUID type affinity
- 500 error debugging layers

**See:** [history/2025-learnings/](history/2025-learnings/)

---

## ⚡ Executive Kernel

**Architecture Principles:**
- **Single Entry:** PUBLIC → INTERNAL → WORKER (no exceptions)
- **Append-only:** Clinical data in HDF5 (sha256 integrity)
- **Zero trust:** Between layers, RBAC Auth0 for ADMIN
- **Observability:** By default (SLOs explicit, kill-switch ready)

**Deployment:**
- **Main branch:** Production (protected, CI/CD only)
- **Dev branch:** Active development (multi-agent chaos)
- **PRs:** AI Gatekeeper (GPT-5) required approval

**Security:**
- ZERO TOLERANCE for hardcoded secrets
- Production SSH for audits only (read-only)
- All deployments via CI/CD (no manual rsync/scp)

---

## 🔗 Quick Links

- **Production:** https://app.aurity.io
- **Backend API:** https://app.aurity.io/api/
- **CI/CD Workflows:** `.github/workflows/`
- **Desktop Apps:** Windows (NSIS), macOS (DMG), Linux (AppImage)

---

**This is the Hong Kong standard: zero bloat, zero duplication, maximum efficiency.**
