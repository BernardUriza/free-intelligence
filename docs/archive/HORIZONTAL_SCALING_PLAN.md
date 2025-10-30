# Free Intelligence - Plan de Escalamiento Horizontal

**Created**: 2025-10-28
**Owner**: Bernard Uriza Orozco
**Status**: Draft v0.1
**Dependencies**: LATENCY_BUDGET.md, BACKPRESSURE_QUEUES_COMPARISON.md

---

## Executive Summary

Este documento define la estrategia de **escalamiento horizontal** para Free Intelligence, cubriendo:

1. **Docker Compose Scale** - Escalar workers y servicios
2. **Particionamiento** - Por cámara, sitio, tipo de consulta
3. **Infraestructura** - 10GbE network, NVMe storage
4. **Load Balancing** - Nginx, HAProxy, DNS round-robin

**Objetivo**: Escalar de **100 sesiones/día** → **1000 sesiones/día** sin degradación.

---

## Arquitectura Actual (Single-Node)

```
┌─────────────────────────────────────────────────┐
│              NAS (Single Node)                  │
│                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ FastAPI  │   │  Redis   │   │  HDF5    │  │
│  │ (1 proc) │───│ Streams  │───│ Storage  │  │
│  └──────────┘   └──────────┘   └──────────┘  │
│                                                 │
│  CPU: 4 cores | RAM: 16GB | Disk: 2TB HDD     │
└─────────────────────────────────────────────────┘

Capacity: ~100 sesiones/día (~4/hora)
```

**Bottlenecks**:
- CPU: Single FastAPI process (no paralelismo)
- Network: 1GbE (125 MB/s)
- Disk: HDD (~150 MB/s writes)

---

## Fase 1: Vertical Scaling (Same Node)

### 1.1 Docker Compose Scale (Workers)

**Objetivo**: Escalar FastAPI workers de 1 → 4 (utilizar 4 cores).

#### Actual: docker-compose.yml

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "7001:7001"
    command: uvicorn backend.fi_consult_service:app --host 0.0.0.0 --port 7001
    volumes:
      - ./storage:/app/storage
    environment:
      - REDIS_URL=redis://redis:6379

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

volumes:
  redis-data:
```

#### Propuesto: Múltiples workers + Load Balancer

```yaml
version: '3.8'
services:
  # Load Balancer (Nginx)
  nginx:
    image: nginx:alpine
    ports:
      - "7001:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api

  # FastAPI (4 replicas)
  api:
    build: .
    deploy:
      replicas: 4  # ← Scale horizontalmente
      resources:
        limits:
          cpus: '1'
          memory: 1G
    expose:
      - "8000"
    command: uvicorn backend.fi_consult_service:app --host 0.0.0.0 --port 8000 --loop uvloop
    volumes:
      - ./storage:/app/storage
    environment:
      - REDIS_URL=redis://redis:6379

  # Event Workers (2 replicas)
  worker:
    build: .
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 512M
    command: python backend/event_worker.py
    volumes:
      - ./storage:/app/storage
    environment:
      - REDIS_URL=redis://redis:6379

  # Redis Streams
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 6gb --maxmemory-policy allkeys-lru

volumes:
  redis-data:
```

#### nginx.conf (Load Balancer)

```nginx
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        least_conn;  # Load balancing strategy
        server api:8000 max_fails=3 fail_timeout=30s;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        location /health {
            access_log off;
            proxy_pass http://api_backend/health;
        }
    }
}
```

#### Start Stack

```bash
# Escalar servicios
docker-compose up --scale api=4 --scale worker=2 -d

