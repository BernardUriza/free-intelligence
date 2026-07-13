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
