# Free Intelligence — Documentación

Guías operativas mínimas. Los documentos > 150 líneas están archivados.

**Artefactos activos:**
- `config/fi.policy.yaml` — Políticas ejecutables (egreso, retención, flags)
- `policies/error_budgets.yml` — SLOs y presupuestos de error
- `backend/src/fi_observability/` — Herramientas read-only (metrics/traces/health/alerts)

**Comandos (Makefile):**
- `make observability-metrics OBS_LOG_SOURCE=/path/to/structured.jsonl`
- `make observability-traces OBS_LOG_SOURCE=/path/to/structured.jsonl`
- `make observability-health OBS_BASE_URL=http://localhost:7001`
- `make observability-alerts`

**Archivados:** `docs/archive/` (review, arquitectura detallada, playbooks extensos)

Consulta `claude.md` para guía operativa y bitácora.
