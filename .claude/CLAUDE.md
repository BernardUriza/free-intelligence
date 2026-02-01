# Free Intelligence · Quick Reference (v0.8.0)

**AURITY — Advanced Universal Reliable Intelligence for Telemedicine Yield**

**Owner:** Bernard Uriza Orozco
**Version:** 0.1.1 (Production)
**Updated:** 2026-01-31 (Hong Kong Transformation)
**TZ:** America/Mexico_City

---

## 🚀 Quick Start

```bash
# Development
make dev-all              # Cloud-dev (tunnel + backend + frontend, ~60s startup)
make dev-all-local        # Local-only (no tunnel, ~30s startup, faster iterations)
make dev-kill             # Kill all dev processes
make test                 # pytest

# Production Deploy
git push origin dev       # → PR to main → CI/CD auto-deploy

# Desktop Builds
gh workflow run build-desktop.yml -f platform=windows
```

**Full docs:** [.claude/README.md](.claude/README.md)

---

## 📚 Documentation Hub

**Navigation:** [.claude/README.md](.claude/README.md)

```
.claude/
├── quick-start/          # Setup guides
├── development/          # Workflows, version mgmt
├── architecture/         # Backend refactor, multi-tenancy
├── operations/ci-cd/     # Windows builds, optimizations
├── security/             # Credentials, SSH policy
├── integrations/         # Browser MCPs
└── guides/               # Mentor mode, insult mode
```

---

## 🎯 Core Principles

1. **Bernard's Workflow:** Simplicity, focus, no tangents → [development/workflow.md](development/workflow.md)
2. **Git Flow:** Work in `dev`, PR to `main` → [development/workflow.md](development/workflow.md#git-workflow)
3. **Security:** ZERO TOLERANCE for secrets → [security/credentials.md](security/credentials.md)
4. **Production:** CI/CD only, no manual edits → [security/ssh-policy.md](security/ssh-policy.md)

---

## ⚙️ Version Management

**Single Source of Truth:** `apps/*/src-tauri/tauri.conf.json`

```bash
pnpm version:check    # Validate consistency
pnpm version:sync     # Sync all files
```

**See:** [development/version-management.md](development/version-management.md)

---

## 🏗️ Project Structure

```
free-intelligence/
├── backend/              # FastAPI + HDF5 (Clean Architecture)
│   ├── infrastructure/  # Auth, workers, observability
│   ├── services/        # Business logic (8 extracted)
│   ├── api/             # HTTP layer
│   └── core/            # Legacy (DI refactor pending)
├── apps/
│   ├── aurity/          # Next.js frontend
│   ├── aurity-desktop/  # Tauri desktop app
│   └── fi-monitor/      # Windows monitor app
└── .claude/             # Documentation (Hong Kong standard)
```

---

## 🔗 Quick Links

- **Production:** https://app.aurity.io
- **Backend:** https://app.aurity.io/api/
- **Full Docs:** [.claude/README.md](.claude/README.md)
- **Setup Guide:** [.claude/quick-start/development-setup.md](.claude/quick-start/development-setup.md)

---

## 🚫 Critical Rules

### No Emojis in Code
```typescript
// ❌ PROHIBITED
const services = [{ icon: '🩺', name: 'Consulta' }];

// ✅ CORRECT
import { Stethoscope } from 'lucide-react';
const services = [{ icon: Stethoscope, name: 'Consulta' }];
```

### No Dangerous Windows Commands
```powershell
# ❌ PROHIBITED - Kills Claude Code
taskkill /F /IM node.exe

# ✅ CORRECT - Kill by port
$pid = (Get-NetTCPConnection -LocalPort 9000 -ErrorAction SilentlyContinue).OwningProcess | Select-Object -First 1
if ($pid) { Stop-Process -Id $pid -Force }
```

### Visual Verification Required
```bash
# After any UI change, MUST verify:
node scripts/check-console-errors.mjs http://localhost:9000/<route>
node scripts/screenshot-cdp.mjs <URL> <output.png>
powershell -Command "Start-Process '<output.png>'"  # Show to user
```

---

## 🏷️ Conventions

- **Commits:** Conventional Commits (feat/fix/docs/chore)
- **Branches:** dev (work) + main (production only)
- **PRs:** AI Gatekeeper (GPT-5) approval required
- **Docs:** Hong Kong standard (zero bloat, zero duplication)

---

**For complete documentation, see:** [.claude/README.md](.claude/README.md)

**This is a quick reference only. All details are in the documentation hub.**
