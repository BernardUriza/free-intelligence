# Free Intelligence - NAS Deployment Guide

Optimized for Synology/QNAP/TrueNAS deployment with minimal resource usage.

---

## Prerequisites

### Hardware Requirements (Minimum)
- CPU: 2 cores (4 recommended)
- RAM: 4GB (8GB recommended)
- Storage: 20GB available (SSD preferred for node_modules)
- Network: 100Mbps (LAN-only, no internet required for runtime)

### Software Requirements
- Node.js 18+ (via NAS package manager or nvm)
- Python 3.11+ (for backend)
- Docker (optional, for containerized deployment)

---

## Installation Steps

### 1. Clone Repository to NAS
```bash
# SSH into your NAS
ssh admin@nas-ip

# Navigate to shared folder
cd /volume1/docker/free-intelligence  # Synology
# or
cd /share/Container/free-intelligence  # QNAP

# Clone repo
git clone <repo-url> .
```

### 2. Install Node.js Dependencies (pnpm)
```bash
# Install pnpm globally (if not installed)
npm install -g pnpm@8.15.0

# Install all dependencies with frozen lockfile
pnpm install:all

# This uses hard links - very efficient on NAS storage
```

### 3. Install Python Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
# Copy environment template
cp .env.example .env.local

# Edit with NAS-specific paths
nano .env.local
```

**Example `.env.local` for NAS:**
```bash
# Storage paths (adjust for your NAS)
CORPUS_PATH=/volume1/free-intelligence/storage/corpus.h5
BACKUP_PATH=/volume1/free-intelligence/backups

# API endpoints (LAN-only)
NEXT_PUBLIC_API_URL=http://192.168.1.100:9001
TIMELINE_API_URL=http://192.168.1.100:9002

# Port configuration
PORT=9000
API_PORT=9001
TIMELINE_PORT=9002

# Node environment
NODE_ENV=production
```

### 5. Build Production Assets
```bash
# Build all apps with Turbo (cached builds)
pnpm build

# This creates optimized production bundles
```

---

## Running Services

### Option A: Manual Start (Development/Testing)
```bash
# Terminal 1: Backend API
make run

# Terminal 2: Timeline API
make run-timeline

# Terminal 3: Frontend
cd apps/aurity && pnpm start
```

### Option B: Process Manager (pm2 - Recommended)
```bash
# Install pm2
npm install -g pm2

# Start all services with ecosystem file
pm2 start ecosystem.config.js

# Save for auto-restart
pm2 save
pm2 startup
```

**ecosystem.config.js example:**
```javascript
module.exports = {
  apps: [
    {
      name: 'fi-backend',
      script: 'make',
      args: 'run',
      cwd: '/volume1/docker/free-intelligence',
      env: { PORT: 9001 }
    },
    {
      name: 'fi-timeline',
      script: 'make',
      args: 'run-timeline',
      cwd: '/volume1/docker/free-intelligence',
      env: { PORT: 9002 }
    },
    {
      name: 'fi-frontend',
      script: 'pnpm',
      args: 'start',
      cwd: '/volume1/docker/free-intelligence/apps/aurity',
      env: { PORT: 9000 }
    }
  ]
};
```

### Option C: Docker Compose (Isolated)
```bash
# Build and start containers
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## Turborepo Configuration for NAS

### Cache Strategy (Local-Only)
- **Remote cache**: DISABLED (no cloud dependencies)
- **Local cache**: Enabled at `.turbo/cache/`
- **Daemon**: DISABLED (reduces memory usage)

### Build Optimizations
```bash
# Parallel builds (use available cores)
pnpm build --concurrency=2

# Incremental builds (only changed packages)
pnpm build --filter=...@latest

# Force rebuild (ignore cache)
pnpm build --force
```

### pnpm Configuration (.npmrc)
- **Hard links**: Enabled (saves 50-70% disk space)
- **Hoist**: Enabled (shared dependencies)
- **Store**: Centralized at `~/.pnpm-store`

---

## Monitoring & Maintenance

