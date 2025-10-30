# Free Intelligence - Port Allocation

**Serie FI dedicada: 9000-9099**

## Puertos Asignados

| Puerto | Servicio | Descripción | Estado |
|--------|----------|-------------|--------|
| **9000** | Aurity Frontend | Next.js 14 + React 18 (Dashboard) | ✅ Asignado |
| **9001** | FastAPI Backend | FI Core API (corpus operations) | ✅ Asignado |
| **9002** | Gateway/Proxy | Nginx/Traefik (futuro) | 🔄 Reservado |
| **9003** | WebSocket Server | Real-time updates (futuro) | 🔄 Reservado |
| **9004** | Metrics | Prometheus/Grafana endpoint | 🔄 Reservado |
| **9005** | Admin Dashboard | Admin UI (futuro) | 🔄 Reservado |
| **9006-9099** | Expansión | Microservicios futuros | 🔄 Reservado |

## Comandos

```bash
# Frontend (Aurity)
pnpm dev                    # → http://localhost:9000

# Backend (FastAPI)
make run                    # → http://localhost:9001

# Frontend solo
pnpm frontend:dev           # → http://localhost:9000

# Backend solo
pnpm backend:dev            # → http://localhost:9001
```

## Razón de la Serie 9000-9099

- ✅ **No colisiona** con puertos comunes (3000, 5000, 8000)
- ✅ **Serie memorizable** y coherente
- ✅ **100 puertos** disponibles para expansión
- ✅ **Rango alto** (9xxx) raramente usado por otros proyectos
- ✅ **Fácil recordar**: "FI = 9000+"

## Configuración por Servicio

### Aurity (Frontend)
- `apps/aurity/package.json`: `"dev": "next dev -p 9000"`
- Env var: `PORT=9000`

### FastAPI (Backend)
- `backend/main.py`: `uvicorn.run(app, host="0.0.0.0", port=9001)`
- Env var: `FI_API_PORT=9001`

## Docker

```yaml
# docker-compose.yml
services:
  aurity:
    ports:
      - "9000:9000"

  fi-api:
    ports:
      - "9001:9001"
```

## Firewall / NAT

Si usas NAS o deployment en LAN:
```bash
# Abrir puertos en macOS firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /path/to/app
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /path/to/app
```

---

**Última actualización**: 2025-10-28
**Versión**: 0.3.0
