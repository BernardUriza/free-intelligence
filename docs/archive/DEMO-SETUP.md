# Free Intelligence Cold - Demo Setup Guide

**Version**: 1.0
**Target**: DELL PowerEdge R350 + Docker
**Duration**: 10 minutes setup
**Purpose**: Demo reproducible para pilotos

---

## 🎯 Overview

Este documento describe cómo configurar una demo local de **Free Intelligence Cold** usando Docker Compose. La demo incluye:

- ✅ FI Backend (FastAPI + HDF5 event store)
- ✅ AURITY Frontend (Next.js UI)
- ✅ IntakeCoach Preset (medical intake assistant)
- ✅ Ollama (local LLM, opcional)

**Hardware recomendado**:
- DELL PowerEdge R350 (Xeon E-2388G, 32GB RAM, 2TB NVMe)
- O cualquier server/laptop con Docker + 8GB RAM mínimo

---

## 🚀 Quick Start (3 comandos)

```bash
# 1. Clone repository
git clone https://github.com/BernardUriza/free-intelligence.git
cd free-intelligence

# 2. Start demo
docker-compose -f docker-compose.demo.yml up -d

# 3. Wait for services (60s) + verify
docker-compose -f docker-compose.demo.yml ps
```

**Access**:
- 🌐 AURITY Frontend: http://localhost:9000
- 🔧 FI Backend: http://localhost:7001
- 📊 FI Corpus API: http://localhost:9001
- 🧠 Ollama (LLM): http://localhost:11434

---

## 📋 Prerequisites

### Required
- Docker 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- Docker Compose 2.0+ (incluido con Docker Desktop)
- 8GB RAM mínimo
- 20GB disk space disponible

### Optional (para producción)
- NVIDIA GPU (para Ollama con aceleración)
- NVIDIA Container Toolkit ([Install Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html))

### Verificación

```bash
# Check Docker
docker --version
# Expected: Docker version 20.10.x or higher

# Check Docker Compose
docker-compose --version
# Expected: Docker Compose version 2.x.x or higher

# Check available RAM
free -h  # Linux
# O Activity Monitor en macOS

# Check disk space
df -h | grep -E "Filesystem|/$"
# Should have >20GB available
```

---

## 🛠️ Detailed Setup

### Step 1: Clone Repository

```bash
# HTTPS
git clone https://github.com/BernardUriza/free-intelligence.git
cd free-intelligence

# O SSH (si tienes acceso configurado)
git clone git@github.com:BernardUriza/free-intelligence.git
cd free-intelligence
```

### Step 2: Configure Environment (opcional)

```bash
# Copy example env file (si existe)
cp .env.example .env

# Edit .env si necesitas cambiar defaults
# - FI_OWNER_ID: Identificador del corpus (default: demo@fi-cold)
# - LOG_LEVEL: INFO, DEBUG, WARNING (default: INFO)
```

### Step 3: Build Images

```bash
# Build all images
docker-compose -f docker-compose.demo.yml build

# O build specific service
docker-compose -f docker-compose.demo.yml build fi-backend
docker-compose -f docker-compose.demo.yml build aurity-frontend
```

**Expected output**:
```
[+] Building 120.5s (25/25) FINISHED
 => [fi-backend internal] load build definition
 => [fi-backend 1/12] FROM docker.io/library/python:3.11-slim
 ...
 => [fi-backend] exporting to image
 => => naming to docker.io/library/free-intelligence:0.3.0
```

### Step 4: Start Services

```bash
# Start in detached mode
docker-compose -f docker-compose.demo.yml up -d

# O start in foreground (para ver logs en vivo)
docker-compose -f docker-compose.demo.yml up
```

**Expected output**:
```
[+] Running 4/4
 ✔ Network fi-demo-network     Created
 ✔ Container fi-ollama          Started
 ✔ Container fi-backend         Started
 ✔ Container aurity-frontend    Started
```

