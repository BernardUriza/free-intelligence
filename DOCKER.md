# Docker Deployment Guide

## Quick Start

```bash
# Start everything (recommended)
make dev-all

# Or manually:
make docker-up      # Start Docker stack
cd apps/aurity && PORT=9000 pnpm dev  # Start Frontend
```

## Services

| Service | Port | URL | Location |
|---------|------|-----|----------|
| Backend API | 7001 | http://localhost:7001 | Docker |
| API Docs | 7001 | http://localhost:7001/docs | Docker |
| Frontend AURITY | 9000 | http://localhost:9000 | Host (hot-reload) |
| Flower (Celery UI) | 5555 | http://localhost:5555 | Docker |
| Redis | 6379 | localhost:6379 | Docker |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network (fi-network)           │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  Redis   │  │ Backend  │  │  Celery  │  │ Flower  │ │
│  │  :6379   │◄─┤  API     │◄─┤  Worker  │◄─┤  :5555  │ │
│  └──────────┘  │  :7001   │  │  (x2)    │  └─────────┘ │
│                └──────────┘  └──────────┘               │
│                     ▲                                    │
└─────────────────────┼────────────────────────────────────┘
                      │
                ┌─────┴──────┐
                │  Frontend  │
                │  (Host)    │
                │  :9000     │
                └────────────┘
```

## Docker Commands

```bash
# Start services
make docker-up          # Start Docker stack
make dev-all            # Start everything (Docker + Frontend)

# Stop services
make docker-down        # Stop Docker stack
Ctrl+C in dev-all       # Stop everything

# Logs
make docker-logs        # All Docker logs
make docker-logs-backend   # Backend API only
make docker-logs-worker    # Celery Worker only
docker logs -f fi-redis    # Redis logs

# Status
make docker-ps          # Show running containers
docker compose -f docker/docker-compose.full.yml ps

# Rebuild
make docker-rebuild     # Rebuild images and restart
```

## Volumes

Shared between Host and Docker:

```
../backend  → /app/backend   (code, hot-reload)
../packages → /app/packages  (shared libs)
../storage  → /app/storage   (HDF5 corpus, audio files)
../logs     → /app/logs      (application logs)
../data     → /app/data      (buffer files)
```

## Environment Variables

Set in `docker/docker-compose.full.yml`:

- `REDIS_HOST=redis` (Docker network name)
- `AURITY_CORPUS_H5=/app/storage/corpus.h5`
- `AURITY_AUDIO_ROOT=/app/storage/audio`
- `WHISPER_MODEL_SIZE=small`
- `HDF5_USE_FILE_LOCKING=FALSE`

## Troubleshooting

### Backend not responding
```bash
docker logs fi-backend | tail -50
docker restart fi-backend
```

### Worker not processing tasks
```bash
docker logs fi-celery-worker | grep "CHUNK_\|WHISPER"
curl http://localhost:5555  # Check Flower UI
```

### Redis connection issues
```bash
docker exec -it fi-redis redis-cli ping  # Should return "PONG"
docker restart fi-redis
```

### Port conflicts
```bash
# Check what's using the ports
lsof -ti:7001,9000,5555,6379
# Kill conflicting processes
lsof -ti:7001 | xargs kill -9
```

### Rebuild from scratch
```bash
docker compose -f docker/docker-compose.full.yml down -v  # Remove volumes
docker compose -f docker/docker-compose.full.yml up -d --build
```

## Production Deployment

For production, uncomment the Frontend service in `docker/docker-compose.full.yml`:

```yaml
frontend:
  build:
    context: ..
    dockerfile: apps/aurity/Dockerfile
  ports:
    - "9000:3000"
  environment:
    - NEXT_PUBLIC_API_URL=http://backend:7001
```

Then:

```bash
docker compose -f docker/docker-compose.full.yml up -d --build
```

## Health Checks

All services have health checks:

```bash
# Check health status
docker ps --format "table {{.Names}}\t{{.Status}}"

# Backend health
curl http://localhost:7001/health

# Redis health
docker exec fi-redis redis-cli ping

# Celery health
docker exec fi-celery-worker celery -A backend.workers.celery_app inspect ping
```

## Performance Tuning

### Scale Celery Workers

Edit `docker/docker-compose.full.yml`:

```yaml
celery_worker:
  command: ... --concurrency=4 ...  # Increase from 2 to 4
```

Or deploy multiple worker containers:

```bash
docker compose -f docker/docker-compose.full.yml up -d --scale celery_worker=3
```

### Whisper Model Size

Change in `docker/docker-compose.full.yml`:

```yaml
environment:
  - WHISPER_MODEL_SIZE=medium  # Options: tiny, small, medium, large
```

Larger models = better accuracy, slower processing.

---

**Created:** 2025-11-10
**Stack:** FastAPI + Next.js + Redis + Celery + faster-whisper
**Version:** 1.0.0
