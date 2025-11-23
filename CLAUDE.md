# CLAUDE.md - Free Intelligence

Project context and guidelines for Claude Code sessions.

---

## Project Overview

**Free Intelligence (FI)** is a privacy-first clinical documentation platform combining:
- **Backend**: Python FastAPI + Ollama/Qwen LLM + HDF5 corpus storage
- **Frontend**: Next.js (Aurity app) with TypeScript
- **Infrastructure**: Local NAS (Synology DS923+) or DigitalOcean Droplet

### Key Principles
1. **Data Sovereignty**: All PHI stays on-premises or in private VPC
2. **Local-First**: Works offline, no mandatory cloud dependencies
3. **HIPAA Compliant**: TLS 1.3, encryption, audit logging

---

## Quick Commands

```bash
# Development
make run              # Start backend API (port 7001)
make run-timeline     # Start timeline API (port 9002)
pnpm dev              # Start frontend (port 9000)

# Testing
pytest backend/       # Run backend tests
pnpm test             # Run frontend tests

# Build
pnpm build            # Production build
docker compose up -d  # Docker deployment
```

---

## Project Structure

```
free-intelligence/
├── backend/           # FastAPI backend (Python)
│   ├── app/           # Main application
│   ├── services/      # Business logic
│   └── storage/       # HDF5 corpus handling
├── apps/
│   └── aurity/        # Next.js frontend
├── config/            # Configuration files
├── docker/            # Docker configs
├── infra/             # Infrastructure as Code
│   └── cloud-init.yaml  # DO Droplet provisioning
├── scripts/           # Deployment & utility scripts
└── docs/              # Documentation
    └── runbooks/      # Operational procedures
```

---

## Infra & Ops

### Architecture: DigitalOcean NAS

```
┌─────────────────────────────────────────────────────────────┐
│                    VPC: 10.116.0.0/20                       │
│                                                             │
│  ┌─────────────────┐     NFSv4      ┌─────────────────┐    │
│  │  fi-nas         │◄──────────────►│  fi-app         │    │
│  │  (Droplet)      │    :2049       │  (Droplet)      │    │
│  │                 │                │                 │    │
│  │  Block Storage  │                │  Backend API    │    │
│  │  /mnt/fi (100G) │                │  Frontend       │    │
│  └─────────────────┘                └─────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Why This Architecture

| Decision | Rationale |
|----------|-----------|
| **Droplet over App Platform** | Block Storage attachment, persistent state, NFS server |
| **Block Storage over Spaces** | POSIX filesystem for HDF5, lower latency |
| **NFSv4 over SMB** | Linux-native, better locking for HDF5 |
| **VPC-only access** | Zero public exposure, HIPAA isolation |
| **cloud-init provisioning** | Reproducible, version-controlled infra |

### Deployment Files

| File | Purpose |
|------|---------|
| `infra/cloud-init.yaml` | Droplet provisioning (NFS, UFW, mounts) |
| `scripts/nfs-setup.sh` | Standalone NFS server setup |
| `scripts/ufw-setup.sh` | Firewall configuration |
| `scripts/smb-setup.sh` | Optional Windows client support |
| `.env.production` | Production environment overrides |

### Runbooks

| Runbook | Location |
|---------|----------|
| DO NAS Deployment | `docs/runbooks/NAS_DEPLOYMENT_DO.md` |
| Local NAS (Synology) | `docs/archive/NAS_DEPLOYMENT.md` |

### Reversion Criteria

Roll back this infrastructure if:
1. **NFS latency > 10ms** for corpus operations
2. **HDF5 locking errors** exceed 1% of write operations
3. **Cost exceeds $50/month** without proportional benefit
4. **Recovery time > 30 min** from volume snapshot

Reversion path:
1. Detach Block Storage from Droplet
2. Restore from snapshot to local NAS
3. Update DNS/client configs to point to local NAS IP

---

## Environment Variables

Critical paths that MUST be overridden for DO deployment:

```bash
# Required overrides in .env.production
CORPUS_PATH=/mnt/fi/data/corpus.h5    # Default: ./storage/corpus.h5
STORAGE_PATH=/mnt/fi/data             # Default: ./storage
BACKUP_PATH=/mnt/fi/backups           # Default: ./backups
LOG_PATH=/mnt/fi/logs                 # Default: ./logs
```

---

## Known Risks

| Risk | Mitigation |
|------|------------|
| HDF5 file locking on NFS | Use NFSv4.1+, monitor for ESTALE errors |
| CORPUS_PATH hardcoded | Override via ENV; ~15 files reference it |
| No encryption at rest | Enable DO Volume encryption (if available) or LUKS |
| Single point of failure | Weekly snapshots, documented failover procedure |

---

## Session Conventions

### Branches
- Feature work: `claude/feature-name-SESSIONID`
- Always push to feature branch, never to main

### Commits
- Conventional commits: `feat:`, `fix:`, `docs:`, `infra:`
- Include card reference if applicable: `[FI-XXX]`

### Code Changes
- Read before edit
- Prefer Edit over Write for existing files
- No changes to `backend/` app code unless explicitly requested
- All infra changes in `infra/` or `scripts/`

---

## Contact

- Repository: Internal
- Documentation: `/docs/`
- Runbooks: `/docs/runbooks/`

**Last Updated**: 2025-11-23
