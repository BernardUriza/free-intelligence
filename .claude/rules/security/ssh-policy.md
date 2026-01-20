# Production SSH Policy (ENFORCED)

**Machine-enforced via:**
- `scripts/hooks/pre-receive-prod` (blocks direct git push)
- `scripts/hooks/prod-integrity-check.sh` (cron every 5min)
- `.github/workflows/deploy-production.yml` (pre-deploy integrity check)

## Allowed on Production Server

✅ **READ-ONLY Operations:**
- SSH for audit: `tail logs`, `check status`
- Viewing files: `cat`, `less`, `head`, `tail`
- Process inspection: `ps`, `top`, `htop`, `lsof`
- Log analysis: `journalctl`, `tail -f /tmp/backend.log`
- Health checks: `curl localhost:7001/api/health`

## Forbidden on Production Server

❌ **File Modification:**
- `vim`, `nano`, `emacs`, or ANY text editor
- `echo "..." > file` (file modification)
- `git commit`, `git push` (blocked by pre-receive hook)
- Adding `print()` or debug statements
- "Quick fixes" of any kind

❌ **Package/Service Management:**
- `pip install` (use CI/CD)
- `systemctl stop/restart` (use CI/CD rollback)

❌ **Manual Deployment:**
- `rsync ./out/ root@servidor:/path/`
- `scp archivo.dmg root@servidor:/path/`
- `ssh root@servidor "mkdir && cp..."`

## Correct Deployment Process

✅ **ALWAYS use CI/CD:**
```bash
git push origin dev      # → PR to main → CI/CD auto-deploy
make ci-deploy           # For immediate deployment
```

✅ **For hotfixes:**
```bash
git checkout -b hotfix/issue-description
# Fix issue
git push origin hotfix/issue-description
gh pr create --base main
# Merge → Auto-deploy
```

## Violation Response

1. Integrity monitor detects change within 5 minutes
2. Alert sent to Slack + logged to `/var/log/aurity-security.log`
3. Next CI/CD deploy auto-resets production to clean state
4. Repeat violations = revoked SSH access

## Claude Code Directive

Claude must NEVER suggest:
- "Just SSH in and edit..."
- "Quick fix on prod..."
- "Temporarily add a print statement..."
- Any command that modifies production files directly

Instead, Claude must ALWAYS suggest:
- "Push to GitHub, CI/CD will deploy"
- "Use make ci-deploy for immediate deployment"
- "Create a hotfix branch and merge to prod"
