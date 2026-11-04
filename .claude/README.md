# Free Intelligence Documentation

**Project:** AURITY — Advanced Universal Reliable Intelligence for Telemedicine Yield
**Owner:** Bernard Uriza Orozco
**Version:** 0.1.1 (Production)
**Updated:** 2026-01-31 (Hong Kong Transformation)

---

## 🚀 Quick Start

```bash
# Development (og118: server :8118 + web :3000)
make dev                  # both; or make dev-server / make dev-web
make dev-kill             # stop whatever listens on :8118 / :3000
make test                 # og118 server pytest + og118-web vitest

# Production Deploy (commit on local main, remote-only PR ref)
git push origin HEAD:refs/heads/bernarduriza/<slug>
gh pr create --base main --head bernarduriza/<slug>   # merge → CI/CD auto-deploy

# FI Monitor (Windows) build
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
├── operations/ci-cd/            # Windows builds, optimizations
├── security/                    # Credentials, SSH policy
├── integrations/                # Browser MCPs
├── guides/                      # Mentor mode, insult mode
├── backlog/                     # Proposed / in-progress items
└── history/                     # Archived learnings (2025)
```

---

## 🎯 Core Principles

### 1. Bernard's Workflow
**Simplicity, focus, no tangents, fast results.**

- Commit on local `main`; a PR rides a remote-only `bernarduriza/<slug>` ref
- Minimal changes only
- Verify → Commit → Push → PR → DONE
- **Never** go on tangents or offer unsolicited "improvements"

**See:** [development/workflow.md](development/workflow.md)

### 2. Git Flow
- **main** is the only branch at rest (protected: PR + CI + AI Gatekeeper)
- PRs ride a remote-only `bernarduriza/<slug>` ref, deleted on merge (`dev` retired 2026-07-06)

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

- **Live app:** og118 — https://app.og118.ai (web on the `og118-web-staging` SWA, server `og118-api` on Azure Container Apps)
- **Framework:** `apps/packages/fi-glass` (chat UI), `fi-runner` (agent runtime), `fi-core` / `free-intelligence-core`
- **aurity:** the SSOT of fi-glass's shape; read it, do not run it (see `.claude/CLAUDE.md`)

---

## 🛠️ Development

### Local og118
`make dev` runs `apps/og118/server/run.sh` (auth mode from its `.env.local`) and
`pnpm --filter og118-web dev` (auth0 mode, see `.claude/rules/local-dev-auth-mode-parity.md`).
Server `.venv` setup: `apps/og118/server/README.md`.

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

### Archived Learnings (2025)
- Next.js static export quirks
- asyncio timeout with httpx
- SQLite UUID type affinity
- 500 error debugging layers

**See:** [history/2025-learnings/](history/2025-learnings/)

---

## ⚡ Executive Kernel

**Deployment:**
- **Main branch:** Production (protected, CI/CD only)
- **PRs:** AI Gatekeeper required approval

**Security:**
- ZERO TOLERANCE for hardcoded secrets
- Production SSH for audits only (read-only)
- All deployments via CI/CD (no manual rsync/scp)

---

## 🔗 Quick Links

- **Production:** https://app.og118.ai
- **CI/CD Workflows:** `.github/workflows/`
- **FI Monitor:** Windows (NSIS) via `build-desktop.yml`

---

**This is the Hong Kong standard: zero bloat, zero duplication, maximum efficiency.**