### Check Service Status
```bash
# pm2 dashboard
pm2 monit

# Check logs
pm2 logs fi-backend
pm2 logs fi-frontend

# Resource usage
pm2 status
```

### Database Maintenance
```bash
# Backup corpus (automatic via policy)
python3 backend/maintenance/backup_corpus.py

# Verify integrity
python3 scripts/verify_corpus.py

# Check disk usage
du -sh storage/corpus.h5
```

### Clean Cache/Temp Files
```bash
# Clean turbo cache
pnpm clean

# Clean node_modules cache
rm -rf node_modules/.cache

# Clean pnpm store (careful - affects all projects)
pnpm store prune
```

---

## Performance Tuning for NAS

### 1. Reduce Memory Footprint
```bash
# Limit Node.js heap size
export NODE_OPTIONS="--max-old-space-size=2048"

# Use production mode
export NODE_ENV=production
```

### 2. Optimize Storage I/O
- Store node_modules on SSD volume (if available)
- Use `pnpm` instead of `npm` (hard links = less I/O)
- Enable NAS cache for shared folders

### 3. Network Configuration
- Use LAN-only access (no internet required)
- Bind to NAS IP (not 0.0.0.0)
- Firewall: Block external ports (9000-9002)

### 4. Scheduled Tasks (NAS Task Scheduler)
```bash
# Daily backup (2 AM)
0 2 * * * /volume1/docker/free-intelligence/scripts/backup_corpus.sh

# Weekly cleanup (Sunday 3 AM)
0 3 * * 0 /volume1/docker/free-intelligence/scripts/cleanup_logs.sh

# Monthly audit (1st of month)
0 0 1 * * python3 /volume1/docker/free-intelligence/backend/maintenance/audit_retention.py
```

---

## Troubleshooting

### Service won't start
```bash
# Check ports in use
netstat -tulpn | grep -E '9000|9001|9002'

# Check permissions
ls -la storage/corpus.h5

# Check logs
tail -f logs/backend.log
```

### Out of memory
```bash
# Increase Node.js heap
export NODE_OPTIONS="--max-old-space-size=4096"

# Restart services
pm2 restart all
```

### Slow builds
```bash
# Check turbo cache
turbo run build --dry-run

# Verify pnpm store
pnpm store status

# Use fewer parallel jobs
pnpm build --concurrency=1
```

---

## Security Considerations

### Access Control
- Frontend: http://nas-ip:9000 (LAN-only)
- Backend API: http://nas-ip:9001 (LAN-only)
- Timeline API: http://nas-ip:9002 (LAN-only)

### Firewall Rules
```bash
# Allow LAN subnet only
iptables -A INPUT -p tcp -s 192.168.1.0/24 --dport 9000:9002 -j ACCEPT
iptables -A INPUT -p tcp --dport 9000:9002 -j DROP
```

### Data Sovereignty
- All data stored locally on NAS
- No external API calls (except LLM if configured)
- PHI never leaves NAS perimeter

---

## Backup Strategy

### Automated Backups
```bash
# Corpus backup (daily)
cp storage/corpus.h5 backups/corpus_$(date +%Y%m%d).h5

# Configuration backup
tar -czf backups/config_$(date +%Y%m%d).tar.gz config/ .env.local
```

### Restore Procedure
```bash
# Stop services
pm2 stop all

# Restore corpus
cp backups/corpus_20250129.h5 storage/corpus.h5

# Restart services
pm2 restart all
```

---

## Upgrade Procedure

### 1. Backup Everything
```bash
./scripts/backup_all.sh
```

### 2. Pull Updates
```bash
git pull origin main
```

### 3. Reinstall Dependencies
```bash
pnpm install:all
```

### 4. Rebuild
```bash
pnpm build --force
```

### 5. Restart Services
```bash
pm2 restart all
```

---

## Contact & Support

- Documentation: `/docs/`
- Issues: Internal tracking (no external dependencies)
- Architecture: See `ARCHITECTURE.md`

**Last Updated**: 2025-10-29
**Version**: 0.3.0
**Deployment Target**: NAS (Local-First)
