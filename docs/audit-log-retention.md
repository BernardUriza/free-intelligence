# Audit Log Retention Policy - Free Intelligence

**Fecha**: 2025-10-26
**Task**: FI-DATA-FEAT-007
**Sprint**: SPR-2025W44 (Sprint 2)
**Autor**: Bernard Uriza Orozco

---

## 🎯 Propósito

Implementar política de **retención de audit logs** para mantener el sistema eficiente mientras preserva trazabilidad suficiente.

**Garantiza**:
- ✅ Retención de 90 días por defecto (configurable)
- ✅ Cleanup automático de logs antiguos
- ✅ Dry-run mode para seguridad
- ✅ Estadísticas de retención
- ✅ No afecta datos dentro del período

---

## 📋 Política de Retención

### Período por Defecto

**90 días** (3 meses) de logs de auditoría.

**Rationale**:
- Suficiente para debugging de issues recientes
- Compliance con mayoría de requerimientos internos
- Balance entre trazabilidad y eficiencia
- Permite análisis de patrones mensuales/trimestrales

### Alcance

**Aplica a**:
- `/audit_logs/` group en corpus.h5
- Todos los audit logs (operation, user_id, timestamps, hashes)

**NO aplica a**:
- `/interactions/` (memoria longitudinal permanente)
- `/embeddings/` (vectores permanentes)
- `/metadata/` (metadatos del corpus)

---

## 🔧 Funciones Implementadas

### 1. get_audit_logs_older_than(days)

Obtiene índices de logs más antiguos que el período especificado.

```python
from audit_logs import get_audit_logs_older_than

# Find logs older than 90 days
old_indices = get_audit_logs_older_than("storage/corpus.h5", days=90)

print(f"Found {len(old_indices)} logs older than 90 days")
```

**Uso**:
- Identificar logs que serían eliminados
- Análisis before cleanup
- Validación de política

### 2. cleanup_old_audit_logs(days, dry_run)

Elimina logs más antiguos que el período especificado.

**⚠️ IMPORTANTE**: Operación **DESTRUCTIVA**. Siempre usar `dry_run=True` primero.

```python
from audit_logs import cleanup_old_audit_logs

# DRY RUN (recomendado primero)
result = cleanup_old_audit_logs(
    "storage/corpus.h5",
    days=90,
    dry_run=True
)
print(f"Would delete: {result['would_delete']} logs")

# ACTUAL CLEANUP (después de revisar dry run)
result = cleanup_old_audit_logs(
    "storage/corpus.h5",
    days=90,
    dry_run=False
)
print(f"Deleted: {result['deleted']} logs")
print(f"Kept: {result['kept']} logs")
```

**Output**:
```python
{
    "dry_run": False,
    "deleted": 150,
    "kept": 2340,
    "retention_days": 90
}
```

### 3. get_retention_stats(retention_days)

Obtiene estadísticas sobre retención de audit logs.

```python
from audit_logs import get_retention_stats

stats = get_retention_stats("storage/corpus.h5", retention_days=90)

print(f"Total logs: {stats['total_logs']}")
print(f"Within retention (< 90d): {stats['within_retention']}")
print(f"Beyond retention (> 90d): {stats['beyond_retention']}")
print(f"Percentage old: {stats['percentage_old']:.1f}%")
print(f"Oldest log: {stats['oldest_log']}")
print(f"Newest log: {stats['newest_log']}")
```

**Output**:
```python
{
    "exists": True,
    "total_logs": 2490,
    "within_retention": 2340,
    "beyond_retention": 150,
    "retention_days": 90,
    "cutoff_date": "2025-07-28T00:00:00-06:00",
    "oldest_log": "2025-01-15T10:30:00-06:00",
    "newest_log": "2025-10-26T00:45:00-06:00",
    "percentage_old": 6.0
}
```

---

## 🔄 Workflow Recomendado

### Cleanup Manual