# Verificar
docker-compose ps
# NAME                COMMAND              PORTS
# fi-nginx-1          nginx                0.0.0.0:7001->80/tcp
# fi-api-1            uvicorn ...          8000/tcp
# fi-api-2            uvicorn ...          8000/tcp
# fi-api-3            uvicorn ...          8000/tcp
# fi-api-4            uvicorn ...          8000/tcp
# fi-worker-1         python worker.py     -
# fi-worker-2         python worker.py     -
# fi-redis-1          redis-server         6379/tcp
```

### Resultados Esperados

| Config | RPS | Latency p95 | CPU Usage |
|--------|-----|-------------|-----------|
| 1 worker | 100 | 800ms | 25% |
| 4 workers + nginx | **350** | **250ms** | 90% |

**Mejora**: 3.5x throughput, 3x reducción de latencia.

---

## Fase 2: Horizontal Scaling (Multi-Node)

### 2.1 Arquitectura Multi-Node

```
                    ┌──────────────┐
                    │  HAProxy LB  │ ← DNS: fi.local
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
      ┌────▼────┐     ┌────▼────┐    ┌────▼────┐
      │ Node 1  │     │ Node 2  │    │ Node 3  │
      │ 4 API   │     │ 4 API   │    │ 4 API   │
      │ 2 Worker│     │ 2 Worker│    │ 2 Worker│
      └────┬────┘     └────┬────┘    └────┬────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                    ┌──────▼───────┐
                    │ Redis Cluster│ ← 3 nodos (master + replicas)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Shared NAS   │ ← NFS mount (HDF5 storage)
                    └──────────────┘
```

**Capacity**: ~1000 sesiones/día (~40/hora)

### 2.2 HAProxy Configuration

```haproxy
# haproxy.cfg
global
    maxconn 4096
    log stdout format raw local0

defaults
    mode http
    timeout connect 10s
    timeout client 30s
    timeout server 30s
    log global

# Frontend (entrada)
frontend fi_frontend
    bind *:80
    default_backend fi_backend

# Backend (nodes)
backend fi_backend
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200

    server node1 192.168.1.101:7001 check
    server node2 192.168.1.102:7001 check
    server node3 192.168.1.103:7001 check
```

### 2.3 Redis Cluster (3 nodos)

```yaml
# redis-cluster-compose.yml
version: '3.8'
services:
  redis-1:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --port 6379
    ports:
      - "6379:6379"

  redis-2:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --port 6380
    ports:
      - "6380:6380"

  redis-3:
    image: redis:7-alpine
    command: redis-server --cluster-enabled yes --port 6381
    ports:
      - "6381:6381"
```

### 2.4 Shared Storage (NFS)

```bash
# NAS (192.168.1.100)
sudo apt install nfs-kernel-server
sudo mkdir -p /mnt/fi-storage
sudo chown nobody:nogroup /mnt/fi-storage
echo "/mnt/fi-storage 192.168.1.0/24(rw,sync,no_subtree_check)" | sudo tee -a /etc/exports
sudo exportfs -ra

# Nodes (mount)
sudo apt install nfs-common
sudo mkdir -p /app/storage
sudo mount 192.168.1.100:/mnt/fi-storage /app/storage

# Auto-mount (add to /etc/fstab)
echo "192.168.1.100:/mnt/fi-storage /app/storage nfs defaults 0 0" | sudo tee -a /etc/fstab
```

---

## Fase 3: Particionamiento por Cámara/Sitio

### 3.1 Estrategia de Particionamiento

**Problema**: Todas las consultas van a un solo HDF5 file (contention).

**Solución**: Particionar por **sitio** o **cámara**.

```
storage/
├── site_hospital_a/
│   ├── corpus_site_a.h5       (Consultas del sitio A)
│   └── redis_stream: fi:site_a
├── site_hospital_b/
│   ├── corpus_site_b.h5       (Consultas del sitio B)
│   └── redis_stream: fi:site_b
└── site_hospital_c/
    ├── corpus_site_c.h5       (Consultas del sitio C)
    └── redis_stream: fi:site_c
```

### 3.2 Partitioning Logic (FastAPI)

```python
# backend/partitioner.py
import hashlib

def get_partition_key(consultation_id: str, site_id: str = None) -> str:
    """
    Determina partition key basado en site_id o hash de consultation_id.

    Args:
        consultation_id: UUID de consulta
        site_id: ID del sitio (opcional, priorizado)

    Returns:
        Partition key (e.g., "site_a", "partition_2")
    """
    if site_id:
        return f"site_{site_id}"

    # Hash-based partitioning (si no hay site_id)
    hash_value = int(hashlib.md5(consultation_id.encode()).hexdigest(), 16)
    partition_num = hash_value % 3  # 3 particiones
    return f"partition_{partition_num}"


