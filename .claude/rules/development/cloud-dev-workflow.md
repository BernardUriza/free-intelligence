# Cloud-Dev Workflow

**Purpose:** Replicate production architecture in local dev environment.

## Architecture

**Production:**
```
Desktop → fi-monitor (cloudflared) → Azure Blob → Cloud Backend (TunnelURLProvider) → Frontend
```

**Cloud-Dev:**
```
Local → fi-monitor (cloudflared) → Local File → Local Backend (TunnelURLProvider) → Local Frontend
```

## Commands

```bash
# Start all services with tunnel (default)
make dev-all

# Start without tunnel (faster, local-only)
make dev-all-local

# Kill all dev processes
make dev-kill

# Restart services
make dev-restart
```

## Startup Sequence

**Cloud-dev (make dev-all):**
1. [0/5] Cleanup existing processes
2. [1/5] Check prerequisites (Python 3.14, Node, pnpm)
3. [2/5] Initialize storage (corpus.h5)
4. [3/5] Start fi-monitor → wait for tunnel URL (45s timeout)
5. [4/5] Start backend (TunnelURLProvider polls local file)
6. [5/5] Start frontend (connects to localhost:7001)

**Local-only (make dev-all-local):**
- Skips step 3 (no fi-monitor)
- Backend uses localhost:11434 directly
- Faster startup (~30s vs ~60s)

## Troubleshooting

### Tunnel timeout (45s)
**Symptom:** `⚠️  Tunnel timeout (45s), falling back to localhost`

**Causes:**
- fi-monitor failed to start → check `logs/fi-monitor-dev.log`
- cloudflared not installed → `brew install cloudflared`
- Port 11434 blocked → Ollama not running

**Fix:**
```bash
# Check logs
tail -f logs/fi-monitor-dev.log

# Start Ollama
ollama serve

# Restart dev
make dev-restart
```

### Backend can't reach Ollama via tunnel
**Symptom:** `curl http://localhost:7001/api/internal/ollama/health` returns 503

**Causes:**
- Tunnel URL stale (> 10 minutes old)
- fi-monitor stopped
- Network issue

**Fix:**
```bash
# Check tunnel file
cat ~/.config/fi-monitor/tunnel-url.json

# Verify timestamp is recent (< 10 min)
# Restart services
make dev-restart
```

### fi-monitor won't start
**Symptom:** `Error: Command not found: pnpm`

**Fix:**
```bash
# Install pnpm
npm install -g pnpm@latest

# Verify directory exists
ls apps/fi-monitor/
```

## Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `DEPLOYMENT_TARGET` | `cloud` | Enables cloud config in backend |
| `FI_USE_TUNNEL` | `true` | Activates TunnelURLProvider polling |
| `FI_TUNNEL_BLOB_URL` | `file://~/.config/fi-monitor/tunnel-url.json` | Local tunnel file path |

## Comparison: dev-all vs dev-all-local

| Feature | dev-all (cloud-dev) | dev-all-local |
|---------|---------------------|---------------|
| **Tunnel** | ✅ Cloudflared | ❌ None |
| **Ollama** | Via tunnel | Direct localhost |
| **Startup** | ~60s (tunnel wait) | ~30s (skip tunnel) |
| **Network** | Offline OK (local file) | Offline OK |
| **Production Parity** | ✅ High | ⚠️  Medium |
| **Use case** | Testing tunnel flow | Quick iterations |

## File Locations

- **Tunnel URL:** `~/.config/fi-monitor/tunnel-url.json`
- **Logs:**
  - `logs/fi-monitor-dev.log` (fi-monitor + cloudflared)
  - `logs/backend-dev.log` (FastAPI)
  - `logs/frontend-aurity-dev.log` (Next.js)
- **Storage:** `storage/corpus.h5` (HDF5)

## How It Works

1. **fi-monitor starts cloudflared:**
   - Command: `cloudflared tunnel --url http://localhost:11434`
   - Tunnel URL appears in stderr: `https://abc-123.trycloudflare.com`
   - fi-monitor extracts URL via regex

2. **fi-monitor publishes URL:**
   - Writes to local file: `~/.config/fi-monitor/tunnel-url.json`
   - Format: `{"tunnel_url": "https://...", "updated_at": "2026-01-26T..."}`
   - Re-uploads every 5 minutes to keep timestamp fresh

