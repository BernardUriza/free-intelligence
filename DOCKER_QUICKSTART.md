# Docker Quick Start 🐳

## One Command to Rule Them All

```bash
make dev-all
```

That's it! This starts:
- ✅ Redis (Docker)
- ✅ Backend API (Docker, port 7001)
- ✅ Celery Worker x2 (Docker, queues: asr + celery)
- ✅ Flower monitoring (Docker, port 5555)
- ✅ Frontend AURITY (Host, port 9000, hot-reload)

Press **Ctrl+C** to stop everything (Docker + Frontend).

---

## URLs

| Service | URL |
|---------|-----|
| Backend API | http://localhost:7001 |
| API Docs | http://localhost:7001/docs |
| Frontend | http://localhost:9000 |
| Flower (Task Monitor) | http://localhost:5555 |

---

## Useful Commands

```bash
# Start/Stop
make docker-up          # Start Docker only
make docker-down        # Stop Docker only

# Logs
make docker-logs        # All Docker services
make docker-logs-backend   # Backend API only
make docker-logs-worker    # Celery Worker only

# Status
make docker-ps          # Show running containers

# Rebuild
make docker-rebuild     # Rebuild images
```

---

## Architecture

```
Host:
  └─ Frontend (Next.js) :9000

Docker (fi-network):
  ├─ Redis :6379
  ├─ Backend API (FastAPI) :7001
  ├─ Celery Worker x2 (faster-whisper)
  └─ Flower :5555
```

---

## Why This Setup?

1. **Backend in Docker** → Consistent environment, no dependency issues
2. **Frontend on Host** → Hot-reload works perfectly
3. **Shared volumes** → Code changes reflect immediately
4. **Path bug fixed** → Backend and Worker share `/app/storage`

---

**Full documentation:** See [DOCKER.md](./DOCKER.md)
