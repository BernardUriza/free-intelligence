# Development Setup

**Last Updated:** 2026-01-31
**Status:** Active

---

## Prerequisites

### Required
- **Python 3.14+** (JIT compiler, t-strings, lazy annotations)
- **Node 20+** (Next.js, pnpm)
- **pnpm 9+** (monorepo package manager)

### Optional (for full stack)
- **Ollama** (local LLM for cloud-dev mode)
- **cloudflared** (tunnel for production parity)

---

## Quick Setup (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/BernardUriza/free-intelligence.git
cd free-intelligence

# 2. Install dependencies
pnpm install

# 3. Setup Python environment
cd backend
python3.14 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows
pip install -r requirements-prod.txt

# 4. Verify setup
pnpm version:check        # Version consistency
make test                 # Backend tests
```

---

## Development Modes

### Local-Only Mode (Fastest - ~30s startup)
```bash
make dev-all-local
```

**Use when:**
- Iterating on UI changes
- Working on backend logic unrelated to tunnels
- Need fastest feedback loop

**Architecture:**
```
Backend (localhost:7001) → Ollama (localhost:11434) → Frontend (localhost:9000)
```

### Cloud-Dev Mode (Production Parity - ~60s startup)
```bash
make dev-all
```

**Use when:**
- Testing tunnel-related features
- Validating production parity
- Working on fi-monitor integration

**Architecture:**
```
fi-monitor → cloudflared tunnel → Backend (TunnelURLProvider) → Frontend
```

---

## Verification

After starting dev mode, verify:

```bash
# 1. Backend health
curl http://localhost:7001/health
# Expected: {"status": "healthy"}

# 2. Frontend
open http://localhost:9000
# Expected: Auth0 login page

# 3. Ollama (cloud-dev only)
curl http://localhost:7001/api/internal/ollama/health
# Expected: 200 OK (or 503 if Ollama not running - acceptable)
```

---

## Troubleshooting

### Python version mismatch
**Error:** `SyntaxError: invalid syntax` (t-strings not supported)
**Fix:**
```bash
python --version  # Should show 3.14.x
pyenv install 3.14.0
pyenv local 3.14.0
```

### pnpm not found
**Fix:**
```bash
npm install -g pnpm@latest
pnpm --version  # Should show 9.x
```

### Port already in use
**Error:** `EADDRINUSE: address already in use :::7001`
**Fix:**
```bash
make dev-kill      # Kill all dev processes
make dev-restart   # Start fresh
```

### Tunnel timeout (cloud-dev)
**Error:** `⚠️ Tunnel timeout (45s), falling back to localhost`
**Fix:**
```bash
# Install cloudflared
brew install cloudflared  # macOS
# or download from https://github.com/cloudflare/cloudflared/releases

# Start Ollama
ollama serve

# Restart dev
make dev-restart
```

---

## Next Steps

1. **Read workflow docs:** [.claude/development/workflow.md](../development/workflow.md)
2. **Setup version hook:** `pnpm version:install-hook` (optional)
3. **Try mentor mode:** [.claude/guides/mentor.md](../guides/mentor.md)
4. **Make your first change:** Work in `dev` branch, verify, commit, PR

---

**See also:**
- [Development Workflow](../development/workflow.md)
- [Version Management](../development/version-management.md)
- [Python 3.14 Features](../development/python-314.md)