3. **Backend discovers tunnel:**
   - `TunnelURLProvider` reads local file (via `file://` protocol)
   - Validates freshness (< 10 minutes)
   - Caches for 60 seconds
   - Falls back to `http://localhost:11434` if unavailable

4. **Frontend connects:**
   - Uses `http://localhost:7001` (backend API)
   - Backend proxies LLM calls to Ollama via tunnel

## Benefits

**Cloud-dev (make dev-all):**
- ✅ Replicates production architecture (catches integration bugs early)
- ✅ Tests tunnel discovery flow
- ✅ Tests TunnelURLProvider caching/fallback logic
- ✅ Works offline (local file, no Azure dependency)
- ⚠️  Slower startup (~60s)

**Local-only (make dev-all-local):**
- ✅ Faster startup (~30s)
- ✅ Simpler setup (no fi-monitor dependency)
- ✅ Good for quick UI iterations
- ⚠️  Doesn't test tunnel integration

## When to Use Each Mode

**Use `make dev-all` (cloud-dev) when:**
- Testing tunnel-related features
- Debugging TunnelURLProvider issues
- Validating production parity
- Working on fi-monitor integration

**Use `make dev-all-local` when:**
- Iterating on UI changes
- Working on backend logic unrelated to tunnels
- Need faster feedback loop
- fi-monitor not available (e.g., CI/CD)

## Testing Checklist

After starting cloud-dev, verify:

```bash
# 1. Check tunnel file exists and is fresh
cat ~/.config/fi-monitor/tunnel-url.json
# Should show: {"tunnel_url": "https://...", "updated_at": "2026-01-26T..."}

# 2. Verify backend health
curl http://localhost:7001/health
# Should return: {"status": "healthy"}

# 3. Test Ollama access via tunnel
curl http://localhost:7001/api/internal/ollama/health
# Should return: 200 OK (or 503 if tunnel failed, but backend still healthy)

# 4. Check frontend
open http://localhost:9000
# Should load without errors

# 5. Check logs for errors
tail -n 50 logs/fi-monitor-dev.log
tail -n 50 logs/backend-dev.log
tail -n 50 logs/frontend-aurity-dev.log
```

## Common Errors

### Error: "fi-monitor app not found at apps/fi-monitor/"
**Cause:** fi-monitor directory doesn't exist
**Fix:** Verify you're in repo root: `ls apps/`

### Error: "Command not found: pnpm"
**Cause:** pnpm not installed
**Fix:** `npm install -g pnpm@latest`

### Error: "Port 7001 already in use"
**Cause:** Previous backend process still running
**Fix:** `make dev-kill` then `make dev-all`

### Warning: "Tunnel timeout (45s), falling back to localhost"
**Cause:** fi-monitor/cloudflared startup too slow
**Impact:** Backend uses localhost:11434 (degrades to local-only mode)
**Fix:** Check fi-monitor logs, restart Ollama, increase timeout if needed

## Advanced Configuration

### Custom tunnel timeout
Edit `backend/src/fi_cli/domains/dev.py`:
```python
tunnel_url = wait_for_tunnel_ready(timeout_s=60)  # Increase to 60s
```

### Disable tunnel health check
Edit `backend/src/fi_model_catalog/services/tunnel_url_provider.py`:
```python
TunnelURLProvider(verify_tunnel_health=False)  # Skip health check
```

### Change cache TTL
```python
TunnelURLProvider(cache_ttl_seconds=120)  # Cache tunnel URL for 2 minutes
```

## Performance Notes

- **Tunnel startup:** 10-30s (cloudflared connection)
- **Backend startup:** 5-10s (FastAPI + dependencies)
- **Frontend startup:** 15-30s (Next.js + Turbopack)
- **Total cloud-dev startup:** ~60s
- **Total local-only startup:** ~30s

## Future Improvements

- [ ] Parallel service startup (fi-monitor + backend simultaneously)
- [ ] Progress bars for each startup phase
- [ ] Automatic retry on fi-monitor failure
- [ ] Dashboard showing service status (similar to Turborepo UI)

---

**See also:**
- `.claude/CLAUDE.md` - Quick reference
- `.claude/rules/development/bernard-workflow.md` - Git workflow
- `.claude/rules/architecture/desktop-app.md` - fi-monitor architecture
