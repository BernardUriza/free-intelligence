# Free Intelligence — Documentación

Guías operativas mínimas. Los documentos > 150 líneas están archivados.

## 🎯 Interfaz Principal: fi_cli

**Todos los comandos del sistema deben ejecutarse a través de `fi_cli`**. Esta CLI unificada reemplaza 60+ scripts legacy con una interfaz tipada, testeable y observable.

```bash
# Ejecución básica
PYTHONPATH=backend/src python -m fi_cli --help

# Comandos principales
PYTHONPATH=backend/src python -m fi_cli dev all          # Arrancar desarrollo
PYTHONPATH=backend/src python -m fi_cli coder lint-fix   # Verificar/corrregir código
PYTHONPATH=backend/src python -m fi_cli ops backend-health  # Health checks
```

### Por qué fi_cli?

- **Unificada**: Un solo comando para todas las operaciones
- **Tipada**: Validación completa y autocompletado
- **Observable**: Métricas y logs estructurados
- **Segura**: Protección PHI/PII integrada
- **Testeable**: Cada comando tiene tests unitarios

**Artefactos activos:**
- `config/fi.policy.yaml` — Políticas ejecutables (egreso, retención, flags)
- `policies/error_budgets.yml` — SLOs y presupuestos de error
- `backend/src/fi_observability/` — Herramientas read-only (metrics/traces/health/alerts)

**Comandos legacy (solo específicos):**
- `make observability-metrics OBS_LOG_SOURCE=/path/to/structured.jsonl`
- `make observability-traces OBS_LOG_SOURCE=/path/to/structured.jsonl`
- `make observability-health OBS_BASE_URL=http://localhost:7001`
- `make observability-alerts`

**Archivados:** `docs/archive/` (review, arquitectura detallada, playbooks extensos)

Consulta `claude.md` para guía operativa y bitácora.
