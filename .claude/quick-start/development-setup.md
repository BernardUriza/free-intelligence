# Development Setup

**Last Updated:** 2026-11-03
**Status:** Active

---

## Prerequisites

- **Node 20+** and **pnpm 10** (monorepo package manager)
- **Python 3.12+** for the og118 server (its Dockerfile runs 3.12)
- `lsof` (used by `make dev-kill`)

---

## Quick Setup

```bash
# 1. Clone
git clone https://github.com/BernardUriza/free-intelligence.git
cd free-intelligence

# 2. JS dependencies (the lockfile is the source of truth)
pnpm install --frozen-lockfile

# 3. og118 server environment (full steps: apps/og118/server/README.md)
cd apps/og118/server
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt pytest-asyncio
pip install -e "../../packages/fi-runner[claude]"
pip install -e "../../packages/fi-core[stores-hdf5]"
cd -

# 4. Credentials (gitignored, never committed)
#    apps/og118/server/.env.local  -> ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN
#    apps/og118/web/.env.local     -> auth0 mode + NEXT_PUBLIC_OG118_API=http://localhost:8118

# 5. Verify
pnpm version:check
make test
```

---

## Run

```bash
make dev          # server :8118 + web :3000
make dev-kill     # stop both
```

Log in through Auth0 on http://localhost:3000; it's a registered callback. Don't
switch the web to `bearer` mode to skip the login when you're judging how the app
looks: see `.claude/rules/local-dev-auth-mode-parity.md`.

---

## Verification

```bash
curl -s http://localhost:8118/health      # {"ok":true}
node scripts/check-console-errors.mjs http://localhost:3000/
```

---

## Troubleshooting

### Port already in use
```bash
make dev-kill
```

### `missing apps/og118/server/.venv`
Run step 3 above.

### `ERROR: set ANTHROPIC_API_KEY ... or CLAUDE_CODE_OAUTH_TOKEN`
`run.sh` found neither in `apps/og118/server/.env.local`.

---

## Next Steps

- [development/workflow.md](../development/workflow.md): git flow and local og118
- [development/version-management.md](../development/version-management.md): FI Monitor versions
