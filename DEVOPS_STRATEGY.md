# Free Intelligence - DevOps Strategy

**Version:** 1.0
**Last Updated:** 2025-10-30
**Owner:** Bernard Uriza Orozco

---

## 📐 Architecture Overview

Free Intelligence is a **Python (FastAPI) + Next.js monorepo** with the following services:

```
┌──────────────────────────────────────────────────────────┐
│ Frontend (Next.js)                                        │
│  • Port: 9000                                             │
│  • Framework: Next.js 14 (App Router)                     │
│  • Package Manager: pnpm (workspaces)                     │
│  • Build Tool: Turborepo                                  │
└──────────────────────────────────────────────────────────┘
                           ↕
┌──────────────────────────────────────────────────────────┐
│ Backend API (FastAPI)                                     │
│  • Port: 7001                                             │
│  • Framework: FastAPI (Python 3.11+)                      │
│  • Server: Uvicorn (ASGI)                                 │
│  • Storage: HDF5 (append-only corpus)                     │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Development Modes

### **Quick Start (Recommended)**

```bash
# One-command startup (all services in single terminal)
make dev-all
```

This starts:
- ✅ Backend API on http://localhost:7001
- ✅ Frontend on http://localhost:9000
- ✅ Auto-reload on file changes
- ✅ Unified log output
- ✅ Graceful shutdown with Ctrl+C

### **Manual Startup (Advanced)**

```bash
# Terminal 1: Backend
make run          # Port 7001

# Terminal 2: Frontend
pnpm dev          # Port 9000
```

### **Individual Services**

```bash
# Backend only
python3 -m uvicorn backend.fi_consult_service:app --reload --port 7001

# Frontend only
cd apps/aurity && pnpm dev
```

---

## 🏗️ Production Deployment

### **Strategy: PM2 Process Manager (No Docker)**

**Rationale:**
- ✅ **Simplicity:** No container overhead on NAS
- ✅ **Resource efficiency:** Direct process management
- ✅ **Auto-restart:** Built-in crash recovery
- ✅ **Monitoring:** Process stats and logs
- ✅ **Zero-downtime:** Hot reload support

### **NAS Deployment (Synology/QNAP/TrueNAS)**

#### **1. One-Command Setup**

```bash
./scripts/nas-setup.sh
```

This performs:
1. Prerequisites check (Node 18+, Python 3.11+, pnpm)
2. Dependency installation (Node + Python)
3. Production build (Turborepo)
4. Corpus initialization
5. Environment configuration

#### **2. Start Services with PM2**

```bash
# Install PM2 globally (one-time)
npm install -g pm2

# Start all services
pm2 start ecosystem.config.js

# Save configuration for auto-start on reboot
pm2 save
pm2 startup

# Monitor services
pm2 status
pm2 logs
pm2 monit
```

#### **3. Service Management**

```bash
# Restart a service
pm2 restart fi-backend-api

# Stop/start services
pm2 stop all
pm2 start all

# View logs
pm2 logs fi-backend-api --lines 100
pm2 logs fi-frontend --lines 100

# Reload without downtime
pm2 reload ecosystem.config.js
```

---

## 📦 PM2 Configuration (`ecosystem.config.js`)

```javascript
module.exports = {
  apps: [
    {
      name: 'fi-backend-api',
      script: 'uvicorn',
      args: 'backend.fi_consult_service:app --host 0.0.0.0 --port 7001 --workers 2',
      interpreter: 'python3',
      instances: 1,
      exec_mode: 'fork',
      max_memory_restart: '1G',
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log'
    },
    {
      name: 'fi-frontend',
      script: 'pnpm',
      args: 'start',
      cwd: './apps/aurity',
      env: {
        NODE_ENV: 'production',
        PORT: '9000'
      },
      max_memory_restart: '1G'
    }
  ]
};
```

**Key Features:**
- **Memory limits:** Auto-restart if process exceeds 1GB
- **Log rotation:** Separate error/output logs
- **Graceful shutdown:** SIGTERM handling
- **Auto-recovery:** Restart on crash

---

## 🔧 Turborepo Optimization

### **`.turborc` (NAS-optimized)**

```json
{
  "telemetry": false,
  "daemon": false,
  "cache": {
    "type": "filesystem",
    "dir": ".turbo/cache"
  }
}
```

### **`.npmrc` (pnpm hard links)**

```ini
# Hard links for 50-70% disk space savings
node-linker=hoisted
shamefully-hoist=true

# Centralized cache
store-dir=~/.pnpm-store
cache-dir=~/.pnpm-cache

# Network optimization
network-timeout=60000
fetch-retries=3
```

**Savings:**
- ~50-70% disk space vs npm
- Faster installs (hard links)
- Shared dependencies across workspaces

---

## 🌐 Networking Configuration

### **Development (LAN Access)**

```bash
# .env.local
NEXT_PUBLIC_API_BASE=http://192.168.1.100:7001
```

### **Production (NAS)**

```bash
# Access from LAN
Frontend: http://nas-ip:9000
Backend:  http://nas-ip:7001/docs
```

### **Port Mapping**

| Service         | Dev Port | Prod Port | Protocol |
|-----------------|----------|-----------|----------|
| Frontend        | 9000     | 9000      | HTTP     |
| Backend API     | 7001     | 7001      | HTTP     |
| Timeline API    | 9002     | 9002      | HTTP (optional) |

---

## 📊 Monitoring & Health Checks

### **Service Health**

```bash
# Backend health
curl http://localhost:7001/health

