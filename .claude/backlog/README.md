# Backlog — AIRE

## El espejo (que la memoria no se pierda)

| # | Item | Estado |
|---|------|--------|
| 1 | Copiar `postgres_session_store.py` oficial del SDK y correrle `run_session_store_conformance` (14 contratos) | Propuesto |
| 2 | Traer `hosting/server.py` del cookbook oficial y **cablearle el `session_store`** (lo que no trae) | Propuesto |
| 3 | `project_id` → `cwd` + `CLAUDE_CONFIG_DIR` por proyecto (el cookbook lo tiene hardcodeado en `/app`) | Propuesto |
| 4 | `uuid5` determinístico del nombre → adiós al `hosting_session_map.json` y al dict en RAM | Propuesto |
| **5** | **Tracer: capítulo 1 → matar el contenedor → capítulo 2 lee el capítulo 1 desde Postgres** | **Propuesto** |

## La escoba (que la basura sea manejable)

El SDK **nunca borra** y delega la retención al adapter por escrito. Nadie lo ha
implementado — ni el cookbook, ni Agno, ni ArcReel. Es el hueco más limpio.

| # | Item | Estado |
|---|------|--------|
| 6 | Retención: TTL por proyecto, archivar sesiones frías, purgar | Propuesto |
| 7 | Backups programados (`pg_dump` + cron) | Propuesto |
| 8 | Métricas: cuánto pesa cada proyecto, cuántas sesiones, cuánto costaron | Propuesto |
| 9 | Compactación / resumen de sesiones viejas antes de archivarlas | Idea |

## Lo que se abre porque la base es tuya

| # | Item | Estado |
|---|------|--------|
| 10 | Página para ver tus sesiones (es un `SELECT`) | Propuesto |
| 11 | Memory Tool (`memory_20250818`) → hechos destilados en la misma base | Propuesto |
| 12 | Hook `Stop` → `git commit && push` del corpus al cerrar cada job | Propuesto |
| 13 | Búsqueda semántica sobre las sesiones (pgvector) | Idea |
| 14 | PR a Agno: añadirle `session_store` a su `ClaudeAgent` (41k ⭐, le faltan pocas líneas) | Idea |

---

**El único que importa hoy es el #5.** Todo lo demás es plomería hasta que el capítulo 2
se acuerde del capítulo 1.
