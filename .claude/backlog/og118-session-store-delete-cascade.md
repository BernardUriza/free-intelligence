# Borrar una conversación debe borrar su sesión nativa del session store

Status: Proposed
Proposed: 2026-07-13 by Claude (hallazgo del E2E de PR #358/#359)

## What it is

`DELETE /conversations/{id}` borra el record del ConversationStore (JSON) pero NO
la sesión nativa del SDK en Postgres (`claude_session_store`): el transcript
completo — tool_use/tool_result incluidos — queda huérfano para siempre. Con uso
personal el volumen es bajo, pero es un transcript íntegro de conversación que
sobrevive a su borrado visible: un gap de higiene de datos, no sólo de disco.

El id es derivable: `ClaudeCodeBackend.sdk_session_uuid(conversation_id)` (uuid5
determinístico) + `project_key_for_directory(cwd)`. El store ya tiene `delete()`
(cascade main + subpaths). Falta sólo el cableado en el endpoint de og118 —
y decidir si la primitiva "delete conversation ⇒ delete native session" pertenece
al framework (fi-runner expone `backend.session_key()`; el endpoint es del
consumidor).

Complemento natural: retención/TTL (`DELETE WHERE mtime < cutoff`, ya sugerido en
el docstring del adapter) para sesiones cuyo chat ya no existe.

## Canonical path to reuse (Art. 6)

`PostgresSessionStore.delete()` (ya existe, conformance-tested) +
`backend.session_key(conversation_id)` (ya público tras #359). No inventar
mapeos: el uuid5 es la relación conversación→sesión.

## The decision that's the owner's

Si el borrado es sincrónico en el endpoint (simple, puede fallar si Postgres no
responde) o best-effort con log (el borrado visible nunca se bloquea por la capa
de memoria — coherente con la degradación loud del lifespan).

## Status / next step

No construido. Siguiente paso: cablear el delete en `DELETE /conversations/{id}`
de `apps/og118/server/app.py` cuando `_session_store` está activo.

## Re-verificado 2026-08-22 — sigue abierto, y es un hueco MÁS GRANDE

El estado "Proposed" es correcto, pero el documento describía sólo la mitad:

- `apps/og118/server/app.py:990` `delete_conversation` llama
  `store.delete(principal.sub, conversation_id)` y nada más. `_session_store`
  (global en `:229`) sólo se toca en el lifespan (`:147`) y al armar el runner
  (`:251`).
- **La segunda superficie que el documento no mencionaba:** el borrado en bloque
  `DELETE /conversations` (`:1002`, `clear_conversations`) tiene exactamente el
  mismo hueco, y ahí el huérfano se multiplica por toda la cuenta.

Las dos mitades del cableado ya existen y están sin usar:
`fi_runner/session_stores/postgres.py:258` (`async def delete(key)`) y
`fi_runner/backends/claude_code.py:122` (`session_key()`, público desde #359).

**Atenuante que faltaba anotar:** el store sólo existe si
`OG118_SESSION_STORE_DSN` está seteado (el paso *"Wire the session store DSN"*
de `og118-backend.yml` es no-op sin él), así que hoy en producción el huérfano
puede no existir todavía. Eso baja la urgencia, **no** cierra la tarjeta: el día
que se prenda el DSN, el hueco se estrena con toda la historia acumulada.