# Frontend health
curl http://localhost:9000/api/health
```

### **PM2 Monitoring**

```bash
# Dashboard
pm2 monit

# CPU/Memory stats
pm2 status

# Logs (real-time)
pm2 logs --lines 50
```

### **Log Locations**

```
logs/
├── backend-dev.log       # Development backend
├── frontend-dev.log      # Development frontend
├── backend-error.log     # Production backend errors
├── backend-out.log       # Production backend output
├── frontend-error.log    # Production frontend errors
└── frontend-out.log      # Production frontend output
```

---

## 🔒 Security & Data Sovereignty

### **Principles**

1. **LAN-only runtime:** No internet dependencies after install
2. **No PHI in cloud:** All data stays on NAS
3. **Append-only storage:** HDF5 corpus (no mutations)
4. **Egress control:** Policy-enforced API allowlist

### **Environment Variables (Secrets)**

```bash
# NEVER commit these
ANTHROPIC_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434

# LAN-only (safe to commit)
NEXT_PUBLIC_API_BASE=http://192.168.1.100:7001
```

---

## 📈 Scaling Strategy

### **Vertical Scaling (NAS)**

```javascript
// ecosystem.config.js
{
  name: 'fi-backend-api',
  args: '--workers 4',  // Increase workers
  max_memory_restart: '2G'  // More memory
}
```

### **Horizontal Scaling (Future)**

```javascript
{
  name: 'fi-backend-api',
  instances: 2,  // Run 2 instances
  exec_mode: 'cluster'  // Load balancing
}
```

---

## 🧪 Testing Strategy

### **Pre-Deployment Validation**

```bash
# Run all tests
make test

# Type checking
pnpm type-check

# Build validation
pnpm build

# Integration smoke test
./tests/smoke_test_transcribe.sh
```

### **Post-Deployment Validation**

```bash
# Health checks
curl http://nas-ip:7001/health
curl http://nas-ip:9000/

# Service status
pm2 status

# Log inspection
pm2 logs --lines 100 --nostream
```

---

## 🚨 Troubleshooting

### **Services won't start**

```bash
# Check ports
lsof -ti:7001  # Backend
lsof -ti:9000  # Frontend

# Kill conflicting processes
lsof -ti:7001 | xargs kill -9
```

### **PM2 process crashed**

```bash
# View error logs
pm2 logs fi-backend-api --err --lines 50

# Restart with verbose logging
pm2 restart fi-backend-api --log-type json
```

### **Frontend build fails**

```bash
# Clear cache
pnpm clean
rm -rf .next .turbo

# Rebuild
pnpm install
pnpm build
```

---

## 📚 Best Practices (DevOps Expert Level)

### **1. Infrastructure as Code**

✅ **Do:**
- Version control `ecosystem.config.js`
- Document port mappings
- Use environment variables for config

❌ **Don't:**
- Hard-code IPs in source code
- Commit `.env.local` files
- Mix dev/prod configurations

### **2. Continuous Integration**

```yaml
# Future: .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: pnpm install
      - run: pnpm type-check
      - run: pnpm test
      - run: make test  # Python tests
```

### **3. Deployment Automation**

```bash
# Future: scripts/deploy-nas.sh
#!/bin/bash
git pull origin main
pnpm install:all
pnpm build
pm2 reload ecosystem.config.js
pm2 save
```

### **4. Monitoring & Alerting**

```bash
# PM2 monitoring (optional)
pm2 install pm2-logrotate  # Log rotation
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

### **5. Backup Strategy**

```bash
# Automated backups (cron)
0 2 * * * /path/to/scripts/backup-corpus.sh
```

---

## 🎯 Recommended Workflow

### **Development Cycle**

```mermaid
graph LR
    A[make dev-all] --> B[Code Changes]
    B --> C[Auto-reload]
    C --> D[Test Locally]
    D --> E[Commit]
    E --> F[Push]
```

### **Deployment Cycle**

```mermaid
graph LR
    A[Pull Latest] --> B[pnpm install:all]
    B --> C[pnpm build]
    C --> D[pm2 reload]
    D --> E[Health Check]
    E --> F[Monitor Logs]
```

---

## 📖 References

- **Turborepo:** https://turbo.build/repo/docs
- **PM2 Documentation:** https://pm2.keymetrics.io/docs
- **FastAPI Deployment:** https://fastapi.tiangolo.com/deployment/
- **Next.js Production:** https://nextjs.org/docs/deployment

---

## 🤝 Support

**Issues:** https://github.com/BernardUriza/free-intelligence/issues
**Trello Board:** https://trello.com/b/YOUR_BOARD_ID
**Card:** FI-INFRA-STR-014

---

**Philosophy:** *Simplicidad operativa con máxima confiabilidad*
**Status:** ✅ Production-ready for NAS deployment
