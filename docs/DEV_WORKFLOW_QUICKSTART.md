# Dev Workflow Quickstart

**Fecha:** 2025-11-14
**Problema resuelto:** Procesos zombies, código congelado, hot reload roto

---

## 🚀 Comandos Esenciales

### 1️⃣ Arrancar Todo (Modo Desarrollo)

```bash
PYTHONPATH=backend/src python -m fi_cli dev all
```

**Qué hace:**
- ✅ **Limpieza automática**: Mata todos los procesos zombies antes de arrancar
- ✅ **Detección Docker**: Si Docker NO está corriendo → arranca backend NATIVO
- ✅ **Hot reload**: Backend (port 7001) + Frontend (port 9000)
- ✅ **Ctrl+C limpio**: Mata todo correctamente

**Arquitectura:**
- **Docker mode** (si Docker está corriendo):
  - Backend API (Docker, port 7001)
  - Redis + Celery + Flower (Docker)
  - Frontend AURITY (Host, port 9000)

- **Native mode** (si Docker NO está corriendo):
  - Backend API (NATIVO, port 7001) - **SIN Redis/Celery**
  - Frontend AURITY (Host, port 9000)

---

### 2️⃣ Matar Todo (Nuclear Cleanup)

```bash
PYTHONPATH=backend/src python -m fi_cli dev kill-all
```

**Qué hace:**
- Mata TODOS los procesos de FI (backend, frontend, workers)
- Limpia puertos: 7001, 9000, 9050, 11434
- Detiene contenedores Docker (si existen)

---

### 3️⃣ Reiniciar Completamente

```bash
PYTHONPATH=backend/src python -m fi_cli dev all
```

**Qué hace:** `dev-kill` + `dev-all` (cleanup + restart)

---

## 🛠️ Troubleshooting

### Problema: "Hot reload no funciona"

**Síntomas:**
- Modificas código
- Guardas archivo
- Recargas navegador
- **Nada cambia** (sigue mostrando código viejo)

**Diagnóstico:**
```bash
# 1. Verificar si hay procesos zombies
lsof -ti:7001,9000,9050

# 2. Verificar procesos activos
ps aux | grep -E "(uvicorn|next-dev)"
```

**Solución:**
```bash
PYTHONPATH=backend/src python -m fi_cli dev all
```

---

### Problema: "Docker no arranca / Connection refused"

**Causa:** Docker Desktop NO está corriendo

**Solución:**
1. Abre Docker Desktop manualmente
2. Espera a que inicie
3. Ejecuta: `PYTHONPATH=backend/src python -m fi_cli dev all`

**O corre en modo NATIVO:**
```bash
# Docker NO requerido - arranca backend nativo
PYTHONPATH=backend/src python -m fi_cli dev all
```

---

### Problema: "5 versiones del backend corriendo"

**Causa:** Procesos zombies de ejecuciones previas

**Solución:**
```bash
PYTHONPATH=backend/src python -m fi_cli dev kill-all
# Verifica que TODO esté muerto:
lsof -ti:7001,9000,9050
# Si imprime PIDs → todavía hay zombies
# Si no imprime nada → limpio ✅

# Ahora arranca:
PYTHONPATH=backend/src python -m fi_cli dev all
```

---

## 📋 Comandos Disponibles

| Comando | Descripción |
|---------|-------------|
| **Arrancar todo** | `PYTHONPATH=backend/src python -m fi_cli dev all` |
| **Matar todo** | `PYTHONPATH=backend/src python -m fi_cli dev kill-all` |
| **Reiniciar** | `PYTHONPATH=backend/src python -m fi_cli dev all` (kill incluido) |
| **Backend solo** | `PYTHONPATH=backend/src python -m fi_cli dev start` |
| **Frontend solo** | `cd apps/aurity && pnpm dev` |

---

## 🔥 Workflow Recomendado

### Inicio del día:
```bash
# 1. Limpia todo
PYTHONPATH=backend/src python -m fi_cli dev kill-all

# 2. Arranca fresh
PYTHONPATH=backend/src python -m fi_cli dev all
```

### Durante desarrollo:
- **Si hot reload funciona:** Trabaja normal
- **Si algo se congela:**
  ```bash
  PYTHONPATH=backend/src python -m fi_cli dev all
  ```

### Fin del día:
```bash
PYTHONPATH=backend/src python -m fi_cli dev kill-all
```

---

## 🎯 Ventajas de esta Solución

✅ **Sin procesos zombies:** Cleanup automático antes de arrancar
✅ **Ctrl+C limpio:** Mata todo correctamente (backend + frontend + Docker)
✅ **Detección Docker:** Arranca nativo si Docker NO está disponible
✅ **Hot reload garantizado:** Limpia caché y procesos viejos
✅ **Monitoreo proactivo:** Detecta código congelado automáticamente

---

## 📝 Logs

### Backend (Docker):
```bash
docker logs -f fi-backend
```

### Backend (Native):
```bash
tail -f logs/backend-dev.log
```

### Frontend:
```bash
tail -f logs/frontend-aurity-dev.log
```

### Todos los servicios:
```bash
docker compose -f docker/docker-compose.full.yml logs -f
```

---

## 🚨 Red Flags

Si ves estos síntomas, ejecuta `make dev-restart`:

1. ❌ Modificas código pero NO ves cambios
2. ❌ Browser dice "Connection refused" pero `lsof -ti:9000` imprime un PID
3. ❌ Backend responde pero con código de hace 2 horas
4. ❌ Error "Address already in use" al arrancar

---

**Autor:** Bernard Uriza Orozco
**Última actualización:** 2025-11-14
**Contexto:** Fix definitivo para procesos zombies + código congelado