### Step 5: Verify Health

```bash
# Check all services
docker-compose -f docker-compose.demo.yml ps

# Expected output:
# NAME               STATUS         PORTS
# fi-backend         Up (healthy)   0.0.0.0:7001->7001/tcp
# aurity-frontend    Up (healthy)   0.0.0.0:9000->3000/tcp
# fi-ollama          Up (healthy)   0.0.0.0:11434->11434/tcp
```

```bash
# Test endpoints
curl http://localhost:7001/health
# Expected: {"status":"healthy","service":"fi-consult","version":"0.3.0"}

curl http://localhost:9000/api/health
# Expected: {"status":"ok"}

curl http://localhost:11434/
# Expected: Ollama is running
```

---

## 🧪 Testing the Demo

### Test 1: IntakeCoach (Browser)

1. **Open AURITY**:
   ```bash
   open http://localhost:9000
   ```

2. **Navigate to Intake**:
   - Click "IntakeCoach" en menú
   - O ir directamente a: http://localhost:9000/intake

3. **Start Consultation**:
   - User: "Hola, tengo dolor de pecho"
   - IntakeCoach: "Entiendo, esto es importante. ¿Cuándo comenzó el dolor?"
   - User: "Hace 2 horas, y se extiende al brazo izquierdo"
   - IntakeCoach: "¿En escala 1-10, qué tan fuerte es?"
   - User: "8 de 10"

4. **Expected Result**:
   - Sistema detecta síntoma crítico
   - Clasifica como URGENCY: CRITICAL
   - Genera nota SOAP automáticamente
   - Muestra badge rojo "CRITICAL"

### Test 2: API Direct (cURL)

```bash
# Start consultation
curl -X POST http://localhost:7001/consultations \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "Juan Pérez",
    "age": 45,
    "chief_complaint": "Dolor de pecho"
  }' | jq

# Expected response:
# {
#   "consultation_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "started",
#   "timestamp": "2025-10-28T18:00:00Z"
# }

# Get consultation
CONSULT_ID="550e8400-e29b-41d4-a716-446655440000"
curl http://localhost:7001/consultations/$CONSULT_ID | jq
```

### Test 3: Event Store Verification

```bash
# Check events in HDF5
docker exec -it fi-backend python3 -c "
from backend.fi_event_store import load_stream
events = load_stream('storage/corpus.h5')
print(f'Total events: {len(events)}')
for e in events[-5:]:
    print(f'  - {e.event_type} @ {e.timestamp}')
"

# Expected output:
# Total events: 12
#   - CONSULTATION_STARTED @ 2025-10-28T18:00:00Z
#   - MESSAGE_RECEIVED @ 2025-10-28T18:00:05Z
#   - EXTRACTION_COMPLETED @ 2025-10-28T18:00:10Z
#   - URGENCY_CLASSIFIED @ 2025-10-28T18:00:12Z
#   - SOAP_GENERATION_COMPLETED @ 2025-10-28T18:00:15Z
```

---

## 🔧 Troubleshooting

### Problem: "Port 7001 already in use"

```bash
# Find process using port
lsof -i :7001

# Kill process
kill -9 <PID>

# O change port in docker-compose.demo.yml:
# ports:
#   - "7002:7001"  # Use 7002 externally instead
```

### Problem: "Service unhealthy"

```bash
# Check logs
docker-compose -f docker-compose.demo.yml logs fi-backend

# Common issues:
# 1. Missing corpus.h5 file
docker exec -it fi-backend ls -la storage/

# 2. Python dependencies not installed
docker-compose -f docker-compose.demo.yml build --no-cache fi-backend

# 3. HDF5 library mismatch
docker exec -it fi-backend python3 -c "import h5py; print(h5py.version.info)"
```

### Problem: "AURITY frontend can't connect to backend"

