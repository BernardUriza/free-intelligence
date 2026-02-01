# Development Workflow

**Updated:** 2026-01-31 (Hong Kong Transformation)
**Status:** Active
**Consolidates:** bernard-workflow.md + git-workflow.md + cloud-dev-workflow.md

---

## 🎯 Bernard's Principles

Bernard values: **simplicity, focus, no tangents, fast results.**

### Work Process (Follow in Order)

1. Understand what's requested (NO assumptions)
2. Make the minimal necessary change
3. Verify locally (`curl`, `make dev-all`)
4. Commit → Push → PR
5. DONE. Don't add more.

### ❌ Prohibited

- Going on tangents ("we could also...")
- Offering unsolicited solutions
- Overcomplicating simple tasks
- Manual deploys when CI/CD exists
- Asking unrelated questions
- Losing focus on the original task

### ✅ Correct

- Focus ONLY on what was requested
- Verify local → commit → PR → DONE
- ASK before acting if unsure
- Keep responses short when Bernard is irritated

---

## 🌿 Git Workflow (2-Branch Model)

### Branches

```
ONLY TWO BRANCHES:
  • dev  → Active development (multi-feature, multi-agent)
  • main → Production (protected, requires PR + CI)
```

### Daily Commands

```bash
git checkout dev                    # Always work in dev
git add . && git commit -m "..."    # Frequent commits
git push origin dev                 # CI validates automatically
```

### ⚠️ Critical: Sync After Merge

When a PR merges to main, dev becomes BEHIND. **ALWAYS sync**:

```bash
git checkout dev
git fetch origin
git merge origin/main -m "chore: sync dev with main after PR #XX merge"
git push origin dev

# Verify dev is updated
git log origin/main..origin/dev    # Should be empty after sync
```

**Problem:** If you don't sync, PRs will be in "BEHIND" state and can't merge
**Solution:** Sync dev with main after EVERY merge

### Deploy to Production

```bash
gh pr create --base main --head dev --title "Release: description"
# Wait for CI ✅ → Merge → Auto-deploy via CD
```

### Rules for Claude

❌ **NEVER:**
- Create additional branches (no feature branches)
- Push directly to main
- Bypass PR review

✅ **ALWAYS:**
- Work in dev
- Use PR to promote to main
- Verify CI passes before merge
- **CRITICAL:** Sync dev with main after EVERY merge

### Optimization: Delete Local main

This workflow uses 2 REMOTE branches (origin/dev, origin/main) but only needs 1 LOCAL branch (dev).

**Benefits:**
- ✅ Impossible to accidentally commit to main
- ✅ origin/main always truth source
- ✅ Less mental confusion
- ✅ `git diff origin/main..dev` works the same

**How to delete:**
```bash
git checkout dev
git branch -D main  # Safe, doesn't affect remote
```

**After deletion:**
```bash
git fetch origin                    # Update remote refs
git merge origin/main               # Sync from remote
git diff origin/main..dev           # Compare with remote
```

---

## ☁️ Cloud-Dev Mode

### Architecture

**Production:**
```
Desktop → fi-monitor (cloudflared) → Azure Blob → Cloud Backend → Frontend
```

**Cloud-Dev:**
```
Local → fi-monitor (cloudflared) → Local File → Local Backend → Local Frontend
```

### Commands

```bash
# Start all services with tunnel (default)
make dev-all              # ~60s startup

# Start without tunnel (faster, local-only)
make dev-all-local        # ~30s startup

# Kill all dev processes
make dev-kill

# Restart services
make dev-restart
```

### Startup Sequence (Cloud-Dev)

1. **[0/5]** Cleanup existing processes
2. **[1/5]** Check prerequisites (Python 3.14, Node, pnpm)
3. **[2/5]** Initialize storage (corpus.h5)
4. **[3/5]** Start fi-monitor → wait for tunnel URL (45s timeout)
5. **[4/5]** Start backend (TunnelURLProvider polls local file)
6. **[5/5]** Start frontend (connects to localhost:7001)

### Comparison: dev-all vs dev-all-local

| Feature | dev-all (cloud-dev) | dev-all-local |
|---------|---------------------|---------------|
| **Tunnel** | ✅ Cloudflared | ❌ None |
| **Ollama** | Via tunnel | Direct localhost |
| **Startup** | ~60s (tunnel wait) | ~30s (skip tunnel) |
| **Network** | Offline OK (local file) | Offline OK |
| **Production Parity** | ✅ High | ⚠️ Medium |
| **Use case** | Testing tunnel flow | Quick iterations |

### When to Use Each Mode

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

### Troubleshooting

**Tunnel timeout (45s):**
- **Symptom:** `⚠️ Tunnel timeout (45s), falling back to localhost`
- **Causes:** fi-monitor failed to start, cloudflared not installed, port 11434 blocked
- **Fix:**
  ```bash
  tail -f logs/fi-monitor-dev.log  # Check logs
  ollama serve                      # Start Ollama
  make dev-restart                  # Restart dev
  ```

**Backend can't reach Ollama via tunnel:**
- **Symptom:** `curl http://localhost:7001/api/internal/ollama/health` returns 503
- **Causes:** Tunnel URL stale (> 10 min old), fi-monitor stopped, network issue
- **Fix:**
  ```bash
  cat ~/.config/fi-monitor/tunnel-url.json  # Check tunnel file
  make dev-restart                          # Restart services
  ```

### File Locations

- **Tunnel URL:** `~/.config/fi-monitor/tunnel-url.json`
- **Logs:**
  - `logs/fi-monitor-dev.log` (fi-monitor + cloudflared)
  - `logs/backend-dev.log` (FastAPI)
  - `logs/frontend-aurity-dev.log` (Next.js)
- **Storage:** `storage/corpus.h5` (HDF5)

---

## ✅ Verification Checklist

After cloud-dev starts, verify:

```bash
# 1. Check tunnel file exists and is fresh
cat ~/.config/fi-monitor/tunnel-url.json
# Should show: {"tunnel_url": "https://...", "updated_at": "2026-01-31T..."}

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

---

**See also:**
- `.claude/development/version-management.md` - Version sync strategy
- `.claude/development/python-314.md` - Python 3.14 requirements
- `.claude/architecture/desktop-app.md` - fi-monitor architecture
