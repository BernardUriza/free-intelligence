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
git checkout -b bernarduriza/<slug>   # transient branch → PR to main → CI/CD auto-deploy
# (branch is deleted on merge; main is the only branch at rest)

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
2. **Git Flow:** transient `bernarduriza/<slug>` branch → PR to `main`, branch deleted on merge (`dev` retired 2026-07-06) → [development/workflow.md](development/workflow.md#git-workflow)
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
│   ├── og118/           # LIVE: the shipping app (web + FastAPI/fi-runner server)
│   ├── packages/
│   │   ├── fi-glass/    # the chat framework (aurity is its SSOT)
│   │   ├── fi-runner/   # the agent runtime + the stream contract (SSOT)
│   │   └── free-intelligence-core/
│   ├── aurity/          # LEGACY (see below) — Next.js frontend
│   ├── aurity-desktop/  # Tauri desktop app
│   └── fi-monitor/      # Windows monitor app
└── .claude/             # Documentation (Hong Kong standard)
```

---

## 🔗 Quick Links

- **Production:** https://app.og118.ai — the app that actually ships today

### ⚠️ The "staging" that is actually PRODUCTION

`app.og118.ai` is a CNAME to `calm-mud-0d59ce80f.7.azurestaticapps.net`, which is
the Azure SWA named **`og118-web-staging`**, deployed by
**`.github/workflows/og118-web-staging.yml`** using the secret
**`AZURE_SWA_TOKEN_OG118_STAGING`**.

Three names say "staging". The domain they serve is production. **There is no
other og118-web deploy workflow** — a merge to `main` ships straight to the app
Bernard uses every day.

Verify, never infer from the name:
```bash
dig +short app.og118.ai CNAME
az staticwebapp show -n og118-web-staging -g og118-rg --query defaultHostname -o tsv
# same hostname → the "staging" workflow IS the production deploy
```

This trap has now bitten twice. On 2026-07-20, after merging five fi-glass PRs,
the deploy was read as "staging only" from the workflow name and Bernard was told
his changes were NOT on the URL he uses — they were live the whole time. Do not
repeat it: `staging.og118.ai` is the broken host (invalid cert, see
[[og118-staging-domain-broken]]); `app.og118.ai` is the real surface, and the
badly-named workflow is what feeds it.
- **Full Docs:** [.claude/README.md](.claude/README.md)
- **Setup Guide:** [.claude/quick-start/development-setup.md](.claude/quick-start/development-setup.md)

---

## 🪦 aurity does not SHIP — but it is not dead code (2026-07-11)

**Read this before "NO LEGACY CODE" below sends you deleting it.** The two are not
in conflict, because two different things are being called legacy:

- **The DEPLOYMENT is dead, and stays dead.** aurity's Azure infrastructure NO
  LONGER EXISTS — no Static Web App, no resource of any kind, a dead service
  principal ("No subscriptions found") — and `app.aurity.io` answers nothing (its
  DNS points at a DigitalOcean IP). Its pipeline (`deploy-azure.yml`) is now
  **manual-only**: it used to run on every push and paint `main` red for something
  nobody intends to ship, and a permanently-red pipeline is worse than none — it
  teaches everyone to ignore red.
- **The CODE is the SSOT of fi-glass, and stays.** aurity's chat anatomy — the
  toolbar menu, the staged file-upload flow — is what the framework extracts and
  what og118 renders. It is not "dead code kept for compatibility" (the thing the
  rule below rightly forbids); it is the canonical shape the live app inherits.
  **Read aurity when you need that shape. Do not try to run it. Do not delete it.**

**The live app is og118** (`apps/og118`, https://app.og118.ai).

---

## ⚠️ Project Status

**THIS APP HAS NOT BEEN LAUNCHED. NO USERS. NO DEADLINE.**

Therefore:
- **NO DEPRECATED CODE** - Delete it, don't mark it deprecated
- **NO LEGACY CODE** - Refactor it now, not "later"
- **NO BACKWARD COMPATIBILITY HACKS** - There's nothing to be compatible with
- **NO TODOs FOR "FUTURE"** - Do it now or delete it

If you (Claude) ever justify keeping dead code as "intentional for compatibility" in a pre-launch app, you are wrong. Delete the garbage.

---

## 🚫 Critical Rules

### Backend: Make Only, Never Raw Commands
```bash
# ❌ PROHIBITED - Never run uvicorn/python directly
uvicorn backend.main:app --reload
python -m backend.main
PYTHONPATH=. uvicorn ...

# ✅ CORRECT - Always use Make
make dev-all-local        # Local development
make dev-all              # Cloud development (with tunnel)
make dev-kill             # Stop all services
make test                 # Run tests
```

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

### Mobile Viewport UX
Content dominates on mobile: non-content chrome <18% of viewport, composer idle ≤64px, 12px gutters, secondary controls behind progressive disclosure, touch targets ≥44px. Full budgets, breakpoints and tokens: [.claude/rules/mobile-viewport-ux.md](rules/mobile-viewport-ux.md)

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
- **Branches:** main only at rest; work rides transient `bernarduriza/<slug>` PR branches, deleted on merge
- **PRs:** AI Gatekeeper (GPT-5) approval required
- **Docs:** Hong Kong standard (zero bloat, zero duplication)

---

**For complete documentation, see:** [.claude/README.md](.claude/README.md)

**This is a quick reference only. All details are in the documentation hub.**