```bash
# 1. Revisar stats actuales
python3 << 'EOF'
from backend.audit_logs import get_retention_stats
from backend.config_loader import load_config

config = load_config()
stats = get_retention_stats(config["storage"]["corpus_path"], retention_days=90)

print(f"📊 Retention Stats:")
print(f"  Total logs: {stats['total_logs']}")
print(f"  Within 90 days: {stats['within_retention']}")
print(f"  Beyond 90 days: {stats['beyond_retention']} ({stats['percentage_old']:.1f}%)")
EOF

# 2. Dry run (ver qué se eliminaría)
python3 << 'EOF'
from backend.audit_logs import cleanup_old_audit_logs
from backend.config_loader import load_config

config = load_config()
result = cleanup_old_audit_logs(
    config["storage"]["corpus_path"],
    days=90,
    dry_run=True
)

print(f"Would delete: {result['would_delete']} logs")
EOF

# 3. Cleanup real (si estás seguro)
python3 << 'EOF'
from backend.audit_logs import cleanup_old_audit_logs
from backend.config_loader import load_config

config = load_config()
result = cleanup_old_audit_logs(
    config["storage"]["corpus_path"],
    days=90,
    dry_run=False
)

print(f"✅ Cleanup completed")
print(f"  Deleted: {result['deleted']} logs")
print(f"  Kept: {result['kept']} logs")
EOF
```

### Cleanup Automático (Futuro)

**Cron job propuesto** (ejecutar semanalmente):

```bash
# crontab -e
# Run every Sunday at 2 AM
0 2 * * 0 cd /path/to/free-intelligence && python3 scripts/cleanup_audit_logs.py
```

**Script**: `scripts/cleanup_audit_logs.py` (a crear):
```python
#!/usr/bin/env python3
"""
Automated audit log cleanup (retention policy enforcement)
"""
from backend.audit_logs import cleanup_old_audit_logs, get_retention_stats
from backend.config_loader import load_config
from backend.logger import get_logger

logger = get_logger()
config = load_config()
corpus_path = config["storage"]["corpus_path"]

# Get stats before
stats_before = get_retention_stats(corpus_path, retention_days=90)

# Cleanup (dry_run=False for automated execution)
result = cleanup_old_audit_logs(corpus_path, days=90, dry_run=False)

logger.info(
    "AUTOMATED_RETENTION_CLEANUP",
    deleted=result["deleted"],
    kept=result["kept"],
    total_before=stats_before["total_logs"]
)

print(f"✅ Automated cleanup completed: {result['deleted']} logs deleted")
```

---

## 🧪 Testing

### Unit Tests

```bash
# Run retention tests
python3 -m unittest tests.test_audit_retention -v
```

**Cobertura** (9 tests):
- Empty corpus handling
- All recent logs (nothing to delete)
- Detection of old logs
- Dry run (no side effects)
- Actual cleanup
- Nothing to delete scenario
- Retention stats computation
- Custom retention periods

### Manual Testing

```python
# Test 1: Check current stats
from backend.audit_logs import get_retention_stats
from backend.config_loader import load_config

config = load_config()
stats = get_retention_stats(config["storage"]["corpus_path"])
assert stats["exists"] == True
print(f"✅ Stats: {stats['total_logs']} total logs")

# Test 2: Dry run
from backend.audit_logs import cleanup_old_audit_logs
result = cleanup_old_audit_logs(
    config["storage"]["corpus_path"],
    days=90,
    dry_run=True
)
assert result["dry_run"] == True
print(f"✅ Dry run: would delete {result['would_delete']} logs")
```

---

## ⚠️ Consideraciones Importantes

### Operación Destructiva

**cleanup_old_audit_logs()** elimina datos permanentemente. No hay undo.

**Protecciones**:
1. **dry_run=True por defecto** - Requiere intención explícita
2. **Logs estructurados** - Todas las operaciones logged
3. **Return values** - Info completa de qué se eliminó

