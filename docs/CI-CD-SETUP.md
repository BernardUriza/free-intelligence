# CI/CD Setup - GitHub Actions

## Overview

Automatic deployment to Digital Ocean production when pushing to `prod` branch.

**Live URL**: https://fi-aurity.duckdns.org/
**Backend API**: https://fi-aurity.duckdns.org/api/

---

## Quick Setup

### 1. Add SSH Key to GitHub Secrets

```bash
# Copy your SSH private key
cat ~/.ssh/id_ed25519_do | pbcopy

# Then add to GitHub:
# https://github.com/BernardUriza/free-intelligence/settings/secrets/actions
# Secret name: DO_SSH_PRIVATE_KEY
# Secret value: <paste the key>
```

### 2. Verify GitHub Secret

```bash
# Check that the secret is configured
gh secret list
```

### 3. Deploy to Production

```bash
# Option 1: Push to prod branch
git checkout -b prod
git push origin prod

# Option 2: Trigger manual deployment
gh workflow run deploy-production.yml
```

---

## Workflow Architecture

```
┌─────────────────────────────────────────────────┐
│ Push to 'prod' branch                           │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Job 1: deploy-frontend                          │
│  - Checkout code                                │
│  - Build Next.js (pnpm build)                   │
│  - rsync to /opt/free-intelligence/apps/aurity/ │
│  - Reload Nginx                                 │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Job 2: deploy-backend                           │
│  - Sync backend/ code                           │
│  - Rebuild Docker image                         │
│  - Recreate container with --env-file           │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Job 3: verify-deployment                        │
│  - curl https://fi-aurity.duckdns.org/health    │
│  - curl https://...duckdns.org/api/.../sessions │
└─────────────────────────────────────────────────┘
```

---

## Environment Variables

### Production (.env on Digital Ocean)

**Location**: `/opt/free-intelligence/.env`

**Required variables**:
```bash
DEEPGRAM_API_KEY=...
AZURE_OPENAI_KEY=...
AZURE_OPENAI_ENDPOINT=...
DATABASE_URL=...
PORT=7001
NODE_ENV=production
ALLOWED_ORIGINS=http://localhost:9000,https://fi-aurity.duckdns.org
```

**⚠️ Important**: `.env` file is NOT synced by CI/CD (excluded in rsync).
Manual changes required via SSH.

---

## Deployment Commands

### Full Deployment (Local)
```bash
# Build frontend locally and deploy
cd apps/aurity
pnpm build
python3 scripts/deploy-scp.py

# Deploy backend
python3 scripts/deploy-backend-cors-fix.py
```

### Manual Deployment (SSH)
```bash
# Connect to droplet
ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65

# Rebuild backend
cd /opt/free-intelligence
docker build -f Dockerfile.optimized -t fi-backend:latest .
docker stop fi-backend && docker rm fi-backend
docker run -d \
  --name fi-backend \
  --env-file /opt/free-intelligence/.env \
  -p 7001:7001 \
  -v /opt/free-intelligence/storage:/app/storage \
  fi-backend:latest

# Check logs
docker logs fi-backend --tail 50

# Reload frontend
nginx -t && systemctl reload nginx
```

---

## Troubleshooting

### Build Fails
```bash
# Check GitHub Actions logs
gh run list --workflow=deploy-production.yml
gh run view <run-id> --log
```

### Backend Container Won't Start
```bash
# SSH into droplet
ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65

# Check Docker logs
docker logs fi-backend --tail 100

# Common issues:
# 1. Missing .env variables
docker exec fi-backend env | grep -E 'DEEPGRAM|AZURE'

# 2. HDF5 file permissions
ls -la /opt/free-intelligence/storage/corpus.h5
docker exec fi-backend ls -la /app/storage/corpus.h5

# 3. Port already in use
lsof -i :7001
```

### Health Check Fails
```bash
# Test endpoints manually
curl https://fi-aurity.duckdns.org/health
curl https://fi-aurity.duckdns.org/api/workflows/aurity/sessions

# Check Nginx configuration
ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65 "nginx -t"
```

---

## Git Branching Strategy

```
main (development)
  ↓
  ↓ (feature branches merge here)
  ↓
prod (production)  ← Triggers deployment
```

**Workflow**:
1. Develop on `main` or feature branches
2. Test locally with `make dev-all`
3. When ready for production: `git checkout prod && git merge main`
4. Push to trigger deployment: `git push origin prod`

---

## Rollback Procedure

```bash
# Option 1: Revert git commit
git revert <commit-hash>
git push origin prod  # Triggers redeployment

# Option 2: Manual rollback
ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65
cd /opt/free-intelligence
git checkout <previous-commit>
docker build -f Dockerfile.optimized -t fi-backend:latest .
docker restart fi-backend
```

---

## Monitoring

### Check Deployment Status
```bash
# View latest workflow run
gh run list --workflow=deploy-production.yml --limit 5

# Watch live deployment
gh run watch
```

### View Logs (Production)
```bash
# Backend logs
ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65 "docker logs fi-backend --tail 100 -f"

# Nginx logs
ssh -i ~/.ssh/id_ed25519_do root@104.131.175.65 "tail -f /var/log/nginx/access.log"
```

---

## Security Notes

- ✅ SSH key stored as GitHub Secret (encrypted at rest)
- ✅ `.env` file excluded from git and rsync
- ✅ HTTPS enforced via Let's Encrypt (auto-renews)
- ✅ CORS restricted to trusted origins
- ⚠️ API keys manually managed on server (not in git)

---

## Next Steps

1. **Add GitHub Secret**: `DO_SSH_PRIVATE_KEY`
2. **Create prod branch**: `git checkout -b prod && git push origin prod`
3. **Test deployment**: Push a small change to `prod`
4. **Monitor logs**: `gh run watch`

**Questions?** Check `.github/workflows/deploy-production.yml` for workflow details.
