# OG118-BACKGROUND-1 — real cross-turn background execution (make "te aviso" true)

Status: **In progress** — 2026-09-12: decidido (ACA Job) y construido en la rama `bernarduriza/og118-background-job`; falta el recibo E2E en app.og118.ai tras el deploy
Proposed: 2026-07-05 by Bernard (dogfood: og118 promised a background investigation, then had no access half an hour later)

## What it is

og118's runtime is **request/response stateless** — each `/chat/stream` turn is a
fresh Claude Code invocation with no process that survives past the reply
(intentional: continuity is client-sent history replay, so the backend survives
ACA replica recycles — see `runner.py` DD-002C). Consequence: when the persona
enters "agent mode" and promises to *"seguir investigando en el background y te
aviso"*, there is no background — the turn ends, nothing runs, and the next turn
the model has no memory or access of the promised task.

The **honesty guard** (shipped separately) makes the persona STOP promising async
work it can't do. This item is the opposite direction: **actually support it** —
a real background job system so "te aviso cuando termine" becomes true:

- a durable task queue / worker that runs a research/analysis job across turns;
- resumable, cancellable jobs (fi-core `task_tracker` v2 already models
  DAG deps / replanning / cancellation — see the task_tracker v2 memory — but its
  EXECUTION is still within a turn);
- a way to surface "job N finished" back into the conversation (push/poll), and
  persistence that survives an ACA replica recycle (the current stateless design
  deliberately has none server-side).

## Canonical path to reuse (Art. 6)

Do NOT hand-roll a queue. Evaluate reusing: fi-core `task_tracker` v2 (plan/step
model + cancellation, already wired as an og118 capability) as the job *model*;
a durable backend for the *execution* (the open question). Whatever runs the job
must respect the same COMPANION `ToolPolicy` and corpus binding as a live turn —
the background worker is not a wider-privilege path.

## The decision that's the owner's — reframed with the live infra (2026-09-12)

La premisa original ("rompe el invariante de cero estado en el servidor") ya no
aplica: las conversaciones viven como JSON en un Azure Files montado en
`og118-api` (`ragstore-vol`), cloud-autoritativas desde julio. Un registro de job
al lado es la misma categoría de estado, no una nueva.

La restricción real es **scale-to-zero**: `og118-api` corre con `minReplicas: 0`,
`maxReplicas: 1`. Un worker dentro de ese contenedor muere en cuanto se va el
tráfico; correrlo ahí exige una réplica caliente permanente (costo 24/7).

Las dos preguntas, en orden:

1. **¿"Te aviso" debe ser verdad, o el honesty guard es la respuesta final?**
2. **Si sí, dónde corre el worker.** La primitiva canónica es un **Azure
   Container Apps Job**: misma imagen, entrypoint `worker`, disparado por la API
   cuando el modelo se compromete a una tarea, cobrado por ejecución, sin réplica
   caliente. Estado del job como archivo en el share que ya existe; modelo del
   job = fi-core `task_tracker` v2 (ya es capability de og118); el worker corre
   bajo la misma `ToolPolicy` COMPANION y el mismo corpus binding que un turno en
   vivo. Al terminar, appendea un mensaje de asistente al record de la
   conversación, y el cliente lo levanta por la librería cloud que ya pollea. La
   notificación es en el transcript, no push.

**Recomendación de Claude:** sí, y el ACA Job. Reusa todo lo que ya existe, agrega
un solo recurso en `og118-rg` y sólo cobra por corrida. La réplica caliente no
compra nada que el Job no dé y factura las 24 horas.

Lo que se acepta al decir que sí: un recurso ACA nuevo, costo por ejecución, y que
la primera versión avisa dentro del chat y no en el teléfono.

## Status / next step

Not built. Blocked on the architecture decision above. The honesty guard ships
now as the correct interim behavior (no lying about async); this item captures the
real-async feature so the roadmap doesn't lose it. See [[framework-first-canary]].

## Construido — 2026-09-12

Decisión tomada por `/ultra-lord`: sí, y el ACA Job. Lo que existe en la rama:

- **Servidor**: `background_jobs.py` (JobStore por directorio-estado en el share,
  cápsula HMAC con vencimiento, arranque del Job por identidad administrada vía
  IMDS + ARM), `mcp_background.py` (la puerta MCP-sobre-HTTP con la única tool
  `start_background_task`, clon del `mcp_http.py` de discord-bot),
  `background_worker.py` (`python background_worker.py` dentro del Job: reclama,
  corre `Runner.run`, entrega con `ConversationStore.append_message`).
- **Anti-clobber**: `put_content` reinserta los mensajes `origin: background` que
  el PUT del cliente no traiga. Sin eso el siguiente turno del usuario borraba el
  resultado del worker — el hallazgo que decidió el diseño.
- **Prompt**: `companion_constraints.md` quedó en el párrafo general; el
  honesty guard vive en `no_background.md` y se anexa sólo cuando la infra NO
  está; con ella se anexa `background_task.md`, que enseña la tool y prohíbe
  prometer sin llamarla.
- **Cliente**: fi-glass `reloadActive()` + `seedVersion` en `useAgentConversation`;
  og118 `useOg118ConversationSync` (focus/visibility + poll de 15 s, sólo en
  cloud y nunca mientras streamea).
- **Infra**: step del workflow que crea el Job desde `scripts/aca_job.yaml`,
  asigna *Container Apps Jobs Operator* a la identidad del app y cablea el trío
  de env. Origen de og118 agregado a `AIRE_REMOTE_TOOL_ORIGINS` (local y droplet).
- **Tests**: servidor 221 → 236; fi-glass 627 → 636; og118 web 116 → 122.

Lo que NO está hasta que haya recibo: la vuelta completa en app.og118.ai — el
modelo llama la tool, la ejecución del Job sale `Succeeded`, y el mensaje aparece
en el chat sin recargar.

### Intento E2E #1 — 2026-09-12 22:33 UTC: bloqueado por las credenciales de AIRE, no por el código

Deploy `a9862fdf` verificado en Azure: Job `og118-worker` Succeeded (comando
`python background_worker.py`, `ragstore` en `/opt/fi/data`), *Container Apps
Jobs Operator* asignado a la identidad `98a6f32f…` sobre el Job, el trío de env
en `og118-api`. La puerta MCP en producción: 404 sin bearer, `tools/list` con
bearer, cápsula falsa → error. AIRE: allowlist con el origen de og118 (sonda: el
origen pasa, `attacker.example.com` sigue 422).

El turno real en app.og118.ai murió antes de llegar al modelo:
`AIRE turn error [credentials_exhausted]`. Journal de la puerta:
`oauth-primary cools 232022s` (≈2.7 días: tope semanal del OAuth) y
`api-key-fallback cools 3600s (default)` a las 22:34:11 UTC. Cero ejecuciones del
Job, como corresponde: la tool nunca se llamó.

Siguiente: reintentar el mismo turno (botón *Reintentar*) cuando el fallback
salga del enfriamiento (~23:35 UTC). Si el fallback vuelve a caer, la causa está
en esa llave (facturación/429), no en og118.