# backend/fi_consult_service.py (modificado)
from backend.partitioner import get_partition_key

@app.post("/consultations/{consultation_id}/events")
async def append_event(consultation_id: str, request: dict):
    # Extraer site_id del request (si existe)
    site_id = request.get('metadata', {}).get('site_id')

    # Determinar partition
    partition_key = get_partition_key(consultation_id, site_id)

    # Push to partitioned Redis Stream
    stream_name = f"fi:events:{partition_key}"
    message_id = redis_client.xadd(stream_name, {
        'consultation_id': consultation_id,
        'event_json': json.dumps(request)
    })

    return {"status": "accepted", "partition": partition_key}, 202
```

### 3.3 Partitioned Workers

```python
# backend/event_worker.py (modificado)
import sys

def main(partition_key: str):
    """Worker dedicado a una partición."""
    stream_name = f"fi:events:{partition_key}"
    corpus_path = f"storage/{partition_key}/corpus.h5"

    worker = EventWorker(stream_name, corpus_path)
    worker.consume()

if __name__ == '__main__':
    partition_key = sys.argv[1]  # Ej: site_a
    main(partition_key)
```

### 3.4 Docker Compose (Partitioned)

```yaml
services:
  # Workers por partición
  worker-site-a:
    build: .
    command: python backend/event_worker.py site_a
    volumes:
      - ./storage/site_a:/app/storage/site_a

  worker-site-b:
    build: .
    command: python backend/event_worker.py site_b
    volumes:
      - ./storage/site_b:/app/storage/site_b

  worker-site-c:
    build: .
    command: python backend/event_worker.py site_c
    volumes:
      - ./storage/site_c:/app/storage/site_c
```

---

## Fase 4: Infraestructura de Alto Rendimiento

### 4.1 Network: 10GbE (10 Gigabit Ethernet)

**Actual**: 1GbE (125 MB/s)
**Propuesto**: 10GbE (1250 MB/s) ← **10x mejora**

**Hardware requerido**:
- **Switch**: QNAP QSW-M2108-2C (8x 10GbE + 2x 25GbE)
- **NIC**: Mellanox ConnectX-4 Lx (10GbE, PCIe)

**Beneficio**:
- Latencia de red reducida: 100µs → 10µs
- Throughput de NFS mejorado: 125 MB/s → 1250 MB/s

### 4.2 Storage: NVMe (Solid State)

**Actual**: HDD (150 MB/s writes, 10ms latency)
**Propuesto**: NVMe SSD (3000 MB/s writes, 0.1ms latency) ← **20x mejora**

**Hardware requerido**:
- **NAS**: Synology DS923+ (4 bay, NVMe cache)
- **Drives**: Samsung 980 PRO (1TB NVMe, 3500 MB/s read)

**Benchmarks esperados**:

| Operación | HDD | SSD | NVMe |
|-----------|-----|-----|------|
| HDF5 append (1KB) | 10ms | 2ms | **0.5ms** |
| HDF5 read (1KB) | 8ms | 1ms | **0.2ms** |
| Sequential write | 150 MB/s | 500 MB/s | **3000 MB/s** |
| Random IOPS | 100 | 50K | **500K** |

**Impacto en latency budget**:
- PERSIST stage: 1700ms (HDD) → **340ms (NVMe)** ← **5x mejora**

### 4.3 Topology: 10GbE + NVMe

```
┌────────────────────────────────────────────────────────────┐
│                       10GbE Switch                         │
│              QNAP QSW-M2108-2C (8x 10GbE)                 │
└──┬────────┬────────┬────────┬────────┬────────────────────┘
   │        │        │        │        │
   │ 10G    │ 10G    │ 10G    │ 10G    │ 10G
   │        │        │        │        │
