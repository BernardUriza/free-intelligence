# Backlog — AIRE

| # | Item | Estado |
|---|------|--------|
| 1 | Copiar `postgres_session_store.py` oficial del SDK y correrle `run_session_store_conformance` (14 contratos) | Propuesto |
| 2 | Traer `hosting/server.py` del cookbook oficial y **cablearle el `session_store`** (lo que no trae) | Propuesto |
| 3 | `project_id` → `cwd` + `CLAUDE_CONFIG_DIR` por proyecto (el cookbook lo tiene hardcodeado en `/app`) | Propuesto |
| 4 | Auth en el endpoint (el server oficial no tiene) | Propuesto |
| 5 | Tracer bullet: capítulo 1 → matar el contenedor → capítulo 2 lee el capítulo 1 **desde Postgres** | Propuesto |
| 6 | Hook `Stop` → `git commit && push` del corpus al cerrar cada job | Propuesto |
| 7 | Memory Tool (`memory_20250818`) → hechos destilados en la misma base | Propuesto |
| 8 | Página para ver las sesiones (la tabla es tuya: es un `SELECT`) | Propuesto |
| 9 | PR a Agno: añadirle `session_store` a su `ClaudeAgent` (41k ⭐, le faltan pocas líneas) | Idea |

**El único que importa es el #5.** Todo lo demás es plomería hasta que el capítulo 2
se acuerde del capítulo 1.
