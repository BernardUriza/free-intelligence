# OG118-BACKGROUND-1 — real cross-turn background execution (make "te aviso" true)

Status: **In progress — recibo del SERVIDOR obtenido 2026-09-28; falta el recibo del CLIENTE** (el turno rompió la UI con React #185 y no persistió; ver intento #3)
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

### Re-verificación 2026-09-15 04:22 UTC (reloj del droplet) — el fallback SÍ volvió a caer, y por la razón anticipada

El fallback no salió del enfriamiento una sola vez: `journalctl -u aire-server`
en `root@159.203.84.13` muestra `CREDENTIAL-EXHAUSTED api-key-fallback cools
3600s (default)` repitiéndose cada pocas horas desde el 2026-09-11, incluida la
línea de las 04:11:37 UTC de hoy — 20 segundos después de un turno real
(`POST .../insult-1489180895264116736/sessions/.../messages` → 200 OK).

**Causa confirmada contra el servicio real, no contra el log** (`curl` directo a
`api.anthropic.com/v1/messages` con esa key, sin pasar por AIRE):

```
HTTP 400 invalid_request_error
"Your credit balance is too low to access the Anthropic API."
```

No es un rate limit que se cure solo. Es la tarjeta de esa cuenta de Anthropic
Console sin saldo — recarga manual, átomo de Bernard (dinero).

`oauth-primary` sigue en su cooldown real de tope semanal (`notice`, 232022s
desde 2026-09-12T22:33:58Z) → libera **2026-09-15T15:01:00Z** (≈10h38m desde el
snapshot de arriba).

**O sea: desde el 2026-09-12 22:33 UTC (>2.5 días) el pool completo de AIRE está
seco** — no sólo bloqueando este E2E, sino cortando con `credentials_exhausted`
cualquier turno real que le llegue (se ve en el mismo journal: Insult e
Insult-judge de discord-bot recibiendo turnos y saliendo mudos, el mismo patrón
del P1 de 2026-08-25/26 documentado en `discord-bot/.claude/rules/aire-budget.md`,
pero esta vez la causa es saldo agotado, no un budget ceiling nominal).

**Siguiente real:** recargar la tarjeta de la cuenta Anthropic Console detrás de
`ANTHROPIC_API_KEY_FALLBACK` (decisión/pago de Bernard), o esperar a las
15:01 UTC de hoy a que libere `oauth-primary` y reintentar el turno E2E desde ahí
— lo segundo no arregla el fallback, sólo restaura un slot temporalmente hasta
que vuelva a topar el límite semanal.

### Re-verificación 2026-09-27 (journal leído por Bernard con `ssh -i ~/.ssh/aire_vm`, pegado en sesión) — el journal parecía sano; NO lo estaba (corregido el mismo día, abajo)

`journalctl -u aire-server --since "48 hours ago"` en el droplet: servicio `active`,
1458 líneas, **177 turnos `POST .../messages` → 200 OK** (los últimos a las 13:25 y
21:54 UTC del 27), y **cero** líneas `CREDENTIAL-EXHAUSTED` / `cools` / `exhaust`.
Control de presencia hecho antes de creerle al vacío ([[both-ends-of-the-data-path]]):
con 177 turnos reales, la ausencia de exhaustion sí es evidencia. El clasificador de
auto mode negó el SSH directo desde Claude (`[Production Reads]`); la lectura fue de
Bernard.

**Siguiente real:** reintentar el turno E2E en app.og118.ai hoy, con el pool vivo.
Si el fallback vuelve a caer, el saldo de la cuenta de Console sigue siendo el átomo.

**CORRECCIÓN, mismo día:** lo de arriba fue fake-green mío. Un `200 OK` en
`POST .../messages` no prueba que el modelo contestó (Rule 22: AIRE responde 200 y
mete el error en el body), y el grep `credential|cools|exhaust` no cacha un 401 de
token revocado porque AIRE no lo enfría. Los 177 turnos "sanos" incluían turnos
mudos.

### Intento E2E #2 — 2026-09-27 ~22:10 UTC: `401 OAuth access token has been revoked`

Login en app.og118.ai por Google (sesión SSO viva en el Chrome de debug; la
contraseña guardada de Auth0 está mal, el principal es `google-oauth2|…`). Chat
nuevo, turno pidiendo explícitamente una tarea en background. Respuesta de og118,
firmada `claude-sonnet-4-5`: **`Failed to authenticate. API Error: 401 OAuth access
token has been revoked.`** La tool nunca se llamó; cero ejecuciones del Job.

**Causa confirmada contra `api.anthropic.com` directo** (curl con el token
canónico `claude-max-oauth`, que es el mismo de `aire-claude-oauth`, org
`8e661957` vegdevida): `HTTP 401 "OAuth access token has been revoked."`

**Por qué está revocado:** el 2026-09-26 Bernard revocó los 28 tokens de Claude
Code de la cuenta vegdevida para cortarle el acceso a Alex (server-bot memoria
`project_revocacion_alex_2026_09_26`, paso 4 ✅). El token de AIRE
(`oauth-primary`) era uno de ellos. El paso 6 de ese plan — re-mintear con
`claude setup-token` por cuenta y propagar con `rotate-claude-oauth.sh` — sigue ⏳.
El backup de AIRE (`aire-claude-oauth-backup`, bernardurizadev, org `7b946828`)
no se pudo probar desde esta sesión (el clasificador negó la lectura); si estuviera
vivo AIRE habría caído a él, así que o está muerto o el rotor no cae en 401.

**Siguiente real (átomo de Bernard, browser consent):** `claude setup-token`
logueado en la cuenta que decida (bernarduriza `d1c8c86b` es la sana según
`oauth-map.md`), capturado con `script -q` para no perderlo, luego
`engineering-playbook/scripts/rotate-claude-oauth.sh <token>` + el paso manual del
droplet (`/etc/aire/env`, `systemctl restart aire-server`), actualizar
`oauth-map.md`, y reintentar este mismo turno. Hasta entonces AIRE está mudo para
TODOS sus consumidores (og118, Insult, BAIR), no sólo para este E2E.

### Rotación del token — 2026-09-28 04:49 UTC

Bernard minteó el token nuevo en vegdevida (org `8e661957`, HTTP 200, 7d al 71%) tras un
primer minteo que cayó en bernarduriza (org `d1c8c86b`, 429: semanal al 100% hasta el
28-sep 14:00 CST). `rotate-claude-oauth.sh` propagó SSOT + Azure `og118-api` + GH secrets;
el droplet (`/etc/aire/env` + `systemctl restart aire-server`) lo corrió Bernard con el
token por stdin del ssh. Prueba de vida de AIRE: un turno real de otra sesión a las 04:50 UTC
contestó con texto de Insult (`claude-opus-4-7`), no con 401. Mapa: `~/.secrets/oauth-map.md`.

### Intento E2E #3 — 2026-09-28 04:50 UTC: la cadena del servidor COMPLETA; el cliente se rompió

Mismo chat (`394cdf32-e313-4dfc-8de6-e97c55297652`), turno pidiendo la tarea en background.

**Recibo del servidor, verificado en tres superficies:**
1. `az containerapp job execution list -n og118-worker -g og118-rg` → `og118-worker-78fbwrj`,
   StartTime `2026-09-28T04:50:44Z`, **Succeeded**. La tool `start_background_task` SÍ se llamó
   y el Job SÍ corrió.
2. `GET /conversations/394cdf32…` (og118-api, bearer del navegador) → 3 mensajes; el tercero es
   `role: assistant, origin: background, createdAt 2026-09-28T04:52:01Z`, con el análisis
   completo ("# Por qué el oganesón marca el final de la tabla periódica…"). El worker entregó
   con `append_message`.
3. `updatedAt` de la conversación = 04:52:01Z, posterior al Job.

**Lo que falló, en el cliente:**
- Durante el stream la consola tiró `Uncaught Error: Minified React error #185` (maximum update
  depth) ×3; el render se quedó en "Still working. This can take a second." sin pintar la respuesta.
- El turno #3 (mensaje del usuario + ack del asistente) **no se persistió**: el PUT del cliente
  nunca salió por el crash. La conversación en el servidor tiene el mensaje del worker pero no
  la pregunta que lo originó — se ve un análisis sin su prompt.
- Que el mensaje `origin: background` aparezca en el chat SIN recargar no pudo verificarse: otra
  sesión de Bernard estaba conduciendo la misma pestaña de app.og118.ai en el Chrome de debug
  (Rule 21.1.a), y en una pestaña nueva la lista de chats no cargó.

**Siguiente:** reproducir el React #185 (sospecha: `useOg118ConversationSync` poll de 15 s /
focus-visibility disparando `reloadActive()` + `seedVersion` DURANTE el stream, o la sesión
concurrente en la misma cuenta), arreglar la pérdida del turno, y repetir el E2E con la pestaña
sin otra sesión encima para el recibo visual (screenshot).