┌──▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼────────────┐
│Node 1│ │Node 2│ │Node 3│ │HA LB │ │ NAS (NVMe)    │
│      │ │      │ │      │ │Proxy │ │ DS923+ 4x1TB  │
└──────┘ └──────┘ └──────┘ └──────┘ └───────────────┘
```

**Total Cost**:
- Switch 10GbE: ~$500 USD (QNAP QSW-M2108-2C)
- NAS NVMe: ~$600 USD (Synology DS923+)
- 4x NVMe 1TB: ~$400 USD (Samsung 980 PRO)
- 3x NICs 10GbE: ~$300 USD (Mellanox ConnectX-4 Lx)
- **Total**: ~$1800 USD

---

## Capacity Planning: Sesiones/Día

### Cálculo de Capacidad

**Fórmula**:
```
Max sesiones/día = (Workers × RPS × 3600s × 24h) / Avg_requests_per_session
```

**Asumiendo**:
- Workers: 12 (3 nodos × 4 workers)
- RPS por worker: 100 req/s
- Avg requests por sesión: 20 (10 mensajes, 10 eventos)

```
Max sesiones/día = (12 × 100 × 86400) / 20
                 = 103,680,000 / 20
                 = 5,184,000 sesiones/día
```

**Conclusión**: Con infraestructura propuesta, capacidad teórica es **5M sesiones/día**.

**Límite realista**: ~**10,000 sesiones/día** (factor de seguridad 0.2%).

---

## Roadmap de Implementación

### Fase 1: Vertical Scaling (1 semana)

**Objetivo**: 100 → 300 sesiones/día

- [ ] Day 1: Docker Compose con 4 workers + nginx
- [ ] Day 2: Redis Streams integration (EventQueue + EventWorker)
- [ ] Day 3: Benchmarks (RPS, latency p95/p99)
- [ ] Day 4-5: Optimizaciones (uvloop, orjson, lzf compression)
- [ ] Day 6: Load testing (300 sesiones/día simuladas)
- [ ] Day 7: Monitoring (Prometheus + Grafana)

**Cost**: $0 (mismo hardware)

---

### Fase 2: Horizontal Scaling (2 semanas)

**Objetivo**: 300 → 1000 sesiones/día

- [ ] Week 1: Multi-node setup (3 nodos con HAProxy)
- [ ] Week 2: Redis Cluster (3 nodos)
- [ ] Week 3: Partitioning (por sitio/cámara)
- [ ] Week 4: NFS shared storage + benchmarks

**Cost**: ~$3000 USD (3 nodos × $1000/nodo)

---

### Fase 3: High-Performance Infra (1 mes)

**Objetivo**: 1000 → 10,000 sesiones/día

- [ ] Week 1: Adquisición de hardware (Switch 10GbE, NAS NVMe)
- [ ] Week 2: Instalación + cableado + configuración
- [ ] Week 3: Migration de HDD → NVMe (con downtime)
- [ ] Week 4: Benchmarks finales + validación

**Cost**: ~$1800 USD (hardware)

---

## Success Metrics

| Métrica | Baseline | Fase 1 | Fase 2 | Fase 3 |
|---------|----------|--------|--------|--------|
| **Max sesiones/día** | 100 | 300 | 1,000 | 10,000 |
| **RPS (total)** | 100 | 350 | 1,200 | 12,000 |
| **Latency p95** | 2000ms | 500ms | 250ms | **50ms** |
| **CPU usage** | 25% | 90% | 80% | 70% |
| **Network bandwidth** | 10 MB/s | 40 MB/s | 150 MB/s | 1500 MB/s |
| **Storage throughput** | 20 MB/s | 80 MB/s | 200 MB/s | **3000 MB/s** |

---

## Referencias

- **Docker Compose Scale**: https://docs.docker.com/compose/compose-file/deploy/
- **HAProxy**: https://www.haproxy.org/
- **Redis Cluster**: https://redis.io/docs/management/scaling/
- **10GbE Networking**: https://www.qnap.com/en/product/qsw-m2108-2c
- **NVMe Performance**: https://www.samsung.com/us/computing/memory-storage/solid-state-drives/

---

**Version History**:
- v0.1 (2025-10-28): Plan completo de escalamiento horizontal