### HDF5 Deletion Mechanism

HDF5 no soporta eliminación in-place de filas. El proceso es:

1. Leer datos a mantener
2. Eliminar dataset viejo
3. Crear dataset nuevo
4. Escribir solo datos mantenidos

**Implicaciones**:
- Operación puede tomar tiempo con muchos logs
- Requiere espacio temporal en disco
- Archivo puede no reducir tamaño inmediatamente (ver HDF5 repacking)

### Repacking HDF5 (Opcional)

Para recuperar espacio en disco después de cleanup:

```bash
# h5repack compresses and reorganizes HDF5 file
h5repack -v storage/corpus.h5 storage/corpus_repacked.h5

# Verify repacked file
python3 -c "import h5py; f = h5py.File('storage/corpus_repacked.h5', 'r'); print(f.keys())"

# Replace original (BACKUP FIRST!)
cp storage/corpus.h5 storage/corpus_backup.h5
mv storage/corpus_repacked.h5 storage/corpus.h5
```

---

## 📊 Eventos de Log

### Nuevos Eventos

```python
# Dry run
"RETENTION_DRY_RUN"  # Dry run ejecutado, reporta qué se eliminaría

# Cleanup
"RETENTION_CLEANUP_COMPLETED"  # Cleanup exitoso
"RETENTION_CLEANUP_NOTHING_TO_DELETE"  # No había logs antiguos
"RETENTION_CLEANUP_FAILED"  # Error durante cleanup

# Stats
"RETENTION_CHECK_FAILED"  # Error al obtener logs antiguos
"RETENTION_STATS_FAILED"  # Error al calcular stats
```

### Ejemplo de Log

```json
{
  "event": "RETENTION_CLEANUP_COMPLETED",
  "level": "info",
  "timestamp": "2025-10-26T02:00:00-06:00",
  "deleted": 150,
  "kept": 2340,
  "retention_days": 90
}
```

---

## 🎯 Configuración Futura

**config.yml** (a implementar):

```yaml
audit_logs:
  retention_days: 90  # Default: 90
  auto_cleanup: false  # Enable automated cleanup
  cleanup_schedule: "0 2 * * 0"  # Cron format (Sundays 2 AM)
  dry_run_first: true  # Always dry run before actual cleanup
```

---

## 📈 Métricas y Monitoring

### KPIs

- **Retention compliance**: % de logs dentro de 90 días
- **Cleanup frequency**: Cada cuánto se ejecuta cleanup
- **Deleted per cleanup**: Cuántos logs se eliminan por ejecución
- **Storage saved**: Espacio recuperado

### Dashboard (Futuro)

```python
# Ejemplo de monitoring stats
{
    "retention_policy": {
        "days": 90,
        "compliance": 98.5,  # % logs within retention
        "total_logs": 2340,
        "oldest_log_age_days": 15,  # Oldest log age
        "last_cleanup": "2025-10-20T02:00:00-06:00",
        "next_cleanup": "2025-10-27T02:00:00-06:00"
    }
}
```

---

## 🔗 Referencias

- **HDF5 Dataset Deletion**: https://docs.h5py.org/en/stable/high/group.html
- **ISO 8601 Timestamps**: https://www.iso.org/iso-8601-date-and-time-format.html
- **Cron Scheduling**: https://crontab.guru/

---

## ✅ Criterios de Aceptación

Política de retención está completa cuando:

1. ✅ Función `get_audit_logs_older_than()` implementada
2. ✅ Función `cleanup_old_audit_logs()` con dry_run
3. ✅ Función `get_retention_stats()` implementada
4. ✅ 90 días como período por defecto
5. ✅ Dry run mode por defecto (seguridad)
6. ✅ Tests unitarios (9/9 passing)
7. ✅ Documentación completa
8. ✅ Eventos de log estructurados

---

**Free Intelligence: 90 días de audit trail, eficiencia garantizada** 📅
