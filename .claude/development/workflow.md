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
3. Verify locally (`make dev`, `make test`, the real page in Chrome)
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

## 🌿 Git Workflow

`main` is the only branch, local and at rest (`dev` retired 2026-07-06). `main` on
GitHub is protected, so a change rides a remote-only ref that dies on merge:

```bash
git status --short && git branch --show-current   # must be clean-enough and on main
git add <exact paths>                              # never -A / . / -a
git diff --cached --name-status                    # read it before committing
git commit -m "feat(scope): ..."
git push origin HEAD:refs/heads/bernarduriza/<slug>
gh pr create --base main --head bernarduriza/<slug>
# PR Gate + AI Gatekeeper green -> gh pr merge --delete-branch -> CI/CD deploys
git pull --ff-only                                 # local main catches the merge
```

A local branch is never created; the `main-only-branches` gate denies it. A checkout
that is not on `main` is an alarm, not a workspace.

---

## 🖥️ Local og118

```bash
make dev          # server (apps/og118/server/run.sh, :8118) + web (next dev, :3000)
make dev-server   # only the server; make dev-web for only the web
make dev-kill     # stop whatever listens on :8118 / :3000
make test         # server pytest + og118-web vitest
```

- The server's `.venv` and its install steps: `apps/og118/server/README.md`.
- `run.sh` reads `apps/og118/server/.env.local` and picks API-key or OAuth mode.
- The web runs in `auth0` mode from `apps/og118/web/.env.local`; never flip it to
  `bearer` to verify how the app looks (`.claude/rules/local-dev-auth-mode-parity.md`).

## ✅ Verification Checklist

```bash
curl -s http://localhost:8118/health      # server up
node scripts/check-console-errors.mjs http://localhost:3000/
node scripts/screenshot-cdp.mjs http://localhost:3000/ /tmp/og118.png
```