```bash
# Check network
docker network inspect fi-demo-network

# Verify FI_ENDPOINT_BASE env var
docker exec -it aurity-frontend env | grep FI_ENDPOINT

# Test connectivity from frontend container
docker exec -it aurity-frontend curl http://fi-backend:7001/health
```

### Problem: "Ollama out of memory"

```bash
# Check Ollama logs
docker-compose -f docker-compose.demo.yml logs ollama

# Reduce model size (edit docker-compose.demo.yml)
# Replace model with smaller version:
# ollama pull llama2:7b  # Instead of llama2:13b

# O disable Ollama completely (comment out service)
```

---

## 🧹 Cleanup

### Stop Services

```bash
# Stop all services
docker-compose -f docker-compose.demo.yml down

# Stop + remove volumes (DELETE ALL DATA)
docker-compose -f docker-compose.demo.yml down -v
```

### Remove Images

```bash
# List images
docker images | grep -E "free-intelligence|aurity|ollama"

# Remove specific image
docker rmi free-intelligence:0.3.0

# Remove all unused images
docker image prune -a
```

### Reset Demo

```bash
# Complete reset
docker-compose -f docker-compose.demo.yml down -v
rm -rf storage/* logs/* exports/*
docker-compose -f docker-compose.demo.yml up -d --build
```

---

## 📊 Monitoring

### View Logs

```bash
# All services
docker-compose -f docker-compose.demo.yml logs -f

# Specific service
docker-compose -f docker-compose.demo.yml logs -f fi-backend

# Last 100 lines
docker-compose -f docker-compose.demo.yml logs --tail=100 fi-backend
```

### Resource Usage

```bash
# Stats (CPU, RAM, Network)
docker stats

# Detailed info
docker-compose -f docker-compose.demo.yml ps --format json | jq
```

### Access Container Shell

```bash
# FI Backend
docker exec -it fi-backend bash

# AURITY Frontend
docker exec -it aurity-frontend sh

# Ollama
docker exec -it fi-ollama bash
```

---

## 🎬 Demo Scenario Scripts

### Scenario 1: GREEN Path (Low Urgency)

```bash
# Patient: Mild headache, no red flags
curl -X POST http://localhost:7001/consultations \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "María González",
    "age": 32,
    "chief_complaint": "Dolor de cabeza leve, 1 día"
  }'

# Expected: URGENCY = LOW
```

### Scenario 2: YELLOW Path (High Urgency)

```bash
# Patient: Chest pain + comorbidities
curl -X POST http://localhost:7001/consultations \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "Carlos Rodríguez",
    "age": 58,
    "chief_complaint": "Dolor de pecho, diabético, fumador"
  }'

# Expected: URGENCY = HIGH
```

### Scenario 3: RED Path (Critical)

```bash
# Patient: Aortic dissection (widow maker)
curl -X POST http://localhost:7001/consultations \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "Juan Martínez",
    "age": 45,
    "chief_complaint": "Dolor de pecho severo irradiado, sudoroso"
  }'

# Expected: URGENCY = CRITICAL
# Expected: CRITICAL_PATTERN_DETECTED event
```

---

## 📚 Additional Resources

- **One-pager**: `docs/sales/FI-COLD-ONE-PAGER.md`
- **Video script**: `docs/sales/VIDEO-SCRIPT-90s.md`
- **Architecture docs**: `docs/architecture/`
- **Full README**: `README.md`
- **QUICKSTART**: `QUICKSTART.md`

---

## 🆘 Support

Si encuentras problemas durante el setup:

1. **Check logs**: `docker-compose logs -f [service]`
2. **Verify prerequisites**: Docker version, disk space, RAM
3. **Rebuild**: `docker-compose build --no-cache`
4. **Contact**:
   - Email: bernard.uriza@free-intelligence.health
   - GitHub Issues: [link por definir]

---

**Status**: Demo setup guide complete ✅
**Next step**: Run demo + record video for one-pager
